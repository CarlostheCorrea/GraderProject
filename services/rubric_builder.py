from __future__ import annotations

import logging
from typing import Any

from services.llm_client import LLMClient
from services.prompt_builder import build_rubric_from_description_messages, build_rubric_from_import_messages

logger = logging.getLogger(__name__)

_RUBRIC_SCHEMA_HINT = """
{
  "rubric_id": "short_slug_v1",
  "name": "Full Rubric Name",
  "short_title": "Short Title",
  "description": "One-sentence description.",
  "version": "1",
  "scale": {
    "min": 1, "max": 4,
    "labels": {"1": "Minimal / Insufficient", "2": "Basic / Emerging", "3": "Competent / Proficient", "4": "Advanced / Sophisticated"},
    "grading_rule": "Score reflects the highest anchor fully met by the evidence."
  },
  "categories": [
    {
      "id": "A",
      "name": "Category Name",
      "weight": 0.25,
      "criteria": [
        {
          "id": "A1",
          "name": "Criterion Name",
          "anchors": {
            "1": "Minimal anchor description.",
            "2": "Basic anchor description.",
            "3": "Competent anchor description.",
            "4": "Advanced anchor description."
          }
        }
      ]
    }
  ],
  "scoring": {"method": "weighted_average"},
  "evidence_policy": {"min_quotes": 1, "max_quotes": 2},
  "letter_grade_map": [
    {"min_score": 3.5, "letter": "A"},
    {"min_score": 3.0, "letter": "B"},
    {"min_score": 2.5, "letter": "C"},
    {"min_score": 2.0, "letter": "D"},
    {"min_score": 0.0, "letter": "F"}
  ]
}"""


class RubricBuilder:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate_from_description(self, description: str) -> dict[str, Any]:
        logger.info("Rubric generation from description. length=%s", len(description))
        messages = build_rubric_from_description_messages(description, _RUBRIC_SCHEMA_HINT)
        parsed, _ = self.llm_client.complete(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        logger.info("Rubric generated. rubric_id=%s", parsed.get("rubric_id", "?"))
        return parsed

    def generate_from_import(self, rubric_text: str) -> dict[str, Any]:
        logger.info("Rubric conversion from import. length=%s", len(rubric_text))
        messages = build_rubric_from_import_messages(rubric_text, _RUBRIC_SCHEMA_HINT)
        parsed, _ = self.llm_client.complete(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        logger.info("Rubric converted. rubric_id=%s", parsed.get("rubric_id", "?"))
        return parsed
