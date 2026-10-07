from abc import ABC, abstractmethod

from app.schemas.candidate import CandidateProfile
from app.schemas.extraction import ExtractedDocument
from app.schemas.job_requirement import JobRequirementProfile
from app.schemas.scoring import CandidateScoreResult, LLMScoreAssessment, SkillNormalizationResult


class LLMClient(ABC):
    @abstractmethod
    def extract_candidate_profile(self, candidate_id: str, file_id: str, document: ExtractedDocument) -> CandidateProfile:
        raise NotImplementedError

    @abstractmethod
    def extract_job_requirement(self, text: str) -> JobRequirementProfile:
        raise NotImplementedError

    @abstractmethod
    def generate_candidate_explanation(
        self, candidate: CandidateProfile, job: JobRequirementProfile, score: CandidateScoreResult
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def generate_interview_questions(
        self, candidate: CandidateProfile, job: JobRequirementProfile, score: CandidateScoreResult
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def normalize_skills(self, skills: list[str], context: str = "") -> SkillNormalizationResult:
        raise NotImplementedError

    @abstractmethod
    def score_candidate_structured(
        self, candidate: CandidateProfile, job: JobRequirementProfile
    ) -> LLMScoreAssessment:
        raise NotImplementedError

    def drain_debug_traces(self) -> list[dict]:
        return []
