from __future__ import annotations

import json
import logging
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from schemas import FollowUpResponse, TaskAGradingOutput, TaskBEditsOutput
from services.model_router import select_model
from services.output_sanitizer import enforce_followup_constraints, normalize_grading_evidence, sanitize_quotes
from services.prompt_builder import (
    build_edit_messages,
    build_fix_json_messages,
    build_followup_messages,
    build_grading_messages,
)
from services.scoring import compute_scores, enforce_conservative_coverage

logger = logging.getLogger(__name__)


class PydanticAIFlow:
    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def _validate_with_retry(
        self,
        *,
        schema_cls: Type[BaseModel],
        payload: dict,
        model: str,
        rubric_id: str,
    ) -> dict:
        try:
            model_obj = schema_cls.model_validate(payload)
            return model_obj.model_dump()
        except ValidationError as e:
            fix_messages = build_fix_json_messages(schema_cls.__name__, json.dumps(payload), str(e))
            fixed, _ = self.llm_client.complete(
                model=model,
                messages=fix_messages,
                response_format={"type": "json_object"},
                rubric_id=rubric_id,
            )
            repaired = schema_cls.model_validate(fixed)
            return repaired.model_dump()

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
        model, reason, token_estimate = select_model(
            rubric_id=rubric_id,
            document_text=document_text,
            user_text=user_instruction,
            grammar_only=grammar_only,
        )
        logger.info(
            "Model routing decision. selected_model=%s reason=%s est_tokens=%s",
            model,
            reason,
            token_estimate,
        )

        messages = build_grading_messages(
            document_text,
            rubric_json,
            rubric_id,
            user_instruction,
            reasoning_mode,
            calibration_examples,
        )
        parsed, _ = self.llm_client.complete(
            model=model,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
            rubric_id=rubric_id,
        )
        parsed, adjusted_count = normalize_grading_evidence(parsed)
        if adjusted_count:
            logger.info("Applied grading evidence normalization. criteria_adjusted=%s", adjusted_count)
        validated = self._validate_with_retry(
            schema_cls=TaskAGradingOutput,
            payload=parsed,
            model=model,
            rubric_id=rubric_id,
        )
        logger.info("After model call stats. criteria_scored=%s", len(validated.get("criteria", [])))

        conservative = enforce_conservative_coverage(validated, rubric_json)
        scored, overall, letter = compute_scores(conservative, rubric_json)
        logger.info(
            "After backend scoring. overall_score_1_to_4=%s letter_grade=%s",
            overall,
            letter,
        )
        return scored

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
        validated = self._validate_with_retry(
            schema_cls=TaskBEditsOutput,
            payload=parsed,
            model=model,
            rubric_id=rubric_id,
        )
        logger.info("After model call stats. edits_count=%s", len(validated.get("edits", [])))
        return validated

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
        validated = self._validate_with_retry(
            schema_cls=FollowUpResponse,
            payload=parsed,
            model=model,
            rubric_id=rubric_id,
        )
        validated["answer"] = enforce_followup_constraints(validated.get("answer", ""), question)
        validated["citations"] = sanitize_quotes(validated.get("citations", []), max_quotes=5)
        logger.info("After model call stats. citation_count=%s", len(validated.get("citations", [])))
        return validated
