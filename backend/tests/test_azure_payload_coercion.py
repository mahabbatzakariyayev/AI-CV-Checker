from app.schemas.candidate import CandidateProfile
from app.schemas.job_requirement import JobRequirementProfile
from app.services.llm.azure_openai_client import AzureOpenAIClient


def test_candidate_payload_coercion_maps_nested_contact_and_skills():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    payload = {
        "candidate_id": "c1",
        "file_id": "f1",
        "full_name": "Mahabbat Zakariyayev",
        "contact": {
            "email": "candidate@example.com",
            "phone": "+994500000000",
            "location": "Baku, Azerbaijan",
            "linkedin": "https://linkedin.com/in/candidate",
        },
        "skills": {
            "languages": ["Python"],
            "backend_frameworks": ["FastAPI"],
            "cloud_platforms": ["Azure", "AWS"],
            "ai": ["LLMs", "RAG"],
            "tools": ["Docker"],
        },
        "work_experience": [
            {
                "job_title": "AI Engineer",
                "organization": "NOVUM",
                "description": ["Built APIs"],
                "skills": ["Python", "FastAPI"],
            }
        ],
        "languages": [{"language": "English"}],
    }
    coerced = client._coerce_payload(payload, CandidateProfile)
    assert coerced["candidate_name"] == "Mahabbat Zakariyayev"
    assert coerced["email"] == "candidate@example.com"
    assert coerced["skills"]["frameworks"] == ["FastAPI"]
    assert coerced["work_experience"][0]["role"] == "AI Engineer"


def test_candidate_payload_coercion_maps_experience_alias_and_spoken_languages():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    payload = {
        "candidate_id": "c1",
        "file_id": "f1",
        "full_name": "Mahabbat Zakariyayev",
        "technical_skills": {
            "programming_languages": ["Python"],
            "ai_ml": ["LLMs", "Azure OpenAI"],
        },
        "skills": {
            "languages": ["English", "French"],
            "soft_skills": ["Communication"],
        },
        "experience": [
            {
                "job_title": "AI Engineer",
                "company": "NOVUM",
                "description": ["Built RAG systems", "Integrated Python applications"],
            }
        ],
    }
    coerced = client._coerce_payload(payload, CandidateProfile)
    assert coerced["skills"]["programming_languages"] == ["Python"]
    assert coerced["skills"]["ai_ml"] == ["LLMs", "Azure OpenAI"]
    assert coerced["languages"] == ["English", "French"]
    assert coerced["work_experience"][0]["company"] == "NOVUM"


def test_job_payload_coercion_maps_nested_skill_sections():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    payload = {
        "title": "AI Engineer",
        "language_requirements": [{"language": "English", "required": True}],
        "skills": {
            "critical": [{"name": "Python", "weight": 0.25}],
            "must_have": [{"name": "FastAPI", "weight": 0.15}],
            "nice_to_have": [{"name": "Docker", "weight": 0.05}],
        },
        "industry": "Document AI",
        "location": "Remote",
    }
    coerced = client._coerce_payload(payload, JobRequirementProfile)
    assert coerced["job_title"] == "AI Engineer"
    assert coerced["required_languages"] == ["English"]
    assert coerced["critical_skills"][0]["name"] == "Python"
    assert coerced["location_requirements"] == ["Remote"]


def test_job_payload_coercion_maps_requirement_alias_keys():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    payload = {
        "title": "AI Engineer",
        "critical_requirements": [{"skill": "Python", "weight": 0.2}],
        "must_have_requirements": [{"skill": "Cloud platforms", "weight": 0.1}],
        "nice_to_have_requirements": [{"skill": "Docker", "weight": 0.05}],
    }
    coerced = client._coerce_payload(payload, JobRequirementProfile)
    assert coerced["critical_skills"][0]["skill"] == "Python"
    assert coerced["must_have_skills"][0]["skill"] == "Cloud platforms"
    assert coerced["nice_to_have_skills"][0]["skill"] == "Docker"


def test_job_payload_coercion_maps_top_level_skills_list():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    payload = {
        "title": "AI Engineer",
        "skills": [
            {"name": "Python", "importance": "critical", "weight": 80},
            {"name": "FastAPI", "importance": "must_have", "weight": 60},
            {"name": "Docker", "importance": "nice_to_have", "weight": 30},
        ],
    }
    coerced = client._coerce_payload(payload, JobRequirementProfile)
    assert coerced["critical_skills"][0]["skill"] == "Python"
    assert coerced["must_have_skills"][0]["skill"] == "FastAPI"
    assert coerced["nice_to_have_skills"][0]["skill"] == "Docker"


def test_skill_normalization_payload_coercion_maps_simple_list_shape():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    coerced = client._coerce_skill_normalization_payload({"skills": ["Python", "ReactJS"]})
    assert coerced["items"][0]["raw_skill"] == "Python"
    assert coerced["items"][1]["normalized_skill"] == "ReactJS"


def test_skill_normalization_payload_coercion_maps_normalized_skills_by_position():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    coerced = client._coerce_skill_normalization_payload(
        {"normalized_skills": ["Python", "Large Language Models"]},
        source_skills=["Python programming", "LLMs"],
    )
    assert coerced["items"][0]["raw_skill"] == "Python programming"
    assert coerced["items"][0]["normalized_skill"] == "Python"
    assert coerced["items"][1]["raw_skill"] == "LLMs"
    assert coerced["items"][1]["normalized_skill"] == "Large Language Models"


def test_llm_score_payload_coercion_maps_category_scores():
    client = AzureOpenAIClient.__new__(AzureOpenAIClient)
    coerced = client._coerce_llm_score_payload(
        {
            "overall_score": 905,
            "recommendation": "Highly Recommended for Interview",
            "confidence": "High",
            "category_scores": {
                "eligibility_and_must_have_fit": 240,
                "technical_depth": 200,
            },
            "skill_assessment": [
                {"skill": "Python", "score": 90, "max_score": 100, "evidence": "Used in work"},
                {"skill": "FastAPI", "score": 0, "max_score": 100, "evidence": "Not found"},
            ],
            "strengths": ["A"],
        }
    )
    assert coerced["total_score"] == 905
    assert coerced["recommendation_label"] == "Highly Recommended for Interview"
    assert coerced["confidence_level"] == "High"
    assert coerced["score_breakdown"]["eligibility_and_must_have_fit"] == 240
    assert coerced["hard_requirement_results"][0]["requirement"] == "Python"
    assert coerced["hard_requirement_results"][1]["status"] == "missing"
    assert coerced["strengths"] == ["A"]
