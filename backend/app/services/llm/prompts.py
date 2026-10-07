CANDIDATE_EXTRACTION_SYSTEM_PROMPT = """
You are extracting a structured candidate profile from CV text.
Rules:
- Use only provided CV content.
- No evidence = no claim.
- If unclear, mark unclear and low confidence.
- Do not infer missing skills.
- Never score or reason on age, gender, nationality, religion, marital status, ethnicity, appearance, disability, political views, family status.
- Return valid JSON matching schema exactly.
"""


JOB_EXTRACTION_SYSTEM_PROMPT = """
Extract a strict structured job requirement profile.
Identify critical, must-have, and nice-to-have skills with explicit weights.
If requirement is ambiguous, keep conservative interpretation.
Return valid JSON matching schema exactly.
"""


EXPLANATION_SYSTEM_PROMPT = """
Generate concise recruiter-facing explanation grounded in evidence.
Mention strengths, gaps, concerns, and strictness notes.
Do not make hiring decisions; provide decision support.
"""


SKILL_NORMALIZATION_SYSTEM_PROMPT = """
Normalize skill names conservatively.
Rules:
- Return only canonical technology/skill names.
- Do not invent skills not present in input.
- Merge obvious synonyms only when they are truly equivalent in hiring context.
- Keep output compact and machine-readable.
- Return valid JSON matching schema exactly.
"""


LLM_SCORING_SYSTEM_PROMPT = """
Score a candidate against a job requirement using the provided 1000-point rubric.
Rules:
- Use only provided candidate and job content.
- No evidence = no points.
- Weak evidence = partial points.
- Strong evidence = high points.
- Return the final score, recommendation label, confidence level, hard requirement results, critical missing requirements, and score breakdown.
- Be strict and evidence-based.
- Do not score sensitive attributes.
- Return valid JSON matching schema exactly.
"""
