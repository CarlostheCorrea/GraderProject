from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, conint


OrchestratorType = Literal["langgraph", "pydanticai"]
ReasoningMode = Literal["off", "on", "default", "internal"]


class RubricInfo(BaseModel):
    rubric_id: str
    name: str
    short_title: str
    summary: str


class CreateSessionRequest(BaseModel):
    document_text: str = Field(min_length=1)
    rubric_id: str
    orchestrator: OrchestratorType = "pydanticai"


class CreateSessionResponse(BaseModel):
    session_id: str


class ExtractDocumentResponse(BaseModel):
    filename: str
    chars: int
    document_text: str


class GradeRequest(BaseModel):
    rubric_id: Optional[str] = None
    orchestrator: OrchestratorType = "pydanticai"
    user_instruction: Optional[str] = None
    grammar_only: bool = False
    reasoning_mode: ReasoningMode = "off"


class EditRequest(BaseModel):
    orchestrator: OrchestratorType = "pydanticai"
    instruction: Optional[str] = None


class AskRequest(BaseModel):
    orchestrator: OrchestratorType = "pydanticai"
    question: str = Field(min_length=1)
    reasoning_mode: ReasoningMode = "off"


class GradingCriterionOutput(BaseModel):
    criterion_id: str
    score: conint(ge=1, le=4)
    label: str
    evidence_quotes: List[str] = Field(default_factory=list, max_length=2)
    justification: str


class TaskAGradingOutput(BaseModel):
    criteria: List[GradingCriterionOutput]
    summary_strengths: List[str] = Field(default_factory=list)
    priority_revisions: List[str] = Field(default_factory=list)
    confidence: conint(ge=0, le=100)
    category_scores: Dict[str, float] = Field(default_factory=dict)
    overall_score_1_to_4: float = 1.0
    letter_grade: str = "F"


class SuggestedEdit(BaseModel):
    original: str
    suggested: str
    reason: str


class TaskBEditsOutput(BaseModel):
    edits: List[SuggestedEdit]
    top_5_writing_fixes: List[str] = Field(default_factory=list)


class FollowUpResponse(BaseModel):
    answer: str
    citations: List[str] = Field(default_factory=list)
    consistency_note: str
