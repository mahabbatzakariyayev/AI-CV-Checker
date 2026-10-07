from app.schemas.job_requirement import JobRequirementProfile


def test_job_requirement_coerces_tool_dicts_to_strings():
    profile = JobRequirementProfile.model_validate(
        {
            "job_title": "Senior AI Engineer",
            "tools_and_platforms": [
                {"name": "Azure DevOps", "importance": "must_have", "weight": 0.04},
                {"skill": "Docker"},
                "Kubernetes",
            ],
        }
    )
    assert profile.tools_and_platforms == ["Azure DevOps", "Docker", "Kubernetes"]


def test_job_requirement_coerces_skill_requirements_for_azure_llm_shape():
    profile = JobRequirementProfile.model_validate(
        {
            "job_title": "Senior AI Engineer",
            "must_have_skills": [
                {"skill": "Azure DevOps", "importance": "must-have"},
                {"name": "Docker", "priority": "must-have"},
            ],
            "critical_skills": [
                {"skill": "Python", "importance": "critical"},
            ],
        }
    )
    assert profile.must_have_skills[0].normalized_skill == "azure_devops"
    assert profile.must_have_skills[0].importance == "must_have"
    assert profile.must_have_skills[1].skill == "Docker"
    assert profile.must_have_skills[1].importance == "must_have"
    assert profile.critical_skills[0].normalized_skill == "python"
