from __future__ import annotations

import logging
from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from services.model_router import select_model
from services.output_sanitizer import enforce_followup_constraints, normalize_grading_evidence, sanitize_quotes
from services.prompt_builder import (
    build_edit_messages,
    build_followup_messages,
    build_grading_messages,
)
from services.scoring import compute_scores, enforce_conservative_coverage

logger = logging.getLogger(__name__)


class GradeState(TypedDict, total=False):
    document_text: str
    rubric_id: str
    rubric_json: dict
    user_instruction: str | None
    grammar_only: bool
    reasoning_mode: str
    calibration_examples: list[dict]
    model: str
    route_reason: str
    token_estimate: int
    grading_result: dict


class LangGraphFlow:
    def __init__(self, llm_client: Any):
        self.llm_client = llm_client
        self._compiled_graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(GradeState)
        graph.add_node("load_rubric", self._load_rubric)
        graph.add_node("route_model", self._route_model)
        graph.add_node("grade", self._grade)
        graph.add_node("compute_scores", self._compute_scores)
        graph.add_node("propose_revision_plan", self._propose_revision_plan)

        graph.add_edge(START, "load_rubric")
        graph.add_edge("load_rubric", "route_model")
        graph.add_edge("route_model", "grade")
        graph.add_edge("grade", "compute_scores")
        graph.add_edge("compute_scores", "propose_revision_plan")
        graph.add_edge("propose_revision_plan", END)
        return graph.compile()

    def _load_rubric(self, state: GradeState) -> GradeState:
        return state

    def _route_model(self, state: GradeState) -> GradeState:
        model, reason, token_estimate = select_model(
            rubric_id=state["rubric_id"],
            document_text=state["document_text"],
            user_text=state.get("user_instruction"),
            grammar_only=state.get("grammar_only", False),
        )
        logger.info(
            "Model routing decision. selected_model=%s reason=%s est_tokens=%s",
            model,
            reason,
            token_estimate,
        )
        state["model"] = model
        state["route_reason"] = reason
        state["token_estimate"] = token_estimate
        return state

    def _grade(self, state: GradeState) -> GradeState:
        messages = build_grading_messages(
            state["document_text"],
            state["rubric_json"],
            state["rubric_id"],
            state.get("user_instruction"),
            state.get("reasoning_mode", "off"),
            state.get("calibration_examples"),
        )
        parsed, _ = self.llm_client.complete(
            model=state["model"],
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
            rubric_id=state["rubric_id"],
        )
        parsed, adjusted_count = normalize_grading_evidence(parsed)
        if adjusted_count:
            logger.info("Applied grading evidence normalization. criteria_adjusted=%s", adjusted_count)
        criteria_count = len(parsed.get("criteria", [])) if isinstance(parsed, dict) else 0
        logger.info("After model call stats. criteria_scored=%s", criteria_count)
        state["grading_result"] = parsed
        return state

    def _compute_scores(self, state: GradeState) -> GradeState:
        conservative = enforce_conservative_coverage(state["grading_result"], state["rubric_json"])
        scored, overall, letter = compute_scores(conservative, state["rubric_json"])
        logger.info(
            "After backend scoring. overall_score_1_to_4=%s letter_grade=%s",
            overall,
            letter,
        )
        state["grading_result"] = scored
        return state

    def _propose_revision_plan(self, state: GradeState) -> GradeState:
        result = state["grading_result"]
        if not result.get("priority_revisions"):
            weak = sorted(result.get("criteria", []), key=lambda c: c.get("score", 1))[:3]
            result["priority_revisions"] = [
                f"Improve {row.get('criterion_id', 'criterion')} with stronger evidence and clearer rubric alignment."
                for row in weak
            ]
            state["grading_result"] = result
        return state

    def grade_document(
        self,
        *,
        document_text: str,
        rubric_id: str,
        rubric_json: dict,
        user_instruction: str | None = None,
        grammar_only: bool = False,
        reasoning_mode: str = "off",
        calibration_examples: list[dict] | None = None,
    ) -> dict:
        state: GradeState = {
            "document_text": document_text,
            "rubric_id": rubric_id,
            "rubric_json": rubric_json,
            "user_instruction": user_instruction,
            "grammar_only": grammar_only,
            "reasoning_mode": reasoning_mode,
            "calibration_examples": calibration_examples or [],
        }
        out = self._compiled_graph.invoke(state)
        return out["grading_result"]

    def suggest_edits(self, *, document_text: str, rubric_id: str, instruction: str | None = None) -> dict:
        model, reason, token_estimate = select_model(
            rubric_id=rubric_id,
            document_text=document_text,
            user_text=instruction,
            grammar_only=True,
        )
        logger.info(
            "Model routing decision. selected_model=%s reason=%s est_tokens=%s",
            model,
            reason,
            token_estimate,
        )
        messages = build_edit_messages(document_text, instruction)
        parsed, _ = self.llm_client.complete(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            rubric_id=rubric_id,
        )
        logger.info(
            "After model call stats. edits_count=%s",
            len(parsed.get("edits", [])) if isinstance(parsed, dict) else 0,
        )
        return parsed

    def answer_followup(
        self,
        *,
        document_text: str,
        rubric_id: str,
        rubric_json: dict,
        grading_result: dict,
        question: str,
        prior_messages: list[dict],
        reasoning_mode: str = "off",
    ) -> dict:
        logger.info(
            "Follow-up request context. question=%s context_included=%s",
            question,
            ["document", "rubric", "grading_result"],
        )
        model, reason, token_estimate = select_model(
            rubric_id=rubric_id,
            document_text=document_text,
            user_text=question,
            grammar_only=False,
        )
        logger.info(
            "Model routing decision. selected_model=%s reason=%s est_tokens=%s",
            model,
            reason,
            token_estimate,
        )

        messages = build_followup_messages(
            document_text,
            rubric_json,
            grading_result,
            question,
            prior_messages,
            reasoning_mode,
        )
        parsed, _ = self.llm_client.complete(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            rubric_id=rubric_id,
        )
        if isinstance(parsed, dict):
            parsed["answer"] = enforce_followup_constraints(parsed.get("answer", ""), question)
            parsed["citations"] = sanitize_quotes(parsed.get("citations", []), max_quotes=5)
        logger.info(
            "After model call stats. citation_count=%s",
            len(parsed.get("citations", [])) if isinstance(parsed, dict) else 0,
        )
        return parsed
