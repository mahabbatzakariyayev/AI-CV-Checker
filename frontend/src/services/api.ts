import axios from "axios";
import { CandidateRow, ScreeningJob, ScreeningJobListItem, ScreeningStatus } from "../types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || ""
});

export const createJob = async (title: string): Promise<ScreeningJob> => {
  const { data } = await api.post("/api/screening-jobs", { title });
  return data;
};

export const listJobs = async (): Promise<ScreeningJobListItem[]> => {
  const { data } = await api.get("/api/screening-jobs");
  return data;
};

export const submitJobRequirementText = async (jobId: string, text: string) => {
  await api.post(`/api/screening-jobs/${jobId}/job-requirement/text`, { text });
};

export const submitJobRequirementFile = async (jobId: string, file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  await api.post(`/api/screening-jobs/${jobId}/job-requirement/file`, formData);
};

export const uploadCvZip = async (jobId: string, file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  await api.post(`/api/screening-jobs/${jobId}/upload-cvs`, formData);
};

export const analyzeJob = async (jobId: string) => {
  await api.post(`/api/screening-jobs/${jobId}/analyze`);
};

export const getStatus = async (jobId: string): Promise<ScreeningStatus> => {
  const { data } = await api.get(`/api/screening-jobs/${jobId}/status`);
  return data;
};

export const getLogs = async (jobId: string): Promise<Array<{ level: string; message: string; created_at: string }>> => {
  const { data } = await api.get(`/api/screening-jobs/${jobId}/logs`);
  return data;
};

export const getDiagnostics = async (jobId: string) => {
  const { data } = await api.get(`/api/screening-jobs/${jobId}/diagnostics`);
  return data;
};

export const getCandidates = async (jobId: string): Promise<CandidateRow[]> => {
  const { data } = await api.get(`/api/screening-jobs/${jobId}/candidates`);
  return data;
};

export const getCandidateDetails = async (jobId: string, candidateId: string) => {
  const { data } = await api.get(`/api/screening-jobs/${jobId}/candidates/${candidateId}`);
  return data;
};

export const getCandidateTrace = async (jobId: string, candidateId: string) => {
  const { data } = await api.get(`/api/screening-jobs/${jobId}/candidates/${candidateId}/trace`);
  return data;
};

export const exportExcelUrl = (jobId: string) => `${api.defaults.baseURL || ""}/api/screening-jobs/${jobId}/export/excel`;
export const exportJsonUrl = (jobId: string) => `${api.defaults.baseURL || ""}/api/screening-jobs/${jobId}/export/json`;
