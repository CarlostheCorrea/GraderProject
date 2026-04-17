from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from orchestrators.langgraph_flow import LangGraphFlow
from orchestrators.pydanticai_flow import PydanticAIFlow
from schemas import (
    AskRequest,
    BuildRubricRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    EditRequest,
    ExtractDocumentResponse,
    FactCheckOutput,
    GradeRequest,
    ImportRubricRequest,
    RewriteOutput,
    RewriteRequest,
    RubricInfo,
)
from services.document_extractor import SUPPORTED_EXTENSIONS, extract_text_from_file
from services.calibration_loader import load_calibration_examples, pick_calibration_anchors
from services.fact_checker import FactChecker
from services.rewriter import Rewriter
from services.rubric_builder import RubricBuilder
from services.llm_client import LLMClient
from services.model_router import estimate_tokens
from services.rubric_loader import RubricLoader
from services.session_store import InMemorySessionStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="Rubric Grader Backend", version="1.0.0")
frontend_dir = Path(__file__).parent / "frontend"

rubrics: Dict[str, dict] = {}
calibration_bank: Dict[str, list[dict]] = {}
session_store = InMemorySessionStore()
llm_client: LLMClient | None = None
langgraph_flow: LangGraphFlow | None = None
pydanticai_flow: PydanticAIFlow | None = None
fact_checker: FactChecker | None = None
rewriter: Rewriter | None = None
rubric_builder: RubricBuilder | None = None


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _get_flow(orchestrator: str):
    if orchestrator == "langgraph":
        if langgraph_flow is None:
            raise HTTPException(status_code=500, detail="LangGraph flow not initialized")
        return langgraph_flow
    if orchestrator == "pydanticai":
        if pydanticai_flow is None:
            raise HTTPException(status_code=500, detail="PydanticAI flow not initialized")
        return pydanticai_flow
    raise HTTPException(status_code=400, detail="Invalid orchestrator")


@app.on_event("startup")
def startup() -> None:
    global rubrics, calibration_bank, llm_client, langgraph_flow, pydanticai_flow, fact_checker, rewriter, rubric_builder
    loader = RubricLoader(Path(__file__).parent / "FileJson")
    rubrics = loader.load_all()
    calibration_bank = load_calibration_examples(Path(__file__).parent / "SampleEssays")

    llm_client = LLMClient()
    langgraph_flow = LangGraphFlow(llm_client)
    pydanticai_flow = PydanticAIFlow(llm_client)
    fact_checker = FactChecker()
    rewriter = Rewriter(llm_client)
    rubric_builder = RubricBuilder(llm_client)


@app.get("/rubrics", response_model=list[RubricInfo])
def list_rubrics() -> list[RubricInfo]:
    return [
        RubricInfo(
            rubric_id=k,
            name=v.get("name", k),
            short_title=v.get("short_title", v.get("name", k)),
            summary=v.get("summary", "Evaluates writing quality using structured criteria."),
        )
        for k, v in rubrics.items()
    ]


@app.get("/health", include_in_schema=False)
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents/extract", response_model=ExtractDocumentResponse)
async def extract_document(file: UploadFile = File(...)) -> ExtractDocumentResponse:
    filename = file.filename or "uploaded_file"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS and suffix != ".doc":
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: .pdf, .txt, .docx")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        text = extract_text_from_file(filename, raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ExtractDocumentResponse(filename=filename, chars=len(text), document_text=text)


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    if req.custom_rubric_json is not None:
        rubric_json = req.custom_rubric_json
        rubric_id = (rubric_json.get("rubric_id") if isinstance(rubric_json, dict) else None) or req.rubric_id
        if not rubric_json:
            raise HTTPException(status_code=400, detail="custom_rubric_json is empty — generate or import a rubric first")
    else:
        rubric_json = rubrics.get(req.rubric_id)
        rubric_id = req.rubric_id
        if not rubric_json:
            raise HTTPException(status_code=404, detail="Unknown rubric_id")

    chars = len(req.document_text)
    est_toks = estimate_tokens(req.document_text)
    logger.info(
        "Request received. type=create_session session_id=%s rubric_id=%s doc_chars=%s est_tokens=%s orchestrator=%s",
        None,
        rubric_id,
        chars,
        est_toks,
        req.orchestrator,
    )

    session = session_store.create(req.document_text, rubric_id, rubric_json)
    return CreateSessionResponse(session_id=session.session_id)


@app.post("/sessions/{session_id}/grade")
def grade_session(session_id: str, req: GradeRequest):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    rubric_id = req.rubric_id or session.rubric_id
    rubric_json = rubrics.get(rubric_id) if rubric_id in rubrics else None
    if rubric_json is None:
        rubric_json = session.rubric_json
    if not rubric_json:
        raise HTTPException(status_code=404, detail="Unknown rubric_id")

    session.rubric_id = rubric_id
    session.rubric_json = rubric_json

    chars = len(session.document_text)
    est_toks = estimate_tokens(session.document_text + (req.user_instruction or ""))
    logger.info(
        "Request received. type=grade session_id=%s rubric_id=%s doc_chars=%s est_tokens=%s orchestrator=%s reasoning_mode=%s",
        session_id,
        rubric_id,
        chars,
        est_toks,
        req.orchestrator,
        req.reasoning_mode,
    )

    flow = _get_flow(req.orchestrator)
    result = flow.grade_document(
        document_text=session.document_text,
        rubric_id=rubric_id,
        rubric_json=rubric_json,
        user_instruction=req.user_instruction,
        grammar_only=req.grammar_only,
        reasoning_mode=req.reasoning_mode,
        calibration_examples=pick_calibration_anchors(calibration_bank.get(rubric_id, []), max_examples=3),
    )

    session.grading_result = result
    if req.user_instruction:
        session.conversation.append({"role": "user", "content": req.user_instruction})
    session.conversation.append({"role": "assistant", "content": f"Grading complete: {result.get('overall_score_1_to_4')}"})
    session_store.update(session)
    return result


