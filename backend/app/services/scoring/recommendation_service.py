class RecommendationService:
    def recommend(
        self,
        total_score: int,
        all_critical_met: bool,
        extraction_quality: str,
        evidence_strength_ratio: float,
        severe_gap: bool,
        forced_label: str | None = None,
    ) -> tuple[str, str]:
        if forced_label:
            return forced_label, "Low"
        if extraction_quality in {"low", "failed"}:
            return "Manual Review Required", "Low"
        if total_score < 500:
            return "Insufficient Evidence", "Low"
        if total_score >= 950 and all_critical_met and evidence_strength_ratio >= 0.8 and not severe_gap:
            return "Highly Recommended for Interview", "High"
        if total_score >= 900 and all_critical_met and evidence_strength_ratio >= 0.7:
            return "Highly Recommended for Interview", "High"
        if total_score >= 850 and all_critical_met and not severe_gap:
            return "Recommended for Interview", "High"
        if total_score >= 780:
            return "Needs Recruiter Review", "Medium"
        if total_score >= 700:
            return "Borderline Match", "Medium"
        if total_score >= 600:
            return "Weak Match", "Low"
        return "Not Recommended Based on Current Evidence", "Low"
