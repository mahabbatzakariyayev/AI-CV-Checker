import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import LabelBadge from "../components/LabelBadge";
import Layout from "../components/Layout";
import { getCandidateDetails, getCandidateTrace } from "../services/api";
import { CandidateTraceStep } from "../types";
import { formatDateTime } from "../utils/time";

function formatScoringMode(mode: string) {
  if (mode === "gpt_5_full_ai_evaluation") {
    return "GPT-5.4 Full AI Evaluation";
  }
  if (mode === "gpt_rubric_with_deterministic_caps") {
    return "GPT-5.4 Rubric Scoring + Hard Caps";
  }
  if (mode === "deterministic_scoring") {
    return "Deterministic Scoring";
  }
  return mode;
}

export default function CandidateDetailPage() {
  const { jobId = "", candidateId = "" } = useParams();
  const [data, setData] = useState<any>(null);
  const [trace, setTrace] = useState<{ steps: CandidateTraceStep[] } | null>(null);

  useEffect(() => {
    getCandidateDetails(jobId, candidateId).then(setData);
    getCandidateTrace(jobId, candidateId).then(setTrace);
  }, [jobId, candidateId]);

  if (!data) {
    return <Layout title="Candidate Details" jobId={jobId}>Loading...</Layout>;
  }

  const { candidate, score, extraction_quality, parser_mode, scoring_mode } = data;
  const aiUsage = data.ai_usage;
  const scoringModeLabel = formatScoringMode(scoring_mode);
  return (
    <Layout title={`Candidate Detail: ${candidate.candidate_name || candidate.file_id}`} jobId={jobId}>
      <div className="grid">
        <div className="card">
          <h3>Summary</h3>
          <p>
            <strong>Score:</strong> {score.total_score}/1000 (cap {score.max_possible_score_after_caps})
          </p>
          <p>
            <strong>Recommendation:</strong> <LabelBadge label={score.recommendation_label} />
          </p>
          <p>
            <strong>Confidence:</strong> {score.confidence_level}
          </p>
          <p>
            <strong>Parser Mode:</strong> {parser_mode}
          </p>
          <p>
            <strong>Scoring Mode:</strong> {scoringModeLabel}
          </p>
          <p>
            <strong>AI Usage:</strong>{" "}
            Job Parser={aiUsage?.job_requirement_parser || "-"}, Candidate Parser=
            {aiUsage?.candidate_parser || parser_mode}, Explanation=
            {aiUsage?.explanation_engine || "langgraph_agentic"}
          </p>
          <p>
            <strong>Email:</strong> {candidate.email || "-"}
          </p>
          <p>
            <strong>Phone:</strong> {candidate.phone || "-"}
          </p>
          <p>
            <strong>Location:</strong> {candidate.location || "-"}
          </p>
          <p>
            <strong>Years Experience:</strong> {candidate.total_years_experience || "-"}
          </p>
        </div>

        <div className="card">
          <h3>Extraction Quality</h3>
          <p>
            Level: {extraction_quality.quality_level} ({extraction_quality.score}/100)
          </p>
          <ul>
            {extraction_quality.warnings?.map((warning: string) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <h3>Score Breakdown</h3>
        <pre>{JSON.stringify(score.score_breakdown, null, 2)}</pre>
      </div>

      <div className="card">
        <h3>Hard Requirement Checks</h3>
        <pre>{JSON.stringify(score.hard_requirements, null, 2)}</pre>
      </div>

      <div className="grid">
        <div className="card">
          <h3>Strengths</h3>
          <ul>{score.strengths.map((item: string) => <li key={item}>{item}</li>)}</ul>
        </div>
        <div className="card">
          <h3>Gaps</h3>
          <ul>{score.gaps.map((item: string) => <li key={item}>{item}</li>)}</ul>
        </div>
      </div>

      <div className="card">
        <h3>Concerns</h3>
        <ul>{score.concerns.map((item: string) => <li key={item}>{item}</li>)}</ul>
      </div>

      <div className="card">
        <h3>Evidence</h3>
        <pre>{JSON.stringify(score.evidence, null, 2)}</pre>
      </div>

      <div className="card">
        <h3>Interview Questions</h3>
        <ul>{score.interview_questions.map((item: string) => <li key={item}>{item}</li>)}</ul>
      </div>

      <div className="card">
        <h3>Candidate Processing Trace</h3>
        {!trace && <p>Loading trace...</p>}
        {trace?.steps?.map((step) => (
          <details key={step.id} style={{ marginBottom: 12 }}>
            <summary>
              [{step.level}] {formatDateTime(step.timestamp)} - {step.message}
              {step.step_key ? ` (${step.step_key})` : ""}
            </summary>
            <pre>{JSON.stringify(step.details, null, 2)}</pre>
          </details>
        ))}
      </div>
    </Layout>
  );
}
