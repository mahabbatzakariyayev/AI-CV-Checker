# CV Screening & Candidate Ranking Platform

Production-oriented document intelligence platform for recruiter decision support.  
The system ingests a ZIP of CVs + job requirement (text or file), extracts structured data, applies strict evidence-based scoring over 1000 points, ranks candidates, explains results, and exports Excel/JSON reports.

## 1) What This Project Does

- Creates screening jobs with audit logs.
- Accepts CV ZIP uploads and job requirement text/file uploads.
- Extracts CV text from PDF, DOCX, TXT, and image files (OCR adapter).
- Calculates extraction quality and flags low-confidence cases.
- Builds structured `CandidateProfile` and `JobRequirementProfile`.
- Scores with strict deterministic 1000-point rubric + mandatory caps.
- Produces recommendation labels, strengths, gaps, concerns, evidence, and interview questions.
- Exports results in Excel and JSON.

## 2) Architecture Overview

### Backend (`FastAPI + SQLAlchemy + Pydantic`)

- `app/api`: HTTP endpoints for jobs, analysis, status, candidates, exports.
- `app/services/worker/analysis_worker.py`: async background analysis worker (thread pool abstraction).
- `app/services/pipeline/screening_pipeline.py`: end-to-end analysis orchestration.
- `app/services/document_extraction/*`: extractor adapters and quality checks.
- `app/services/llm/*`: LLM abstraction + mock + Azure OpenAI + LangChain/LangGraph agentic evaluation.
- `app/services/scoring/*`: deterministic scoring, caps, recommendations.
- `app/services/export/*`: Excel/JSON generation.
- `app/models/db_models.py`: relational data model.

### Frontend (`React + TypeScript + Vite`)

- Create job page.
- Setup page (ZIP + job requirement text/file).
- Status page with logs and progress.
- Ranked table with filtering/search.
- Candidate detail page.
- Export links.

## 3) Tech Stack

- Python, FastAPI, Pydantic v2, SQLAlchemy
- SQLite (local dev), PostgreSQL-ready design
- React, TypeScript, Vite
- LangChain + LangGraph (agentic explanation/question generation)
- PyMuPDF, python-docx, pytesseract adapter
- pandas + openpyxl exports
- pytest test suite

## 4) Setup

### Prerequisites

- Python 3.11+
- Node.js 20+

### Environment

Copy:

```bash
cp .env.example .env
```

Keep `.env` local. Never commit API keys, candidate documents, generated reports, application logs, or local databases. Rotate any credential immediately if it is exposed.

Set Azure mode if needed:

```env
LLM_BACKEND=azure
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.4
AZURE_OPENAI_API_VERSION=2024-10-21
DOCUMENT_INTELLIGENCE_PROVIDER=azure_document_intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
AZURE_DOCUMENT_INTELLIGENCE_API_VERSION=2024-11-30
AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout
```

### Backend Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Run

```bash
cd frontend
npm install
npm run dev
```

Set API base URL if backend is not on `http://localhost:8000`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## 5) Environment Variables

See `.env.example`:

- `APP_ENV`, `DATABASE_URL`
- `UPLOAD_DIR`, `EXPORT_DIR`
- `MAX_ZIP_SIZE_MB`, `MAX_FILE_SIZE_MB`, `MAX_FILES_PER_ZIP`
- `ANALYSIS_WORKER_MAX_WORKERS`, `STATUS_STREAM_INTERVAL_SECONDS`
- `LLM_BACKEND` (`mock` or `azure`)
- `LLM_PROVIDER`
- Azure OpenAI config
- Document intelligence provider config
- `ENABLE_OCR`

## 6) API Endpoints

- `POST /api/screening-jobs`
- `POST /api/screening-jobs/{job_id}/job-requirement/text`
- `POST /api/screening-jobs/{job_id}/job-requirement/file`
- `POST /api/screening-jobs/{job_id}/upload-cvs`
- `POST /api/screening-jobs/{job_id}/analyze`
- `GET /api/screening-jobs/{job_id}/status`
- `GET /api/screening-jobs/{job_id}/status/stream` (SSE progress stream)
- `GET /api/screening-jobs/{job_id}/candidates`
- `GET /api/screening-jobs/{job_id}/candidates/{candidate_id}`
- `GET /api/screening-jobs/{job_id}/logs`
- `GET /api/screening-jobs/{job_id}/export/excel`
- `GET /api/screening-jobs/{job_id}/export/json`
- `GET /api/health`

## 7) Scoring Model (1000 Points)

- A. Eligibility & must-have fit: 300
- B. Technical depth: 250
- C. Relevant experience: 180
- D. Project/achievement evidence: 100
- E. Seniority/ownership: 70
- F. Education/certs: 40
- G. Communication/language: 30
- H. Evidence confidence: 30

### Strict Caps

Implemented caps include:

- Missing critical skills (1 => 749, 2+ => 649)
- Min experience gap => 699
- Missing required language => 799
- Low extraction quality => 649
- Low evidence quality => 749
- Skills-only without project/work evidence => 779
- Extraction failure => score 0 / failed extraction
- Role alignment missing => 749

## 8) Recommendation Labels

- `Highly Recommended for Interview`
- `Recommended for Interview`
- `Needs Recruiter Review`
- `Borderline Match`
- `Weak Match`
- `Not Recommended Based on Current Evidence`
- `Manual Review Required`
- `Insufficient Evidence`
- `Failed Extraction`

## 9) Document Extraction Strategy

- PDF: PyMuPDF extraction + scanned detection heuristics, or Azure Document Intelligence when enabled.
- DOCX: paragraphs + tables + header/footer inclusion.
- TXT: direct extraction.
- Image/scanned files: OCR adapter (`pytesseract`) or `OCR_REQUIRED` warning.
- Quality scoring checks for text length, empty pages, contact data, and section detection.

## 10) LangChain / LangGraph Agentic Side

- `AzureOpenAIClient` uses `langchain-openai`.
- `AgenticEvaluationService` uses `langgraph` `StateGraph`:
  - explanation node
  - interview-question node
- Deterministic scoring remains authoritative; agentic layer only enriches explanations/questions.

## 11) Safety & Fairness

- Sensitive attributes are not used in scoring:
  age, gender, nationality, religion, marital status, ethnicity, appearance, disability, political views, family status.
- System messaging warns: decision support only; humans make final hiring decisions.

## 12) Testing

Run:

```bash
cd backend
pytest
```

Covered tests:

- ZIP extraction security
- File validation
- CV text extraction
- Extraction quality scoring
- Job requirement parsing schema
- Skill normalization
- Scoring engine behavior
- Score caps
- Recommendation labels
- Export generation

## 13) Limitations

- Local `.doc` parsing is limited; conversion service should be added for production.
- OCR confidence is heuristic in local mode.
- Current semantic matching uses lightweight similarity placeholder.
- Background worker currently uses in-process thread pool abstraction (good for local/single-node runtime).
- Azure Document Intelligence requires valid endpoint/key and installed SDK package.

## 14) Production Improvements

- Azure Blob Storage adapter
- Queue worker (Celery/RQ/Azure Service Bus)
- Azure Document Intelligence model/feature tuning per document family
- Azure OpenAI structured outputs hardening
- Embeddings + Azure AI Search hybrid retrieval
- AuthN/AuthZ with Microsoft Entra ID
- PostgreSQL + Alembic migrations