@app.post("/sessions/{session_id}/edit")
def edit_session(session_id: str, req: EditRequest):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    chars = len(session.document_text)
    est_toks = estimate_tokens(session.document_text + (req.instruction or ""))
    logger.info(
        "Request received. type=edit session_id=%s rubric_id=%s doc_chars=%s est_tokens=%s orchestrator=%s",
        session_id,
        session.rubric_id,
        chars,
        est_toks,
        req.orchestrator,
    )

    flow = _get_flow(req.orchestrator)
    result = flow.suggest_edits(
        document_text=session.document_text,
        rubric_id=session.rubric_id,
        instruction=req.instruction,
    )
    session.conversation.append({"role": "assistant", "content": "Provided grammar/clarity edits."})
    session_store.update(session)
    return result


@app.post("/sessions/{session_id}/ask")
def ask_session(session_id: str, req: AskRequest):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.grading_result:
        raise HTTPException(status_code=400, detail="Grade the session first before follow-up Q&A")

    chars = len(session.document_text)
    est_toks = estimate_tokens(session.document_text + req.question)
    logger.info(
        "Request received. type=followup session_id=%s rubric_id=%s doc_chars=%s est_tokens=%s orchestrator=%s reasoning_mode=%s",
        session_id,
        session.rubric_id,
        chars,
        est_toks,
        req.orchestrator,
        req.reasoning_mode,
    )

    flow = _get_flow(req.orchestrator)
    result = flow.answer_followup(
        document_text=session.document_text,
        rubric_id=session.rubric_id,
        rubric_json=session.rubric_json,
        grading_result=session.grading_result,
        question=req.question,
        prior_messages=session.conversation,
        reasoning_mode=req.reasoning_mode,
    )

    session.conversation.append({"role": "user", "content": req.question})
    session.conversation.append({"role": "assistant", "content": str(result)})
    session_store.update(session)
    return result


@app.post("/sessions/{session_id}/rewrite", response_model=RewriteOutput)
def rewrite_essay(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.grading_result:
        raise HTTPException(status_code=400, detail="Grade the session first before rewriting")
    if rewriter is None:
        raise HTTPException(status_code=500, detail="Rewriter not initialized")

    all_criteria = session.grading_result.get("criteria", [])
    weak_criteria = [
        {
            "criterion_name": c.get("criterion_name", c.get("criterion_id", "")),
            "score": c.get("score", 1),
            "justification": c.get("justification", ""),
        }
        for c in all_criteria
        if c.get("score", 4) < 4
    ]

    if not weak_criteria:
        weak_criteria = [
            {
                "criterion_name": c.get("criterion_name", c.get("criterion_id", "")),
                "score": c.get("score", 4),
                "justification": c.get("justification", ""),
            }
            for c in all_criteria
        ]

    logger.info(
        "Request received. type=rewrite session_id=%s weak_criteria=%s",
        session_id,
        len(weak_criteria),
    )

    result = rewriter.rewrite(
        document_text=session.document_text,
        weak_criteria=weak_criteria,
    )

    session.conversation.append({
        "role": "assistant",
        "content": f"Full essay rewrite complete. Addressed {len(weak_criteria)} criteria.",
    })
    session_store.update(session)
    return result


@app.post("/sessions/{session_id}/factcheck", response_model=FactCheckOutput)
def factcheck_session(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if fact_checker is None:
        raise HTTPException(status_code=500, detail="Fact checker not initialized")

    logger.info("Request received. type=factcheck session_id=%s doc_chars=%s", session_id, len(session.document_text))

    result = fact_checker.check(session.document_text)
    session.conversation.append({"role": "assistant", "content": f"Fact-check complete. {len(result.get('claims', []))} claims checked."})
    session_store.update(session)
    return result


@app.post("/rubrics/build")
def build_rubric(req: BuildRubricRequest):
    if rubric_builder is None:
        raise HTTPException(status_code=500, detail="Rubric builder not initialized")
    logger.info("Request received. type=build_rubric desc_chars=%s", len(req.description))
    result = rubric_builder.generate_from_description(req.description)
    return result


@app.post("/rubrics/import")
def import_rubric(req: ImportRubricRequest):
    if rubric_builder is None:
        raise HTTPException(status_code=500, detail="Rubric builder not initialized")
    logger.info("Request received. type=import_rubric text_chars=%s", len(req.rubric_text))
    result = rubric_builder.generate_from_import(req.rubric_text)
    return result


