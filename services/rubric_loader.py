from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


RUBRIC_FILE_MAP = {
    "OtherCatMeta_updated.json": {
        "rubric_id": "college_cross_disciplinary_other_v1",
        "name": "OtherCatMeta_updated",
        "short_title": "Academic Skills (Cross-Disciplinary)",
        "summary": "Best for cross-disciplinary skill assessment (reasoning, problem framing, logic/quantitative thinking, ethics, and reflection) rather than essay craft alone.",
    },
    "NatSciMeta_updated.json": {
        "rubric_id": "essay_quality_v2",
        "name": "NatSciMeta_updated",
        "short_title": "Essay Quality",
        "summary": "Best for overall essay writing quality using precise anchors for argument clarity, structure, evidence integration, and polished prose.",
    },
    "phdMeta_updated.json": {
        "rubric_id": "phd_unified_meta_v3",
        "name": "phdMeta_updated",
        "short_title": "PhD Academic Paper",
        "summary": "Best for doctoral-level writing such as dissertations, proposals, and publishable scholarship with advanced academic rigor expectations.",
    },
    "HumanSosMeta_updated.json": {
        "rubric_id": "college_humanities_social_sciences_meta_v2",
        "name": "HumanSosMeta_updated",
        "short_title": "Humanities & Social Sciences",
        "summary": "Best for undergraduate humanities/social science analysis emphasizing argumentation, interpretation, disciplinary concepts, and evidence use.",
    },
}


class RubricLoader:
    def __init__(self, rubric_dir: Path):
        self.rubric_dir = rubric_dir
        self._rubrics: Dict[str, dict] = {}

    def load_all(self) -> Dict[str, dict]:
        loaded: Dict[str, dict] = {}
        for filename, meta in RUBRIC_FILE_MAP.items():
            path = self.rubric_dir / filename
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            normalized = self._normalize_rubric(raw, meta)
            loaded[normalized["rubric_id"]] = normalized

        self._rubrics = loaded
        logger.info(
            "Startup rubric load complete. loaded_rubrics=%s",
            [{"rubric_id": r["rubric_id"], "name": r.get("name")} for r in loaded.values()],
        )
        return loaded

    @property
    def rubrics(self) -> Dict[str, dict]:
        return self._rubrics

    def _normalize_rubric(self, raw: dict, meta: dict) -> dict:
        norm = dict(raw)

        norm["rubric_id"] = raw.get("rubric_id", meta["rubric_id"])
        norm["name"] = raw.get("name", meta["name"])
        norm["short_title"] = raw.get("short_title", meta.get("short_title", self._to_short_title(norm["name"])))
        norm["summary"] = raw.get("summary", meta.get("summary", self._to_summary(raw.get("description", ""))))

        scale_labels = raw.get("scale_labels") or raw.get("scale", {}).get("labels")
        norm["scale_labels"] = scale_labels or {
            "1": "Beginning",
            "2": "Developing",
            "3": "Proficient",
            "4": "Advanced",
        }

        letter_map = raw.get("letter_grade_map") or raw.get("scoring", {}).get("letter_grade_map") or []
        norm["letter_grade_map"] = self._normalize_letter_grade_map(letter_map)
        return norm

    def _to_short_title(self, name: str) -> str:
        title = (name or "").strip()
        if not title:
            return "Rubric"
        replacements = [
            ("College-Level ", ""),
            ("General Academic ", ""),
            ("Cross-Disciplinary ", ""),
            ("Analytical Writing ", ""),
            ("Rubric", ""),
        ]
        for source, target in replacements:
            title = title.replace(source, target)
        title = " ".join(title.split())
        return title if title else "Rubric"

    def _to_summary(self, description: str) -> str:
        desc = " ".join((description or "").split())
        if not desc:
            return "Evaluates writing quality using structured criteria."
        if "." in desc:
            sentence = desc.split(".", 1)[0].strip()
            if sentence:
                return sentence + "."
        return desc[:160].rstrip() + ("..." if len(desc) > 160 else "")

    def _normalize_letter_grade_map(self, rows: List[dict]) -> List[dict]:
        normalized: List[dict] = []
        for row in rows:
            if "min_score" in row and "letter" in row:
                normalized.append(
                    {
                        "min_score": float(row["min_score"]),
                        "letter": str(row["letter"]),
                    }
                )
                continue
            if "min_inclusive" in row and "grade" in row:
                normalized.append(
                    {
                        "min_score": float(row["min_inclusive"]),
                        "letter": str(row["grade"]),
                    }
                )
        return normalized
