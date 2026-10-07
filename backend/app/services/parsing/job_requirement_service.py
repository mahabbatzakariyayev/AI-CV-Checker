from app.schemas.job_requirement import JobRequirementProfile
from app.services.llm.base import LLMClient


class JobRequirementService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def parse(self, job_text: str) -> JobRequirementProfile:
        return self.llm_client.extract_job_requirement(job_text)
