import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import { createJob, listJobs } from "../services/api";
import { ScreeningJobListItem } from "../types";
import { formatDateTime, formatDuration } from "../utils/time";

export default function CreateJobPage() {
  const [title, setTitle] = useState("Senior AI Engineer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [jobs, setJobs] = useState<ScreeningJobListItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    listJobs().then(setJobs).catch(() => setJobs([]));
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const job = await createJob(title);
      navigate(`/jobs/${job.id}/setup`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to create screening job");
    } finally {
      setLoading(false);
    }
  };

  const filteredJobs = jobs.filter((job) => (statusFilter === "all" ? true : job.status === statusFilter));
  const completedJobs = jobs.filter((job) => job.status === "completed").length;
  const processingJobs = jobs.filter((job) => job.status === "processing" || job.status === "queued").length;
  const failedJobs = jobs.filter((job) => job.status === "failed").length;

  return (
    <Layout title="Create Screening Job">
      <form className="card form" onSubmit={onSubmit}>
        <label>
          Job Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} required minLength={2} />
        </label>
        {error && <div className="error">{error}</div>}
        <button disabled={loading}>{loading ? "Creating..." : "Create Job"}</button>
      </form>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-title">Total Jobs</div>
          <div className="stat-value">{jobs.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">Completed</div>
          <div className="stat-value">{completedJobs}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">In Progress</div>
          <div className="stat-value">{processingJobs}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">Failed</div>
          <div className="stat-value">{failedJobs}</div>
        </div>
      </div>
      <div className="card table-wrap">
        <div className="toolbar">
          <h3 className="toolbar-title">Existing Screening Jobs</h3>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All Statuses</option>
            {[...new Set(jobs.map((job) => job.status))].map((status) => (
              <option value={status} key={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Status</th>
              <th>Submitted</th>
              <th>Last Updated</th>
              <th>Duration</th>
              <th>Files</th>
              <th>Parser Mode</th>
              <th>Last Event</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredJobs.map((job) => (
              <tr key={job.id}>
                <td>{job.title}</td>
                <td>{job.status}</td>
                <td>{formatDateTime(job.submitted_at)}</td>
                <td>{formatDateTime(job.updated_at)}</td>
                <td>{formatDuration(job.analysis_duration_seconds)}</td>
                <td>
                  {job.processed_files}/{job.total_files} (failed {job.failed_files})
                </td>
                <td>{job.job_parser_mode}</td>
                <td>{job.last_event || "-"}</td>
                <td>
                  <Link to={`/jobs/${job.id}/setup`}>Setup</Link> |{" "}
                  <Link to={`/jobs/${job.id}/status`}>Status</Link> |{" "}
                  <Link to={`/jobs/${job.id}/ranking`}>Ranking</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
