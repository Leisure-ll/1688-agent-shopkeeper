#!/usr/bin/env python3
"""Goal drift reviewer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Set

from .state import Plan


@dataclass
class ReviewResult:
    drift: bool
    reason: str
    suggestion: str = ""


class Reviewer:
    """Lightweight deterministic reviewer for the demo.

    A production version can replace this with a structured LLM call. Keeping
    the interface separate makes that swap small and easy to explain.
    """

    def review(self, original_goal: str, plan: Plan, recent_activity: Iterable[str]) -> ReviewResult:
        goal_terms = self._terms(original_goal)
        activity_terms = self._terms(" ".join(recent_activity))
        if not activity_terms:
            return ReviewResult(False, "no activity yet")

        overlap = goal_terms & activity_terms
        ecommerce_terms = {"1688", "商品", "选品", "铺货", "店铺", "趋势", "商机", "抖店", "淘宝", "拼多多", "小红书"}
        original_text = original_goal.lower()
        activity_text = " ".join(recent_activity).lower()
        goal_in_domain = bool(goal_terms & ecommerce_terms) or any(term in original_text for term in ecommerce_terms)
        activity_in_domain = bool(activity_terms & ecommerce_terms) or any(term in activity_text for term in ecommerce_terms)

        if goal_in_domain and not activity_in_domain:
            return ReviewResult(True, "recent activity left the 1688/e-commerce domain", "rollback and re-plan around 1688 tools")
        if goal_in_domain and activity_in_domain:
            return ReviewResult(False, "activity remains inside the e-commerce domain")
        if goal_terms and len(overlap) / max(len(goal_terms), 1) < 0.08:
            return ReviewResult(True, "recent activity has little lexical overlap with the original goal", "re-check plan goals")
        return ReviewResult(False, "activity remains aligned")

    def _terms(self, text: str) -> Set[str]:
        return {term.lower() for term in re.findall(r"[\w\u4e00-\u9fff]{2,}", text)}
