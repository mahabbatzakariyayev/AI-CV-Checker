import { Navigate, Route, Routes } from "react-router-dom";
import CandidateDetailPage from "./pages/CandidateDetailPage";
import CreateJobPage from "./pages/CreateJobPage";
import JobSetupPage from "./pages/JobSetupPage";
import RankingPage from "./pages/RankingPage";
import StatusPage from "./pages/StatusPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<CreateJobPage />} />
      <Route path="/jobs/:jobId/setup" element={<JobSetupPage />} />
      <Route path="/jobs/:jobId/status" element={<StatusPage />} />
      <Route path="/jobs/:jobId/ranking" element={<RankingPage />} />
      <Route path="/jobs/:jobId/candidates/:candidateId" element={<CandidateDetailPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
