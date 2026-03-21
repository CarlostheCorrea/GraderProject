from __future__ import annotations

from typing import Dict, List, Tuple

from services.output_sanitizer import sanitize_quotes


def _criterion_index(rubric_json: dict) -> Dict[str, dict]:
    idx: Dict[str, dict] = {}
    for category in rubric_json.get("categories", []):
        for criterion in category.get("criteria", []):
            idx[criterion["id"]] = {
                "category_id": category["id"],
                "category_weight": float(category.get("weight", 1.0)),
                "criterion_weight": float(criterion.get("weight", 1.0)),
                "criterion_desc": criterion.get("description", ""),
            }
    return idx


def enforce_conservative_coverage(grading_result: dict, rubric_json: dict) -> dict:
    criteria = grading_result.get("criteria", [])
    existing = {c.get("criterion_id"): c for c in criteria if c.get("criterion_id")}
    scale_labels = rubric_json.get("scale_labels", {"1": "Beginning", "2": "Developing", "3": "Proficient", "4": "Advanced"})

    for category in rubric_json.get("categories", []):
        for criterion in category.get("criteria", []):
            cid = criterion["id"]
            if cid not in existing:
                criteria.append(
                    {
                        "criterion_id": cid,
                        "score": 1,
                        "label": scale_labels.get("1", "Beginning"),
                        "evidence_quotes": ["Missing direct evidence for this criterion."],
                        "justification": "Required evidence was missing; conservative scoring applied.",
                    }
                )
                continue

            item = existing[cid]
            evidence_quotes = sanitize_quotes(item.get("evidence_quotes", []))
            item["evidence_quotes"] = evidence_quotes
            if not evidence_quotes:
                item["score"] = 1
                item["label"] = scale_labels.get("1", "Beginning")
                item["evidence_quotes"] = ["Missing direct evidence for this criterion."]
                item["justification"] = (
                    "The draft did not provide sufficient quoted evidence for this criterion, "
                    "so conservative scoring was applied."
                )

    grading_result["criteria"] = criteria
    if "confidence" not in grading_result:
        grading_result["confidence"] = 55
    return grading_result


def compute_scores(grading_result: dict, rubric_json: dict) -> Tuple[dict, float, str]:
    criteria_idx = _criterion_index(rubric_json)
    grouped: Dict[str, List[Tuple[float, float]]] = {}

    for item in grading_result.get("criteria", []):
        cid = item.get("criterion_id")
        if cid not in criteria_idx:
            continue
        meta = criteria_idx[cid]
        grouped.setdefault(meta["category_id"], []).append(
            (float(item.get("score", 1)), meta["criterion_weight"])
        )

    category_scores: Dict[str, float] = {}
    weighted_total = 0.0
    weight_sum = 0.0

    for category in rubric_json.get("categories", []):
        category_id = category["id"]
        category_weight = float(category.get("weight", 1.0))
        rows = grouped.get(category_id, [])

        if rows:
            crit_weight_sum = sum(w for _, w in rows)
            cat_score = sum(score * w for score, w in rows) / crit_weight_sum
        else:
            cat_score = 1.0

        category_scores[category_id] = round(cat_score, 2)
        weighted_total += cat_score * category_weight
        weight_sum += category_weight

    overall = weighted_total / weight_sum if weight_sum else 1.0
    overall = round(overall, 2)
    letter = letter_grade_for_score(overall, rubric_json)

    grading_result["category_scores"] = category_scores
    grading_result["overall_score_1_to_4"] = overall
    grading_result["letter_grade"] = letter
    return grading_result, overall, letter


def letter_grade_for_score(score_1_to_4: float, rubric_json: dict) -> str:
    mapping = rubric_json.get("letter_grade_map", [])
    ordered = sorted(mapping, key=lambda x: float(x.get("min_score", 0.0)), reverse=True)
    for row in ordered:
        if score_1_to_4 >= float(row.get("min_score", 0.0)):
            return str(row.get("letter", "F"))
    return "F"
