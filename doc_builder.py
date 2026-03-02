import logging
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path
from typing import Dict, List
import json
import html

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── Palette ────────────────────────────────────────────────────────────────
HEADING_COLOR  = RGBColor(0x1a, 0x37, 0x5e)   # deep navy
RULE_COLOR     = RGBColor(0x1a, 0x37, 0x5e)
MUTED_COLOR    = RGBColor(0x44, 0x55, 0x66)    # slate grey

BODY_FONT   = "Calibri"
HEADING_FONT = "Calibri"
NAME_SIZE   = Pt(20)
CONTACT_SIZE = Pt(10)
SECTION_SIZE = Pt(10)
BODY_SIZE   = Pt(10.5)


def _set_para_spacing(para, before: int = 0, after: int = 0, line: int = None):
    """Set paragraph spacing in twips (1 pt = 20 twips)."""
    pPr = para._p.get_or_add_pPr()
    spacing = OxmlElement('w:spacing')
    spacing.set(qn('w:before'), str(before * 20))
    spacing.set(qn('w:after'),  str(after  * 20))
    if line is not None:
        spacing.set(qn('w:line'), str(line))
        spacing.set(qn('w:lineRule'), 'auto')
    pPr.append(spacing)


def _add_horizontal_rule(doc: Document, color: RGBColor = RULE_COLOR):
    """Add a thin 0.5pt border below the paragraph (acts as a rule)."""
    para = doc.add_paragraph()
    _set_para_spacing(para, before=0, after=2)
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'),   'single')
    bottom.set(qn('w:sz'),    '4')   # 0.5 pt
    bottom.set(qn('w:space'), '1')
    r, g, b = color[0], color[1], color[2]
    bottom.set(qn('w:color'), f'{r:02X}{g:02X}{b:02X}')
    pBdr.append(bottom)
    pPr.append(pBdr)
    return para


def _section_heading(doc: Document, text: str):
    """Add a styled section heading with a rule below."""
    para = doc.add_paragraph()
    _set_para_spacing(para, before=8, after=1)
    run = para.add_run(text.upper())
    run.font.name    = HEADING_FONT
    run.font.size    = SECTION_SIZE
    run.font.bold    = True
    run.font.color.rgb = HEADING_COLOR
    _add_horizontal_rule(doc)


def _set_doc_margins(doc: Document):
    """Set page margins to 2.5 cm on all sides (A4)."""
    from docx.oxml.ns import qn
    for section in doc.sections:
        section.page_height = Cm(29.7)
        section.page_width  = Cm(21.0)
        margin = Cm(2.0)
        section.top_margin    = margin
        section.bottom_margin = margin
        section.left_margin   = Cm(2.2)
        section.right_margin  = Cm(2.2)


