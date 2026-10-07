from app.services.scoring.recommendation_service import RecommendationService


def test_recommendation_strict_threshold():
    service = RecommendationService()
    label, confidence = service.recommend(
        total_score=930,
        all_critical_met=True,
        extraction_quality="high",
        evidence_strength_ratio=0.8,
        severe_gap=False,
    )
    assert label == "Highly Recommended for Interview"
    assert confidence == "High"
