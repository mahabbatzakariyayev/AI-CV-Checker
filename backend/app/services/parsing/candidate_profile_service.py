from app.schemas.candidate import CandidateProfile
from app.schemas.extraction import ExtractedDocument
from app.services.llm.base import LLMClient


class CandidateProfileService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def extract_profile(self, candidate_id: str, file_id: str, document: ExtractedDocument) -> CandidateProfile:
        return self.llm_client.extract_candidate_profile(candidate_id=candidate_id, file_id=file_id, document=document)
