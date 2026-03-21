from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from openai import BadRequestError, OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=api_key)

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        top_p: float = 1.0,
        seed: int | None = 42,
        response_format: Optional[dict[str, Any]] = None,
        rubric_id: Optional[str] = None,
    ) -> tuple[Any, str]:
        prompt_preview = messages[-1]["content"][:400].replace("\n", " ") if messages else ""
        logger.info(
            "Before model call. model=%s rubric_id=%s prompt_preview=%s",
            model,
            rubric_id,
            prompt_preview,
        )

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        if seed is not None:
            kwargs["seed"] = seed
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = self.client.chat.completions.create(**kwargs)
        except BadRequestError as exc:
            # Some model backends may not support seeded sampling; fallback safely.
            if "seed" in kwargs and "seed" in str(exc).lower():
                logger.warning("Model rejected seed parameter; retrying without seed. model=%s", model)
                kwargs.pop("seed", None)
                response = self.client.chat.completions.create(**kwargs)
            else:
                raise
        content = response.choices[0].message.content or ""

        parsed: Any = content
        parsing_succeeded = False
        if response_format is not None:
            parsed = json.loads(content)
            parsing_succeeded = True

        logger.info("After model call. parsing_succeeded=%s content_len=%s", parsing_succeeded, len(content))
        return parsed, content