class ResumeBuilder:
    def __init__(self):
        self.resume_data: Dict = {}

    # ── Legacy collect methods (kept for compatibility) ─────────────────
    def collect_personal_info(self, name, contact_info):
        self.resume_data['name'] = name
        self.resume_data['contact_info'] = contact_info

    def collect_experience(self, experience):
        self.resume_data['experience'] = experience

    def collect_education(self, education):
        self.resume_data['education'] = education

    def build_resume_text(self) -> str:
        """Plain-text fallback."""
        resume = f"{self.resume_data.get('name', '')}\n"
        contact = self.resume_data.get('contact_info', {})
        if isinstance(contact, dict):
            resume += f"{contact.get('email', '')} | {contact.get('phone', '')} | {contact.get('location', '')}\n\n"
        resume += 'WORK EXPERIENCE\n'
        for exp in self.resume_data.get('experience', []):
            if isinstance(exp, dict):
                resume += f"  {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('dates', '')})\n"
        resume += '\nEDUCATION\n'
        for edu in self.resume_data.get('education', []):
            if isinstance(edu, dict):
                resume += f"  {edu.get('degree', '')} from {edu.get('institution', '')}\n"
        return resume

    # ── Main Word document builder ───────────────────────────────────────
    def build_word_document(self, output_path: str, candidate_data: Dict) -> str:
        """
        Build a professionally formatted Australian-style resume as a .docx file.
        Sections: Header, Professional Summary, Key Skills, Work Experience,
                  Education, Certifications, Awards, Technical Skills.
        """
        doc = Document()
        _set_doc_margins(doc)

        # Remove default Normal paragraph spacing
        normal = doc.styles['Normal']
        normal.font.name = BODY_FONT
        normal.font.size = BODY_SIZE

        contact: Dict = candidate_data.get('contact', {})

        # ── Header: Name ────────────────────────────────────────────────
        name_para = doc.add_paragraph()
        _set_para_spacing(name_para, before=0, after=2)
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        name_run = name_para.add_run(candidate_data.get('name', '').strip().upper())
        name_run.font.name  = HEADING_FONT
        name_run.font.size  = NAME_SIZE
        name_run.font.bold  = True
        name_run.font.color.rgb = HEADING_COLOR

        # ── Contact line ────────────────────────────────────────────────
        contact_parts = []
        if contact.get('phone'):    contact_parts.append(contact['phone'])
        if contact.get('email'):    contact_parts.append(contact['email'])
        if contact.get('location'): contact_parts.append(contact['location'])
        if contact.get('linkedin'): contact_parts.append(contact['linkedin'])

        contact_para = doc.add_paragraph()
        _set_para_spacing(contact_para, before=0, after=4)
        contact_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_run = contact_para.add_run('  ·  '.join(contact_parts))
        contact_run.font.name  = BODY_FONT
        contact_run.font.size  = CONTACT_SIZE
        contact_run.font.color.rgb = MUTED_COLOR

        # Thin rule under header
        _add_horizontal_rule(doc)

        # ── Professional Summary ────────────────────────────────────────
        summary = candidate_data.get('professional_summary', '').strip()
        if summary:
            _section_heading(doc, 'Professional Summary')
            p = doc.add_paragraph()
            _set_para_spacing(p, before=2, after=6, line=276)  # 1.15 line spacing
            r = p.add_run(summary)
            r.font.name = BODY_FONT
            r.font.size = BODY_SIZE

        # ── Key Skills ─────────────────────────────────────────────────
        key_skills = candidate_data.get('key_skills', [])
        if key_skills:
            _section_heading(doc, 'Key Skills')
            p = doc.add_paragraph()
            _set_para_spacing(p, before=2, after=6)
            r = p.add_run('  ·  '.join(str(s) for s in key_skills))
            r.font.name = BODY_FONT
            r.font.size = BODY_SIZE

        # ── Work Experience ─────────────────────────────────────────────
        experience = candidate_data.get('experience', [])
        if experience:
            _section_heading(doc, 'Work Experience')
            for i, exp in enumerate(experience):
                # Row 1: Job Title (bold) — right-aligned dates
                job_para = doc.add_paragraph()
                _set_para_spacing(job_para, before=4, after=0)
                title_run = job_para.add_run(exp.get('title', ''))
                title_run.font.name  = BODY_FONT
                title_run.font.size  = BODY_SIZE
                title_run.font.bold  = True

                dates = exp.get('dates', '')
                if dates:
                    # Tab-separated so dates float right via a right-aligned tab stop
                    tab_run = job_para.add_run('\t' + dates)
                    tab_run.font.name  = BODY_FONT
                    tab_run.font.size  = BODY_SIZE
                    tab_run.font.bold  = False
                    tab_run.font.color.rgb = MUTED_COLOR
                    # Add right-indent tab stop
                    from docx.oxml import OxmlElement
                    from docx.oxml.ns import qn
                    pPr = job_para._p.get_or_add_pPr()
                    tabs = OxmlElement('w:tabs')
                    tab = OxmlElement('w:tab')
                    tab.set(qn('w:val'), 'right')
                    # page width - margins ≈ 16.6 cm → 9400 twips
                    tab.set(qn('w:pos'), '9360')
                    tabs.append(tab)
                    pPr.append(tabs)

                # Row 2: Company  |  Location (italic, muted)
                company   = exp.get('company', '')
                location  = exp.get('location', '')
                sub_parts = [p for p in [company, location] if p]
                if sub_parts:
                    sub_para = doc.add_paragraph()
                    _set_para_spacing(sub_para, before=0, after=1)
                    sub_run = sub_para.add_run('  |  '.join(sub_parts))
                    sub_run.font.name    = BODY_FONT
                    sub_run.font.size    = BODY_SIZE
                    sub_run.font.italic  = True
                    sub_run.font.color.rgb = MUTED_COLOR

                # Description paragraph (if no bullets)
                description = exp.get('description', '').strip()
                bullets     = exp.get('bullets', [])

                if bullets:
                    for bullet in bullets:
                        bp = doc.add_paragraph(style='List Bullet')
                        _set_para_spacing(bp, before=1, after=1)
                        pPr = bp._p.get_or_add_pPr()
                        ind = OxmlElement('w:ind')
                        ind.set(qn('w:left'), '360')
                        ind.set(qn('w:hanging'), '180')
                        pPr.append(ind)
                        br = bp.add_run(str(bullet))
                        br.font.name = BODY_FONT
                        br.font.size = BODY_SIZE
                elif description:
                    dp = doc.add_paragraph()
                    _set_para_spacing(dp, before=1, after=1, line=276)
                    dr = dp.add_run(description)
                    dr.font.name = BODY_FONT
                    dr.font.size = BODY_SIZE

                # Spacing between jobs (except last)
                if i < len(experience) - 1:
                    sp = doc.add_paragraph()
                    _set_para_spacing(sp, before=0, after=3)

        # ── Education ──────────────────────────────────────────────────
        education = candidate_data.get('education', [])
        if education:
            _section_heading(doc, 'Education')
            for edu in education:
                degree = edu.get('degree', '')
                field  = edu.get('field',  '')
                grad   = edu.get('graduation_year', '')
                deg_text = f"{degree}{' — ' + field if field else ''}"

                edu_para = doc.add_paragraph()
                _set_para_spacing(edu_para, before=4, after=0)
                dr = edu_para.add_run(deg_text)
                dr.font.name = BODY_FONT
                dr.font.size = BODY_SIZE
                dr.font.bold = True
                if grad:
                    tab_run = edu_para.add_run('\t' + grad)
                    tab_run.font.name  = BODY_FONT
                    tab_run.font.size  = BODY_SIZE
                    tab_run.font.bold  = False
                    tab_run.font.color.rgb = MUTED_COLOR
                    pPr = edu_para._p.get_or_add_pPr()
                    tabs = OxmlElement('w:tabs')
                    tab_el = OxmlElement('w:tab')
                    tab_el.set(qn('w:val'), 'right')
                    tab_el.set(qn('w:pos'), '9360')
                    tabs.append(tab_el)
                    pPr.append(tabs)

                inst = edu.get('institution', '')
                if inst:
                    ip = doc.add_paragraph()
                    _set_para_spacing(ip, before=0, after=4)
                    ir = ip.add_run(inst)
                    ir.font.name    = BODY_FONT
                    ir.font.size    = BODY_SIZE
                    ir.font.italic  = True
                    ir.font.color.rgb = MUTED_COLOR

        # ── Certifications ─────────────────────────────────────────────
        certs = candidate_data.get('certifications', [])
        if certs:
            _section_heading(doc, 'Certifications')
            for cert in certs:
                cp = doc.add_paragraph(style='List Bullet')
                _set_para_spacing(cp, before=1, after=1)
                cr = cp.add_run(str(cert))
                cr.font.name = BODY_FONT
                cr.font.size = BODY_SIZE

        # ── Awards ─────────────────────────────────────────────────────
        awards = candidate_data.get('awards', [])
        if awards:
            _section_heading(doc, 'Awards & Recognition')
            for award in awards:
                ap = doc.add_paragraph(style='List Bullet')
                _set_para_spacing(ap, before=1, after=1)
                ar = ap.add_run(str(award))
                ar.font.name = BODY_FONT
                ar.font.size = BODY_SIZE

        # ── Technical Skills ───────────────────────────────────────────
        tech_skills = candidate_data.get('technical_skills', [])
        if tech_skills:
            _section_heading(doc, 'Technical Skills')
            p = doc.add_paragraph()
            _set_para_spacing(p, before=2, after=6)
            r = p.add_run('  ·  '.join(str(s) for s in tech_skills))
            r.font.name = BODY_FONT
            r.font.size = BODY_SIZE

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
        logger.info(f'Resume saved → {output_path}')
        return output_path

    # ── HTML preview builder ─────────────────────────────────────────────
    def build_html_preview(self, candidate_data: Dict) -> str:
        """
        Return a self-contained HTML string that visually matches the .docx layout.
        Styled to look like an A4 document with the same sections and formatting.
        """
        e = html.escape
        contact: Dict = candidate_data.get('contact', {})

        contact_parts = []
        if contact.get('phone'):    contact_parts.append(e(contact['phone']))
        if contact.get('email'):
            em = e(contact['email'])
            contact_parts.append(f'<a href="mailto:{em}">{em}</a>')
        if contact.get('location'): contact_parts.append(e(contact['location']))
        if contact.get('linkedin'):
            li = e(contact['linkedin'])
            contact_parts.append(f'<a href="https://{li}" target="_blank">{li}</a>')

        def section(title: str, body: str) -> str:
            return (
                f'<div class="section">'
                f'  <div class="section-heading">{e(title).upper()}</div>'
                f'  <div class="section-rule"></div>'
                f'  {body}'
                f'</div>'
            )

        body_parts: List[str] = []

        # Professional Summary
        summary = candidate_data.get('professional_summary', '').strip()
        if summary:
            body_parts.append(section('Professional Summary',
                f'<p class="body-text">{e(summary)}</p>'))

        # Key Skills
        key_skills = candidate_data.get('key_skills', [])
        if key_skills:
            skills_html = '  ·  '.join(e(str(s)) for s in key_skills)
            body_parts.append(section('Key Skills',
                f'<p class="body-text">{skills_html}</p>'))

        # Work Experience
        experience = candidate_data.get('experience', [])
        if experience:
            exp_html = ''
            for exp in experience:
                title    = e(exp.get('title',    ''))
                company  = e(exp.get('company',  ''))
                location = e(exp.get('location', ''))
                dates    = e(exp.get('dates',    ''))
                desc     = e(exp.get('description', '').strip())
                bullets  = exp.get('bullets', [])

                sub = '  |  '.join(p for p in [company, location] if p)

                exp_html += (
                    f'<div class="exp-entry">'
                    f'  <div class="exp-header">'
                    f'    <span class="exp-title">{title}</span>'
                    f'    <span class="exp-dates">{dates}</span>'
                    f'  </div>'
                    f'  <div class="exp-sub">{sub}</div>'
                )
                if bullets:
                    exp_html += '<ul class="exp-bullets">'
                    for b in bullets:
                        exp_html += f'<li>{e(str(b))}</li>'
                    exp_html += '</ul>'
                elif desc:
                    exp_html += f'<p class="body-text">{desc}</p>'
                exp_html += '</div>'
            body_parts.append(section('Work Experience', exp_html))

        # Education
        education = candidate_data.get('education', [])
        if education:
            edu_html = ''
            for edu in education:
                degree = e(edu.get('degree', ''))
                field  = e(edu.get('field',  ''))
                inst   = e(edu.get('institution', ''))
                grad   = e(edu.get('graduation_year', ''))
                deg_text = f"{degree}{' — ' + field if field else ''}"
                edu_html += (
                    f'<div class="edu-entry">'
                    f'  <div class="edu-header">'
                    f'    <span class="edu-degree">{deg_text}</span>'
                    f'    <span class="edu-year">{grad}</span>'
                    f'  </div>'
                    f'  <div class="edu-inst">{inst}</div>'
                    f'</div>'
                )
            body_parts.append(section('Education', edu_html))

        # Certifications
        certs = candidate_data.get('certifications', [])
        if certs:
            c_html = '<ul class="exp-bullets">' + ''.join(f'<li>{e(str(c))}</li>' for c in certs) + '</ul>'
            body_parts.append(section('Certifications', c_html))

        # Awards
        awards = candidate_data.get('awards', [])
        if awards:
            a_html = '<ul class="exp-bullets">' + ''.join(f'<li>{e(str(a))}</li>' for a in awards) + '</ul>'
            body_parts.append(section('Awards & Recognition', a_html))

        # Technical Skills
        tech_skills = candidate_data.get('technical_skills', [])
        if tech_skills:
            ts_html = '  ·  '.join(e(str(s)) for s in tech_skills)
            body_parts.append(section('Technical Skills',
                f'<p class="body-text">{ts_html}</p>'))

        name_html = e(candidate_data.get('name', '').strip().upper())
        contact_html = '  ·  '.join(contact_parts)

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Resume Preview</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Calibri, 'Segoe UI', Arial, sans-serif;
    font-size: 10.5pt;
    color: #222;
    background: #fff;
  }}
  .page {{
    width: 21cm;
    min-height: 29.7cm;
    padding: 2cm 2.2cm;
    margin: 0 auto;
    background: #fff;
  }}
  /* Header */
  .resume-name {{
    font-size: 20pt;
    font-weight: 700;
    color: #1a375e;
    text-align: center;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
  }}
  .resume-contact {{
    font-size: 9.5pt;
    color: #445566;
    text-align: center;
    margin-bottom: 10px;
  }}
  .resume-contact a {{ color: #445566; text-decoration: none; }}
  .header-rule {{
    border: none;
    border-top: 1.5px solid #1a375e;
    margin-bottom: 14px;
  }}
  /* Sections */
  .section {{ margin-bottom: 14px; }}
  .section-heading {{
    font-size: 9pt;
    font-weight: 700;
    color: #1a375e;
    letter-spacing: 0.08em;
    margin-bottom: 2px;
  }}
  .section-rule {{
    border-top: 1px solid #1a375e;
    margin-bottom: 6px;
  }}
  .body-text {{
    font-size: 10.5pt;
    line-height: 1.4;
    color: #222;
  }}
  /* Experience */
  .exp-entry {{ margin-bottom: 10px; }}
  .exp-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }}
  .exp-title  {{ font-weight: 700; font-size: 10.5pt; }}
  .exp-dates  {{ font-size: 10pt; color: #445566; }}
  .exp-sub    {{ font-style: italic; color: #445566; font-size: 10pt; margin-bottom: 4px; }}
  .exp-bullets {{
    margin-left: 1.1em;
    padding-left: 0.5em;
    font-size: 10.5pt;
    line-height: 1.5;
  }}
  .exp-bullets li {{ margin-bottom: 2px; }}
  /* Education */
  .edu-entry {{ margin-bottom: 8px; }}
  .edu-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }}
  .edu-degree {{ font-weight: 700; font-size: 10.5pt; }}
  .edu-year   {{ font-size: 10pt; color: #445566; }}
  .edu-inst   {{ font-style: italic; color: #445566; font-size: 10pt; }}
</style>
</head>
<body>
<div class="page">
  <div class="resume-name">{name_html}</div>
  <div class="resume-contact">{contact_html}</div>
  <hr class="header-rule"/>
  {''.join(body_parts)}
</div>
</body>
</html>'''


if __name__ == '__main__':
    # Quick smoke test
    sample = {
        "name": "Jane Smith",
        "contact": {
            "phone": "0412 345 678",
            "email": "jane.smith@email.com",
            "location": "Melbourne, VIC",
            "linkedin": "linkedin.com/in/janesmith"
        },
        "professional_summary": (
            "Experienced software engineer with 7+ years delivering scalable "
            "web applications for the Australian financial services sector."
        ),
        "key_skills": ["Python", "React", "AWS", "Agile", "CI/CD"],
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "ANZ Bank",
                "location": "Melbourne, VIC",
                "dates": "Jan 2020 – Present",
                "description": "",
                "bullets": [
                    "Led a team of 5 engineers delivering a $2M digital banking platform",
                    "Reduced deployment time by 60% through CI/CD pipeline optimisation",
                ]
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Computer Science",
                "field": "Software Engineering",
                "institution": "University of Melbourne",
                "graduation_year": "2016"
            }
        ],
        "certifications": ["AWS Certified Solutions Architect"],
        "awards": [],
        "technical_skills": ["Python", "JavaScript", "PostgreSQL", "Docker", "Kubernetes"]
    }
    builder = ResumeBuilder()
    builder.build_word_document('/tmp/test_resume.docx', sample)
    html_out = builder.build_html_preview(sample)
    with open('/tmp/test_resume.html', 'w') as f:
        f.write(html_out)
    print("Smoke test complete. Files: /tmp/test_resume.docx, /tmp/test_resume.html")
