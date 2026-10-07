import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import LabelBadge from "../components/LabelBadge";
import Layout from "../components/Layout";
import { exportExcelUrl, exportJsonUrl, getCandidates } from "../services/api";
import { CandidateRow } from "../types";
import { formatDateTime } from "../utils/time";

function formatScoringMode(mode: string) {
  if (mode === "gpt_5_full_ai_evaluation") {
    return "GPT-5.4 Full AI Evaluation";
  }
  if (mode === "gpt_rubric_with_deterministic_caps") {
    return "GPT-5.4 Rubric + Caps";
  }
  if (mode === "deterministic_scoring") {
    return "Deterministic";
  }
  return mode;
}

export default function RankingPage() {
  const { jobId = "" } = useParams();
  const [rows, setRows] = useState<CandidateRow[]>([]);
  const [search, setSearch] = useState("");
  const [labelFilter, setLabelFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score_desc");

  useEffect(() => {
    getCandidates(jobId).then(setRows);
  }, [jobId]);

  const filtered = useMemo(() => {
    const query = search.toLowerCase();
    const filteredRows = rows.filter((row) => {
      const searchable = `${row.candidate_name} ${row.strengths.join(" ")} ${row.gaps.join(" ")}`.toLowerCase();
      const matchSearch = query ? searchable.includes(query) : true;
      const matchLabel = labelFilter === "all" ? true : row.recommendation === labelFilter;
      return matchSearch && matchLabel;
    });
    return [...filteredRows].sort((a, b) => {
      if (sortBy === "score_desc") return b.score - a.score;
      if (sortBy === "score_asc") return a.score - b.score;
      if (sortBy === "name_asc") return (a.candidate_name || "").localeCompare(b.candidate_name || "");
      if (sortBy === "name_desc") return (b.candidate_name || "").localeCompare(a.candidate_name || "");
      if (sortBy === "recent") return new Date(b.score_created_at).getTime() - new Date(a.score_created_at).getTime();
      return 0;
    });
  }, [rows, search, labelFilter, sortBy]);

  const avgScore = filtered.length ? Math.round(filtered.reduce((sum, row) => sum + row.score, 0) / filtered.length) : 0;
  const topScore = filtered.length ? Math.max(...filtered.map((row) => row.score)) : 0;
  const recommendedCount = filtered.filter((row) => row.recommendation.includes("Recommended")).length;

  return (
    <Layout title="Candidate Ranking" jobId={jobId}>
      <div className="card toolbar">
        <input placeholder="Search by candidate name or skill..." value={search} onChange={(event) => setSearch(event.target.value)} />
        <select value={labelFilter} onChange={(event) => setLabelFilter(event.target.value)}>
          <option value="all">All Recommendations</option>
          {[...new Set(rows.map((row) => row.recommendation))].map((label) => (
            <option value={label} key={label}>
              {label}
            </option>
          ))}
        </select>
        <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
          <option value="score_desc">Score: High to Low</option>
          <option value="score_asc">Score: Low to High</option>
          <option value="name_asc">Name: A-Z</option>
          <option value="name_desc">Name: Z-A</option>
          <option value="recent">Most Recently Processed</option>
        </select>
        <a className="button-link" href={exportExcelUrl(jobId)}>
          Export Excel
        </a>
        <a className="button-link" href={exportJsonUrl(jobId)}>
          Export JSON
        </a>
      </div>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-title">Candidates</div>
          <div className="stat-value">{filtered.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">Average Score</div>
          <div className="stat-value">{avgScore}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">Top Score</div>
          <div className="stat-value">{topScore}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">Recommended</div>
          <div className="stat-value">{recommendedCount}</div>
        </div>
      </div>

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Candidate</th>
              <th>Score</th>
              <th>Recommendation</th>
              <th>Confidence</th>
              <th>Years Exp</th>
              <th>Processed At</th>
              <th>Top Strengths</th>
              <th>Main Gaps</th>
              <th>Extraction</th>
              <th>Parser</th>
              <th>Scoring</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.candidate_id}>
                <td>{row.rank}</td>
                <td>{row.candidate_name || row.original_file_name}</td>
                <td>{row.score}/1000</td>
                <td>
                  <LabelBadge label={row.recommendation} />
                </td>
                <td>{row.confidence}</td>
                <td>{row.years_experience ?? "-"}</td>
                <td>{formatDateTime(row.score_created_at)}</td>
                <td>{row.strengths.slice(0, 2).join("; ")}</td>
                <td>{row.gaps.slice(0, 2).join("; ")}</td>
                <td>
                  {row.extraction_quality.quality_level} ({row.extraction_quality.score})
                </td>
                <td>{row.parser_mode}</td>
                <td>{formatScoringMode(row.scoring_mode)}</td>
                <td>
                  <Link to={`/jobs/${jobId}/candidates/${row.candidate_id}`}>View</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
