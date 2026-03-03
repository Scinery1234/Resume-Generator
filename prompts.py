"""
OpenAI prompt definitions and builder functions for the Resume Generator.

This module contains two separate prompt strategies:

1. **Document-based generation** (primary flow — POST /api/generate)
   - `SYSTEM_PROMPT_GENERATE` : expert Australian resume-writer persona with strict JSON output rules.
   - `build_generate_prompt`  : assembles the user-facing prompt from uploaded document text,
                                a job description, and optional additional information.

2. **Legacy wizard-based generation** (POST /api/generate-resume)
   - `SYSTEM_PROMPT_DRAFT`    : simpler prompt used to enhance a manually filled-in summary.
   - `create_resume_prompt`   : formats structured candidate data into a plain-text prompt.
"""

# ── Document-based AI generation (primary flow) ────────────────────────────

SYSTEM_PROMPT_GENERATE = """You are a highly experienced Australian professional resume writer with over 10 years of expertise creating compelling, tailored resumes for senior-level candidates across all industries.

Your task is to:
1. Extract all relevant information from the candidate's uploaded documents (old resumes, LinkedIn exports, cover letters, portfolios, or any other supporting material).
2. Carefully analyse the job description to identify the key skills, requirements, qualifications, and keywords the employer is looking for.
3. IMPORTANT: If the candidate provides additional information (responses to selection criteria, specific examples, achievements, etc.), you MUST actively incorporate this information into the resume. Use it to:
   - Create more targeted and relevant bullet points
   - Highlight specific achievements and examples
   - Address selection criteria directly
   - Strengthen the professional summary
   - Add relevant skills and experiences that align with the job requirements
4. Produce a tailored, professionally written Australian-style resume that:
   • Aligns the candidate's background precisely with the job requirements
   • Uses industry-specific keywords from the job description for ATS (Applicant Tracking System) optimisation
   • Quantifies achievements with concrete numbers, percentages, or dollar values wherever possible
   • Uses strong Australian English action verbs (led, delivered, implemented, drove, achieved, established, managed, reduced, increased, developed, etc.)
   • Follows current Australian resume conventions:
     - Professional summary (not an objective statement)
     - No photo, no date of birth, no references section
     - Dates in "Month Year – Month Year" format (e.g. "Jan 2019 – Mar 2022")
     - Location as "City, State" (e.g. "Sydney, NSW")
   • Is concise and ideally fits within 2 pages
   • Reflects a senior professional tone — confident, authoritative, achievement-focused

STRICT RULES:
- Extract contact details accurately from the documents — do NOT invent or guess phone numbers, emails, or addresses
- If the documents do not contain certain contact information, leave that field as an empty string
- Do NOT fabricate, invent, or embellish any experience, qualifications, dates, or company names
- Write a compelling 3–5 sentence professional summary specifically tailored to the job description
- Select 8–12 key skills that are the most relevant to the stated job requirements
- For each work experience entry, write 3–5 achievement-focused bullet points
- List education entries in reverse-chronological order (most recent first)
- Include certifications and awards only if they appear in the candidate's documents
- CRITICAL: If additional information is provided by the candidate, you MUST actively incorporate it throughout the resume. Use specific examples, achievements, and details from the additional information to create targeted bullet points and strengthen the professional summary. Do not ignore or minimize this information—it is essential for tailoring the resume to the job requirements.

You MUST respond with ONLY valid JSON — no prose, no markdown, no code fences, no explanation.
The JSON must strictly follow this exact schema (include every key even if the value is an empty string or empty list):

{
  "name": "Full Name",
  "contact": {
    "email": "email@example.com",
    "phone": "04XX XXX XXX",
    "location": "City, State",
    "linkedin": "linkedin.com/in/username"
  },
  "professional_summary": "3-5 sentence professional summary tailored to the specific role.",
  "key_skills": ["Skill 1", "Skill 2", "Skill 3"],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "location": "City, State",
      "dates": "Month Year – Month Year",
      "description": "",
      "bullets": [
        "Led a team of X engineers to deliver Y, resulting in Z% improvement in performance.",
        "Implemented X system that reduced Y by $Z annually."
      ]
    }
  ],
  "education": [
    {
      "degree": "Bachelor of Commerce",
      "field": "Finance",
      "institution": "University of Sydney",
      "graduation_year": "2012"
    }
  ],
  "certifications": ["Certification Name (Year)"],
  "awards": ["Award Name (Year)"],
  "technical_skills": ["Tool 1", "Tool 2", "Framework 3"]
}"""


