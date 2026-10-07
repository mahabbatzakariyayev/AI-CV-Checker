import { FormEvent, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import { analyzeJob, submitJobRequirementFile, submitJobRequirementText, uploadCvZip } from "../services/api";

export default function JobSetupPage() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const [jobText, setJobText] = useState("");
  const [jobFile, setJobFile] = useState<File | null>(null);
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    try {
      if (jobText.trim()) {
        await submitJobRequirementText(jobId, jobText.trim());
      } else if (jobFile) {
        await submitJobRequirementFile(jobId, jobFile);
      } else {
        throw new Error("Provide job requirement text or file.");
      }
      if (!zipFile) throw new Error("Upload a CV ZIP file.");
      await uploadCvZip(jobId, zipFile);
      await analyzeJob(jobId);
      navigate(`/jobs/${jobId}/status`);
    } catch (e: any) {
      setStatus(e?.response?.data?.detail || e.message || "Setup failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout title="Job Setup" jobId={jobId}>
      <form className="card form" onSubmit={submit}>
        <label>
          CV ZIP Upload
          <input type="file" accept=".zip" onChange={(event) => setZipFile(event.target.files?.[0] || null)} required />
        </label>

        <label>
          Job Requirement (Text)
          <textarea rows={8} value={jobText} onChange={(event) => setJobText(event.target.value)} placeholder="Paste job requirement here..." />
        </label>
        <label>
          Or Upload Job Requirement File (PDF/DOCX/TXT)
          <input type="file" accept=".pdf,.docx,.txt" onChange={(event) => setJobFile(event.target.files?.[0] || null)} />
        </label>
        {status && <div className="error">{status}</div>}
        <button disabled={busy}>{busy ? "Analyzing..." : "Analyze"}</button>
      </form>
    </Layout>
  );
}
