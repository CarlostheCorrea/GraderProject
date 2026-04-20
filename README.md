# Rubric Grader

Rubric Grader is a local FastAPI app with a built-in web UI for:

- rubric-based grading
- grammar/clarity edit suggestions
- follow-up Q&A on grading results
- live fact-checking against real web sources (powered by OpenAI web search)

## Requirements

- Python 3.10+ (Python 3.11 or 3.12 recommended for easiest installs)
- OpenAI API key

## Quick Start (3 Steps)

### 1. Clone and enter the project

```bash
git clone https://github.com/CarlostheCorrea/GraderProject.git
cd GraderProject
```

### 2. Set your OpenAI API key

macOS/Linux:

```bash
cp .env.example .env
# Edit .env and replace the placeholder key.
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
# Edit .env and replace the placeholder key.
```

### 3. Run the app

macOS/Linux:

```bash
./run.sh
```

Windows PowerShell:

```powershell
.\run.ps1
```

Open [http://127.0.0.1:8017](http://127.0.0.1:8017).

## Manual Run (No Script)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8017
```

## Frontend Workflow

1. Choose a built-in rubric, or create a temporary custom rubric with the Rubric Builder.
2. Paste text or upload `.pdf`, `.txt`, `.docx`, or `.doc` and click `Extract Text From File`.
3. Click `Create Session`.
4. Run fact-checking, grading, edits, or follow-up Q&A.
5. After grading, optionally use `Rewrite Essay` to rewrite the full essay around weak rubric criteria.

## How To Use The App

1. Start the server and open [http://127.0.0.1:8017](http://127.0.0.1:8017).
2. In `Session Setup`, choose the rubric:
   - Use the `Session Setup` tab to select a built-in rubric.
<img width="1444" height="725" alt="Screenshot 2026-04-20 at 2 33 48 PM" src="https://github.com/user-attachments/assets/18d24ae8-8be7-4558-80fc-bcc05d2c15a6" />
   - Use `Rubric Builder` to generate a custom rubric from a description or convert an existing pasted rubric to JSON.
<img width="1132" height="651" alt="Screenshot 2026-04-20 at 2 35 06 PM" src="https://github.com/user-attachments/assets/6e7935b6-dc10-4c62-bc6d-f84a9b7a356c" />
   - Click `Save & Use This Rubric` if you create a custom rubric. Custom rubrics are temporary for the current session and do not have calibration essays.
4. Add the document:
   - Paste text directly into `Document Text`, or
   - Upload a `.txt`, `.pdf`, `.docx`, or `.doc` file and click `Extract Text From File`.
5. Click `Create Session`. The app stores the selected rubric and document text in memory.
6. Optional: click `Run Fact Check` to extract verifiable claims, search live web sources through OpenAI web search, and return verdicts with source links.
<img width="1309" height="752" alt="Screenshot 2026-04-20 at 2 35 50 PM" src="https://github.com/user-attachments/assets/2cc15b44-d2af-4021-b7c3-4b4f09bab993" />
8. Click `Run Grading` to score the paper against the selected rubric. The result includes:
   - Overall score and letter grade.
   - Summary strengths and priority revisions.
   - A named criteria breakdown using actual criterion names and category names rather than only codes like `A1` or `B1`.
   - Evidence quotes and rubric-anchored justifications.
<img width="1382" height="821" alt="Screenshot 2026-04-20 at 2 37 04 PM" src="https://github.com/user-attachments/assets/e7c4106d-18ae-4640-af1a-0bc5a7d59f48" />
9. After grading, use `Rewrite Essay` if you want the app to rewrite the full essay around the weakest criteria.
10. Use `Generate Edits` for grammar and clarity suggestions.
<img width="1342" height="716" alt="Screenshot 2026-04-20 at 2 38 02 PM" src="https://github.com/user-attachments/assets/21efdb20-43da-437b-ba1b-33a44d2d3bca" />
11. Use `Ask` in `Follow-up Q&A` to ask questions about the document, rubric, grading result, or revision priorities.
<img width="1280" height="535" alt="Screenshot 2026-04-20 at 2 38 46 PM" src="https://github.com/user-attachments/assets/2aff3d78-c8e3-4989-b15e-a52a261a6eb8" />
12. Restarting the app clears in-memory sessions and temporary custom rubrics.

## Example Essays

Provided are example essays in different formats that can be used in the project.

[Essays](https://github.com/CarlostheCorrea/GraderProject/tree/main/ExampleEssays)

## API Endpoints

- `GET /rubrics`
- `GET /health`
- `POST /documents/extract` (multipart upload: `.pdf`, `.txt`, `.docx`)
- `POST /sessions`
- `POST /sessions/{session_id}/factcheck`
- `POST /sessions/{session_id}/grade`
- `POST /sessions/{session_id}/edit`
- `POST /sessions/{session_id}/ask`

## Rubric Files

- `FileJson/OtherCatMeta_updated.json` -> `college_cross_disciplinary_other_v1`
- `FileJson/NatSciMeta_updated.json` -> `essay_quality_v2`
- `FileJson/phdMeta_updated.json` -> `phd_unified_meta_v3`
- `FileJson/HumanSosMeta_updated.json` -> `college_humanities_social_sciences_meta_v2`

## Notes

- Sessions are stored in memory; restarting the app clears sessions.
- Calibration examples are loaded from `SampleEssays/` per rubric and used as internal scoring anchors.
- The system does not request or return chain-of-thought.
- Fact-checking uses the OpenAI Responses API (`gpt-4o` + `web_search_preview` tool) and deducts from your existing OpenAI API credit — no additional API key or third-party account required. Web search queries cost slightly more than standard completions (~$25/1,000 queries).

## Project Features

- Model differentiation (`gpt-4o` vs `gpt-4o-mini`):
  - Included via model routing logic in `services/model_router.py` (routes by estimated complexity/token load).
- Reliability pattern(s):
  - Chain-of-Thought (CoT): Included as internal-only reasoning for grading (`reasoning_mode="on"`), not exposed in outputs.
  - Analogical Prompting: Included via rubric calibration examples from `SampleEssays/` injected into grading prompts.
- Agent/orchestration framework:
  - PydanticAI-style type-safe validation flow: Included and used in default grading path (`orchestrators/pydanticai_flow.py`).
  - LangGraph state-machine flow: Also implemented (`orchestrators/langgraph_flow.py`), but default app usage is PydanticAI.

## Troubleshooting

- `OPENAI_API_KEY is not set`:
  - Set `OPENAI_API_KEY` in `.env` or export it in your shell, then rerun the app.
- `Address already in use` on port 8017:
  - Stop the process using port 8017, or run:
  - `uvicorn main:app --host 127.0.0.1 --port 8018`
- Browser shows stale UI behavior:
  - Hard refresh (`Cmd+Shift+R` on macOS, `Ctrl+F5` on Windows).
- Server restarts repeatedly in a loop:
  - Use stable mode without reload: `uvicorn main:app --host 127.0.0.1 --port 8017`

## Architecture & Request Flow

### High-level Architecture

- `main.py`:
  - FastAPI app, endpoint routing, startup initialization.
- `frontend/`:
  - Static web UI (`index.html`, `app.js`, `style.css`) served by FastAPI.
- `schemas.py`:
  - Request/response models and validation constraints.
- `services/`:
  - `rubric_loader.py`: loads/normalizes rubric JSON files.
  - `calibration_loader.py`: loads rubric-specific sample essays for calibration.
  - `llm_client.py`: model API calls.
  - `prompt_builder.py`: builds grading/edit/follow-up prompts.
  - `output_sanitizer.py`: quote and response constraint cleanup.
  - `scoring.py`: deterministic backend score/letter computation.
  - `model_router.py`: model selection logic (e.g., `gpt-4o` vs `gpt-4o-mini`).
  - `session_store.py`: in-memory session storage.
  - `fact_checker.py`: live fact-checking via OpenAI Responses API with web search tool.
- `orchestrators/`:
  - `pydanticai_flow.py`: default grading/edit/Q&A flow with type-safe output validation and repair fallback.
  - `langgraph_flow.py`: state-machine alternative flow.

### Runtime Flow

1. Startup:
   - Load rubrics from `FileJson/`.
   - Load calibration examples from `SampleEssays/`.
   - Initialize LLM client and orchestrators.
2. Create session (`POST /sessions`):
   - Validate input schema.
   - Store text + selected rubric in memory.
3. Grade (`POST /sessions/{id}/grade`):
   - Build grading prompt with rubric + optional instruction + calibration examples.
   - Route model and call LLM.
   - Normalize evidence fields.
   - Validate output against `TaskAGradingOutput`; if invalid, run repair call.
   - Compute deterministic overall/category/letter scores in backend.
4. Fact Check (`POST /sessions/{id}/factcheck`):
   - Call OpenAI Responses API with `web_search_preview` tool using the existing `OPENAI_API_KEY`.
   - Model identifies up to 6 verifiable claims, searches the web for each, and returns structured verdicts with source URLs.
5. Edit (`POST /sessions/{id}/edit`):
   - Build edit prompt and return structured grammar/clarity edits.
6. Follow-up Q&A (`POST /sessions/{id}/ask`):
   - Build follow-up prompt with document + rubric + prior grading result.
   - Validate response schema and enforce output constraints (e.g., requested sentence count).
7. Frontend display:
   - Render structured results for fact-checking, grading, edits, and Q&A.
- `Could not build wheels for grpcio` / `Could not find <Python.h>`:
  - Delete and recreate the virtual environment, then reinstall:
  - `rm -rf .venv && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
  - If possible, use Python 3.11 or 3.12.
