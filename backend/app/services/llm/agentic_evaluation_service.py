from typing import TypedDict

from app.schemas.candidate import CandidateProfile
from app.schemas.job_requirement import JobRequirementProfile
from app.schemas.scoring import CandidateScoreResult
from app.services.llm.base import LLMClient


class EvaluationState(TypedDict):
    candidate: CandidateProfile
    job: JobRequirementProfile
    score: CandidateScoreResult
    explanation: dict
    interview_questions: list[str]


class AgenticEvaluationService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.graph = self._build_graph()

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph
        except ImportError:
            return None

        graph = StateGraph(EvaluationState)

        def explanation_node(state: EvaluationState):
            explanation = self.llm_client.generate_candidate_explanation(
                state["candidate"], state["job"], state["score"]
            )
            return {"explanation": explanation}

        def questions_node(state: EvaluationState):
            questions = self.llm_client.generate_interview_questions(
                state["candidate"], state["job"], state["score"]
            )
            return {"interview_questions": questions}

        graph.add_node("explain", explanation_node)
        graph.add_node("questions", questions_node)
        graph.set_entry_point("explain")
        graph.add_edge("explain", "questions")
        graph.add_edge("questions", END)
        return graph.compile()

    def run(self, candidate: CandidateProfile, job: JobRequirementProfile, score: CandidateScoreResult) -> tuple[dict, list[str]]:
        if not self.graph:
            explanation = self.llm_client.generate_candidate_explanation(candidate, job, score)
            questions = self.llm_client.generate_interview_questions(candidate, job, score)
            return explanation, questions

        state: EvaluationState = {
            "candidate": candidate,
            "job": job,
            "score": score,
            "explanation": {},
            "interview_questions": [],
        }
        result = self.graph.invoke(state)
        return result.get("explanation", {}), result.get("interview_questions", [])
