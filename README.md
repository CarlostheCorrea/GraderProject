# Rubric Grader

Rubric Grader is a local FastAPI app with a built-in web UI for:

- rubric-based grading
- grammar/clarity edit suggestions
- follow-up Q&A on grading results

## Requirements

- Python 3.10+ (Python 3.11 or 3.12 recommended for easiest installs)
- OpenAI API key

## Quick Start (3 Steps)

### 1. Clone and enter the project

```bash
git clone https://github.com/CarlostheCorrea/GenAI.git
cd GenAI/GraderProject
```

### 2. Set your OpenAI API key

macOS/Linux:

```bash
export OPENAI_API_KEY="your_key_here"
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_key_here"
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

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Manual Run (No Script)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app
```

## Frontend Workflow

1. Choose a rubric.
2. Paste text or upload `.pdf`, `.txt`, or `.docx` and click `Extract Text From File`.
3. Click `Create Session`.
4. Run grading, edits, or follow-up Q&A.

## How To Use The App

1. In `Session Setup`, add your document:
   - Paste text directly into `Document Text`, or
   - Upload a `.txt`, `.pdf`, or `.docx` file and click `Extract Text From File`.
2. Pick the rubric that best matches your assignment.
3. Click `Create Session`.
   
<img width="1246" height="822" alt="Screenshot1" src="https://github.com/user-attachments/assets/6ff5d8c0-e66e-4928-9cd9-ddea87376241" />
   
4. Use one of the actions:
   - `Run Grading` to score the paper against the rubric and return criterion-level scores, evidence quotes, and an overall letter grade.
   
<img width="1346" height="589" alt="Screenshot2" src="https://github.com/user-attachments/assets/14a30501-9df6-4b94-932c-aa05fa46326f" />

   - `Generate Edits` for grammar/clarity suggestions and practical rewrite recommendations you can apply directly.

<img width="1291" height="583" alt="Screenshot3" src="https://github.com/user-attachments/assets/9794302f-4642-48e7-83b6-2efe22ccdce4" />

   - `Ask` in `Follow-up Q&A` to ask questions about the paper or grading, such as summaries, missing evidence, or revision priorities.

<img width="1320" height="499" alt="Screenshot4" src="https://github.com/user-attachments/assets/0718a4ee-5bb7-47b5-8e1e-080e62ecf425" />


## Example Essays

Provided are example essays in different formats that can be used in the project.

[Essays](https://github.com/CarlostheCorrea/GenAI/tree/main/GraderProject/ExampleEssays)

## API Endpoints

- `GET /rubrics`
- `GET /health`
- `POST /documents/extract` (multipart upload: `.pdf`, `.txt`, `.docx`)
- `POST /sessions`
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
  - Set the environment variable, then rerun the app.
- `Address already in use` on port 8000:
  - Stop the process using port 8000, or run:
  - `uvicorn main:app --port 8001`
- Browser shows stale UI behavior:
  - Hard refresh (`Cmd+Shift+R` on macOS, `Ctrl+F5` on Windows).
- Server restarts repeatedly in a loop:
  - Use stable mode without reload: `uvicorn main:app`

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
4. Edit (`POST /sessions/{id}/edit`):
   - Build edit prompt and return structured grammar/clarity edits.
5. Follow-up Q&A (`POST /sessions/{id}/ask`):
   - Build follow-up prompt with document + rubric + prior grading result.
   - Validate response schema and enforce output constraints (e.g., requested sentence count).
6. Frontend display:
   - Render structured results for grading, edits, and Q&A.
- `Could not build wheels for grpcio` / `Could not find <Python.h>`:
  - Delete and recreate the virtual environment, then reinstall:
  - `rm -rf .venv && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
  - If possible, use Python 3.11 or 3.12.
