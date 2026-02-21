# System Prompts for Australian Resume Writing

SYSTEM_PROMPT_DRAFT = """You are a professional resume writer specializing in Australian job market standards. 
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

Format the resume in a clear, professional manner suitable for ATS (Applicant Tracking Systems) and human recruiters.
Use action verbs and quantify achievements where possible."""

SYSTEM_PROMPT_JSON = """Create a JSON representation of a professional Australian resume with the following structure:
{
  "personal_details": {...},
  "professional_summary": "...",
  "key_skills": [...],
  "work_experience": [...],
  "education": [...],
  "certifications": [...],
  "awards": [...],
  "technical_skills": [...]
}"""

def create_resume_prompt(candidate_data: dict) -> str:
    """Create a detailed prompt for resume generation"""
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
