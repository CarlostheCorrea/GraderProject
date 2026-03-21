# Product Specification: Rubric Grader

## 1. Product Overview

Rubric Grader is a web-based grading assistant that evaluates user-submitted writing against predefined academic rubrics, generates improvement edits, and supports follow-up Q&A on results.

The product ships as a single FastAPI service with an embedded frontend and is designed for fast local use.

## 2. Problem Statement

Manual rubric-based grading is time-intensive and often inconsistent. Users also need actionable writing improvements and the ability to ask clarifying questions after receiving scores.

## 3. Goals

- Provide consistent rubric-based scoring from uploaded text.
- Generate practical grammar and clarity edit suggestions.
- Support contextual follow-up questions tied to prior grading.
- Keep setup simple for local deployment.

## 4. Non-Goals

- Persistent long-term storage of grading sessions.
- User authentication/authorization.
- LMS integration in the current version.

## 5. Target Users

- Instructors and teaching assistants grading essays.
- Students self-evaluating drafts before submission.
- Program evaluators reviewing writing quality at scale.

## 6. Core User Flows

1. User opens the frontend at `/`.
2. User creates a session with writing text and a rubric ID.
3. User runs grading to get category and overall scores.
4. User requests edit suggestions for grammar/clarity improvements.
5. User asks follow-up questions about grade outcomes.

## 7. Functional Requirements

### 7.1 Rubric Management

- System must expose available rubrics via `GET /rubrics`.
- System must map rubric IDs to JSON rubric definitions.
- System must reject invalid rubric IDs with clear error messaging.

### 7.2 Session Lifecycle

- System must create grading sessions via `POST /sessions`.
- Session data must include source text, selected rubric, and generated outputs.
- Session state is in-memory and resets on service restart.

### 7.3 Grading

- System must grade session text via `POST /sessions/{session_id}/grade`.
- Response must include rubric-aligned category scoring.
- Backend must compute category and overall scores deterministically from model output + rubric logic.

### 7.4 Edit Suggestions

- System must provide grammar and clarity edits via `POST /sessions/{session_id}/edit`.
- Suggestions should be concrete, readable, and tied to user text quality.

### 7.5 Follow-up Q&A

- System must support follow-up questions via `POST /sessions/{session_id}/ask`.
- Answers should be grounded in session context (text, rubric, and prior grading outputs).

### 7.6 Health and Reliability

- System must provide health status via `GET /health`.
- Errors must be returned with actionable messages and appropriate HTTP status codes.

## 8. Non-Functional Requirements

- API response for standard requests should generally complete within a few seconds, depending on model latency.
- Service must run locally with minimal setup (`pip install` + `uvicorn`).
- Product must avoid requesting or returning chain-of-thought.

## 9. API Surface (Current)

- `GET /rubrics`
- `GET /health`
- `POST /sessions`
- `POST /sessions/{session_id}/grade`
- `POST /sessions/{session_id}/edit`
- `POST /sessions/{session_id}/ask`

## 10. Rubrics (Current Mapping)

- `OtherCatMeta_updated.json` -> `college_cross_disciplinary_other_v1`
- `NatSciMeta_updated.json` -> `essay_quality_v2`
- `phdMeta_updated.json` -> `phd_unified_meta_v3`
- `HumanSosMeta_updated.json` -> `college_humanities_social_sciences_meta_v2`

## 11. Success Metrics

- Percentage of sessions that complete grading without error.
- Median response times for `/grade`, `/edit`, and `/ask`.
- User-rated usefulness of edit suggestions.
- Repeat usage rate for follow-up Q&A after grading.

## 12. Risks and Mitigations

- In-memory storage risk: session loss on restart.
  - Mitigation: add optional persistent session backend in future versions.
- Model response variance risk: inconsistent qualitative feedback.
  - Mitigation: strengthen prompts and schema validation.
- Rubric mismatch risk: invalid rubric IDs or malformed rubric files.
  - Mitigation: strict validation on startup and request-time checks.

## 13. Future Enhancements

- Persistent storage for sessions and outputs.
- Authentication and role-based access.
- Batch grading and CSV export.
- LMS/API integrations.
- Analytics dashboard for rubric performance trends.
