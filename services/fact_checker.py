from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

_SYSTEM = """You are a rigorous fact-checker for academic essays.

Steps:
1. Read the essay and identify up to 6 specific, verifiable factual claims
   (statistics, historical events, named people or organizations, dates, scientific claims).
   Skip opinions, interpretations, or vague assertions.
2. Use web search to verify each claim against a real, authoritative source.
3. Return ONLY a valid JSON object — no markdown fences, no explanation outside JSON.

Required JSON structure:
{
  "claims": [
    {
      "claim": "Exact factual statement from the essay",
      "verdict": "Supported" | "Contradicted" | "Unverifiable",
      "explanation": "1-2 sentences on what the source says vs. the claim",
      "source_title": "Name of the source",
      "source_url": "https://..."
    }
  ]
}

Rules:
- verdict "Supported": source clearly confirms the claim
- verdict "Contradicted": source clearly contradicts the claim
- verdict "Unverifiable": no reliable source found; set source_title and source_url to ""
- Include source_url only when you have retrieved a real URL from search results
- Return JSON only — nothing before or after the JSON object
"""


class FactChecker:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=api_key)

    def check(self, document_text: str) -> dict[str, Any]:
        doc_excerpt = document_text[:8000]
        logger.info("Starting fact check. doc_chars=%s", len(document_text))

        response = self.client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            instructions=_SYSTEM,
            input=f"Fact-check the following essay:\n\n{doc_excerpt}",
        )

        raw = response.output_text or ""
        result = self._parse(raw)
        logger.info("Fact check complete. claims=%s", len(result.get("claims", [])))
        return result

    def _parse(self, raw: str) -> dict[str, Any]:
        # Strip markdown code fences if the model wraps with them
        clean = raw.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", clean)
        if match:
            clean = match.group(1)

        try:
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Could not parse fact-check JSON. raw=%s", raw[:300])
            return {"claims": []}
