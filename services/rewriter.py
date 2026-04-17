from __future__ import annotations

import logging
from typing import Any

from services.llm_client import LLMClient
from services.prompt_builder import build_rewrite_messages

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
