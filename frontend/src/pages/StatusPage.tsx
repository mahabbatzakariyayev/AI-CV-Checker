import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import { getDiagnostics, getLogs, getStatus } from "../services/api";
import { ScreeningStatus } from "../types";
import { formatDateTime, formatDuration } from "../utils/time";

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

export default function StatusPage() {
  const { jobId = "" } = useParams();
  const [status, setStatus] = useState<ScreeningStatus | null>(null);
  const [logs, setLogs] = useState<Array<{ level: string; message: string; created_at: string }>>([]);
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [logFilter, setLogFilter] = useState("all");

  useEffect(() => {
    const fetchLogs = async () => {
      const [logsData, diagnosticsData] = await Promise.all([getLogs(jobId), getDiagnostics(jobId)]);
      setLogs(logsData);
      setDiagnostics(diagnosticsData);
    };
    getStatus(jobId).then(setStatus);
    fetchLogs();
    const logTimer = setInterval(fetchLogs, 3000);

    const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
    const stream = new EventSource(`${baseUrl}/api/screening-jobs/${jobId}/status/stream`);
    stream.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setStatus((prev) => ({
          ...(prev || {
            job_id: payload.job_id,
            created_at: "",
            updated_at: "",
            errors: []
          }),
          ...payload
        }));
      } catch {
        // ignore malformed events
      }
    };
    stream.onerror = () => {
      stream.close();
    };

    return () => {
      clearInterval(logTimer);
      stream.close();
    };
  }, [jobId]);

  const progress = status?.total_files ? Math.round((status.processed_files / status.total_files) * 100) : 0;
  const elapsedSeconds =
    status?.created_at && status?.updated_at
      ? Math.max(0, (new Date(status.updated_at).getTime() - new Date(status.created_at).getTime()) / 1000)
      : null;
  const filteredLogs = logs.filter((item) => (logFilter === "all" ? true : item.level === logFilter));
  return (
    <Layout title="Processing Status" jobId={jobId}>
      <div className="card">
        <p>Status: {status?.status || "loading..."}</p>
        <p>Submitted: {formatDateTime(status?.created_at)}</p>
        <p>Last Updated: {formatDateTime(status?.updated_at)}</p>
        <p>Elapsed: {formatDuration(elapsedSeconds)}</p>
        <p>Total files: {status?.total_files || 0}</p>
        <p>Processed: {status?.processed_files || 0}</p>
        <p>Failed: {status?.failed_files || 0}</p>
        <div className="progress">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
        {status?.status === "completed" && (
          <Link className="button-link" to={`/jobs/${jobId}/ranking`}>
            Open Candidate Ranking
          </Link>
        )}
        {diagnostics && (
          <div>
            <p>Job Parser Mode: {diagnostics.job_parser_mode}</p>
            <p>Scoring Mode: {formatScoringMode(diagnostics.scoring_mode)}</p>
            <p>
              Candidate Parser Modes: primary {diagnostics.candidate_primary_llm_count}, fallback{" "}
              {diagnostics.candidate_mock_fallback_count}
            </p>
          </div>
        )}
      </div>
      <div className="card">
        <div className="toolbar">
          <h3 className="toolbar-title">Logs</h3>
          <select value={logFilter} onChange={(event) => setLogFilter(event.target.value)}>
            <option value="all">All Logs</option>
            <option value="INFO">INFO</option>
            <option value="ERROR">ERROR</option>
          </select>
        </div>
        <div className="log-list">
          {filteredLogs.map((item, index) => (
            <div key={`${item.created_at}-${index}`} className={`log ${item.level.toLowerCase()}`}>
              [{item.level}] {formatDateTime(item.created_at)} - {item.message}
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
