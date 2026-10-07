from app.schemas.candidate import CandidateProfile


def test_candidate_schema_coerces_skill_list_and_named_lists():
    profile = CandidateProfile.model_validate(
        {
            "candidate_id": "c1",
            "file_id": "f1",
            "skills": [
                {"name": "Python", "category": "programming_language"},
                {"name": "FastAPI", "category": "framework"},
                {"name": "Azure OpenAI", "category": "cloud"},
            ],
            "certifications": [{"name": "Azure AI Engineer Associate"}],
            "languages": [{"language": "English"}],
            "extraction_quality": {
                "quality_level": "high",
                "score": 90,
                "text_length": 1000,
                "page_count": 2,
                "has_email": True,
                "has_phone": True,
                "detected_sections": ["experience"],
                "warnings": [],
                "requires_manual_review": False,
            },
        }
    )
    assert "Python" in profile.skills.programming_languages
    assert "FastAPI" in profile.skills.frameworks
    assert "Azure AI Engineer Associate" in profile.certifications
    assert "English" in profile.languages


def test_candidate_schema_allows_missing_extraction_quality():
    profile = CandidateProfile.model_validate({"candidate_id": "c2", "file_id": "f2"})
    assert profile.extraction_quality is None


def test_candidate_schema_coerces_nested_shapes():
    profile = CandidateProfile.model_validate(
        {
            "candidate_id": "c3",
            "file_id": "f3",
            "work_experience": {
                "company": "X",
                "role": "Engineer",
                "responsibilities": "Built APIs",
                "technologies": [{"name": "Python"}, "FastAPI"],
                "achievements": [{"text": "Reduced latency 30%"}],
            },
            "projects": {
                "name": "RAG Bot",
                "technologies": [{"skill": "Azure OpenAI"}],
            },
        }
    )
    assert len(profile.work_experience) == 1
    assert profile.work_experience[0].responsibilities == ["Built APIs"]
    assert "Python" in profile.work_experience[0].technologies
    assert profile.projects[0].technologies == ["Azure OpenAI"]
