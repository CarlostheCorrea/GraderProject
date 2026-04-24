from __future__ import annotations

import logging
from typing import Any

from services.llm_client import LLMClient
from services.prompt_builder import build_rewrite_messages, build_source_rewrite_messages

logger = logging.getLogger(__name__)


class Rewriter:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def rewrite(
        self,
        *,
        document_text: str,
        weak_criteria: list,
    ) -> dict[str, Any]:
        logger.info("Rewrite requested. criteria_count=%s", len(weak_criteria))
        messages = build_rewrite_messages(
            document_text=document_text,
            weak_criteria=weak_criteria,
        )
        parsed, _ = self.llm_client.complete(
            model="gpt-4o",
            messages=messages,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        logger.info("Rewrite complete. criteria_addressed=%s", len(weak_criteria))
        return parsed

    def rewrite_with_sources(
        self,
        *,
        document_text: str,
        selected_claims: list,
    ) -> dict[str, Any]:
        logger.info("Source-based rewrite requested. selected_claims=%s", len(selected_claims))
        messages = build_source_rewrite_messages(
            document_text=document_text,
            selected_claims=selected_claims,
        )
        parsed, _ = self.llm_client.complete(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        logger.info("Source-based rewrite complete. sources_used=%s", len(parsed.get("sources_used", [])))
        return parsed