def build_generate_prompt(documents_text: str, job_description: str, additional_info: str = "") -> str:
    """Assemble the user-facing prompt for document-based resume generation.

    The prompt is structured into clearly labelled sections so that the model
    can locate each piece of information reliably:

    - ``CANDIDATE DOCUMENTS``       — concatenated text extracted from all uploaded files.
    - ``JOB DESCRIPTION``           — the job ad pasted by the user.
    - ``ADDITIONAL INFORMATION``    — optional extra context (selection criteria responses,
                                      key achievements, etc.). When present, the model is
                                      explicitly instructed to weave this content throughout
                                      the resume rather than treating it as an afterthought.

    Parameters
    ----------
    documents_text : str
        Combined plain-text content extracted from the candidate's uploaded files.
        Each file's content is prefixed with ``--- filename ---`` for clarity.
    job_description : str
        The full job advertisement text provided by the user.
    additional_info : str, optional
        Free-form text with extra candidate context (e.g. selection criteria answers,
        notable achievements). Defaults to an empty string (section is omitted).

    Returns
    -------
    str
        The fully assembled user prompt to pass to the OpenAI chat completion API.
    """
    prompt = f"""Please create a professional, tailored Australian resume using the information below.

=== CANDIDATE DOCUMENTS ===
{documents_text}

=== JOB DESCRIPTION ===
{job_description}"""

    if additional_info and additional_info.strip():
        # Explicitly instruct the model to incorporate the additional information
        # throughout the resume, not just reference it once.
        prompt += f"""

=== ADDITIONAL INFORMATION (MUST BE INCORPORATED) ===
The candidate has provided the following CRITICAL additional information that MUST be actively incorporated into the resume. This information is essential and should be used to:

1. Create specific, targeted bullet points that directly address the job requirements
2. Highlight achievements and examples that match the selection criteria
3. Strengthen the professional summary with relevant details
4. Add or emphasize skills and experiences mentioned in this section
5. Ensure the resume directly responds to what the employer is looking for

ADDITIONAL INFORMATION PROVIDED BY CANDIDATE:
{additional_info.strip()}

IMPORTANT: Do not just reference this information—actively use it to craft compelling bullet points, enhance the professional summary, and ensure the resume directly addresses the job requirements. This information should be woven throughout the resume, not just mentioned once."""

    prompt += """

Instructions:
- Extract all relevant experience, skills, education, and contact details from the candidate documents above.
- Tailor the resume specifically to match the skills, keywords, and requirements in the job description.
- CRITICAL: If additional information was provided, you MUST actively incorporate it throughout the resume:
  * Use specific examples and achievements from the additional information in your bullet points
  * Reference selection criteria responses in the professional summary and experience sections
  * Ensure the additional information is woven into the resume naturally, not just added as a separate section
  * Make the resume directly address what the candidate highlighted in their additional information
- Respond with ONLY the JSON object — no other text before or after."""

    return prompt


# ── Legacy prompts (kept for /api/generate-resume wizard endpoint) ──────────

SYSTEM_PROMPT_DRAFT = """You are a professional resume writer specialising in Australian job market standards.
Create a well-formatted, professional resume based on the candidate information provided.
The resume should follow Australian resume conventions and include:
- Personal Details (Name, Contact Information)
- Professional Summary
- Key Skills
- Work Experience (with dates, company, location, and achievements)
- Education
- Certifications (if any)
- Awards (if any)
- Technical Skills

Format the resume clearly for ATS (Applicant Tracking Systems) and human recruiters.
Use action verbs and quantify achievements where possible."""


def create_resume_prompt(candidate_data: dict) -> str:
    """Build a plain-text prompt for the legacy wizard-based generation endpoint.

    This prompt is used by ``POST /api/generate-resume``, which accepts
    structured candidate data directly rather than uploaded documents. The
    model is asked to enhance the professional summary; the rest of the resume
    is built deterministically by :class:`doc_builder.ResumeBuilder`.

    Parameters
    ----------
    candidate_data : dict
        A dictionary matching the ``CandidateInput`` Pydantic model, containing
        keys such as ``name``, ``contact``, ``professional_summary``,
        ``key_skills``, ``experience``, ``education``, ``certifications``,
        ``awards``, and ``technical_skills``.

    Returns
    -------
    str
        A formatted plain-text prompt ready to be sent to the OpenAI API.
    """
    prompt = f"""Generate a professional resume for the following candidate:

Name: {candidate_data.get('name', 'N/A')}
Email: {candidate_data.get('contact', {}).get('email', 'N/A')}
Phone: {candidate_data.get('contact', {}).get('phone', 'N/A')}
Location: {candidate_data.get('contact', {}).get('location', 'N/A')}

Professional Summary:
{candidate_data.get('professional_summary', 'N/A')}

Key Skills: {', '.join(candidate_data.get('key_skills', []))}

Work Experience:
"""
    for exp in candidate_data.get('experience', []):
        prompt += f"""
- {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}, {exp.get('location', 'N/A')}
  Dates: {exp.get('dates', 'N/A')}
  Description: {exp.get('description', 'N/A')}
  Achievements:
"""
        for bullet in exp.get('bullets', []):
            prompt += f"  • {bullet}\n"

    prompt += "\nEducation:\n"
    for edu in candidate_data.get('education', []):
        prompt += f"- {edu.get('degree', 'N/A')} in {edu.get('field', 'N/A')} from {edu.get('institution', 'N/A')} ({edu.get('graduation_year', 'N/A')})\n"

    if candidate_data.get('certifications'):
        prompt += f"\nCertifications: {', '.join(candidate_data.get('certifications', []))}\n"

    if candidate_data.get('awards'):
        prompt += f"\nAwards: {', '.join(candidate_data.get('awards', []))}\n"

    if candidate_data.get('technical_skills'):
        prompt += f"\nTechnical Skills: {', '.join(candidate_data.get('technical_skills', []))}\n"

    return prompt
