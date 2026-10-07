export type ScreeningJob = {
  id: string;
  title: string;
  status: string;
};

export type ScreeningJobListItem = {
  id: string;
  title: string;
  status: string;
  submitted_at: string;
  created_at: string;
  updated_at: string;
  total_files: number;
  processed_files: number;
  failed_files: number;
  job_parser_mode: string;
  analysis_duration_seconds: number | null;
  last_event: string | null;
};

export type ScreeningStatus = {
  job_id: string;
  status: string;
  total_files: number;
  processed_files: number;
  failed_files: number;
  created_at: string;
  updated_at: string;
  errors: string[];
};

export type CandidateRow = {
  rank: number;
  candidate_id: string;
  candidate_name: string;
  email: string;
  phone: string;
  score: number;
  max_score_after_caps: number;
  recommendation: string;
  confidence: string;
  years_experience: number;
  candidate_created_at: string;
  score_created_at: string;
  strengths: string[];
  gaps: string[];
  extraction_quality: { quality_level: string; score: number };
  original_file_name: string;
  parser_mode: string;
  scoring_mode: string;
  ai_usage?: {
    job_requirement_parser: string;
    candidate_parser: string;
    scoring_engine: string;
    explanation_engine: string;
  };
};

export type CandidateTraceStep = {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  candidate_id: string | null;
  step_key?: string;
  details: Record<string, unknown>;
};
