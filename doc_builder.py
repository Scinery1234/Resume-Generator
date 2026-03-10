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

# ── Template Definitions ────────────────────────────────────────────────────
TEMPLATES = {
    "modern": {
        "heading_color": RGBColor(0x1a, 0x37, 0x5e),   # deep navy
        "rule_color":    RGBColor(0x1a, 0x37, 0x5e),
        "muted_color":   RGBColor(0x44, 0x55, 0x66),   # slate grey
        "body_font":     "Calibri",
        "heading_font":  "Calibri",
        "name_size":     Pt(20),
        "contact_size":  Pt(10),
        "section_size":  Pt(10),
        "body_size":     Pt(10.5),
        "name_align":    WD_ALIGN_PARAGRAPH.CENTER,
        "section_rule":  True,
        # HTML colours
        "html_heading":  "#1a375e",
        "html_rule":     "#1a375e",
        "html_muted":    "#445566",
        "html_name_size": "20pt",
        "html_body_size": "10.5pt",
        "html_section_size": "9pt",
        "html_contact_size": "9.5pt",
        "html_accent_bg": None,
    },
    "classic": {
        "heading_color": RGBColor(0x1a, 0x1a, 0x1a),   # near black
        "rule_color":    RGBColor(0x33, 0x33, 0x33),
        "muted_color":   RGBColor(0x55, 0x55, 0x55),
        "body_font":     "Georgia",
        "heading_font":  "Georgia",
        "name_size":     Pt(18),
        "contact_size":  Pt(10),
        "section_size":  Pt(10),
        "body_size":     Pt(10.5),
        "name_align":    WD_ALIGN_PARAGRAPH.CENTER,
        "section_rule":  True,
        "html_heading":  "#1a1a1a",
        "html_rule":     "#333333",
        "html_muted":    "#555555",
        "html_name_size": "18pt",
        "html_body_size": "10.5pt",
        "html_section_size": "9.5pt",
        "html_contact_size": "10pt",
        "html_accent_bg": None,
    },
    "creative": {
        "heading_color": RGBColor(0x6b, 0x21, 0xa8),   # purple
        "rule_color":    RGBColor(0x08, 0x91, 0xb2),   # teal
        "muted_color":   RGBColor(0x4b, 0x55, 0x63),
        "body_font":     "Calibri",
        "heading_font":  "Calibri",
        "name_size":     Pt(22),
        "contact_size":  Pt(10),
        "section_size":  Pt(10),
        "body_size":     Pt(10.5),
        "name_align":    WD_ALIGN_PARAGRAPH.LEFT,
        "section_rule":  True,
        "html_heading":  "#6b21a8",
        "html_rule":     "#0891b2",
        "html_muted":    "#4b5563",
        "html_name_size": "22pt",
        "html_body_size": "10.5pt",
        "html_section_size": "9pt",
        "html_contact_size": "9.5pt",
        "html_accent_bg": None,
    },
    "minimal": {
        "heading_color": RGBColor(0x37, 0x41, 0x51),   # dark slate
        "rule_color":    RGBColor(0xd1, 0xd5, 0xdb),   # light gray
        "muted_color":   RGBColor(0x6b, 0x72, 0x80),
        "body_font":     "Calibri",
        "heading_font":  "Calibri",
        "name_size":     Pt(19),
        "contact_size":  Pt(10),
        "section_size":  Pt(9),
        "body_size":     Pt(10.5),
        "name_align":    WD_ALIGN_PARAGRAPH.LEFT,
        "section_rule":  True,
        "html_heading":  "#374151",
        "html_rule":     "#d1d5db",
        "html_muted":    "#6b7280",
        "html_name_size": "19pt",
        "html_body_size": "10.5pt",
        "html_section_size": "8.5pt",
        "html_contact_size": "9.5pt",
        "html_accent_bg": None,
    },
    "executive": {
        "heading_color": RGBColor(0x1c, 0x1c, 0x2e),   # near-black deep charcoal
        "rule_color":    RGBColor(0xb4, 0x53, 0x09),   # warm amber-gold
        "muted_color":   RGBColor(0x52, 0x52, 0x52),
        "body_font":     "Calibri",
        "heading_font":  "Calibri",
        "name_size":     Pt(22),
        "contact_size":  Pt(10),
        "section_size":  Pt(9.5),
        "body_size":     Pt(10.5),
        "name_align":    WD_ALIGN_PARAGRAPH.LEFT,
        "section_rule":  True,
        "html_heading":  "#1c1c2e",
        "html_rule":     "#b45309",
        "html_muted":    "#525252",
        "html_name_size": "22pt",
        "html_body_size": "10.5pt",
        "html_section_size": "9.5pt",
        "html_contact_size": "9.5pt",
        "html_accent_bg": None,
    },
}

# Available template IDs and metadata (used by the API)
TEMPLATE_LIST = [
    {
        "id": "modern",
        "name": "Modern",
        "description": "Clean navy-blue design — polished and professional.",
    },
    {
        "id": "classic",
        "name": "Classic",
        "description": "Traditional serif format — timeless and formal.",
    },
    {
        "id": "creative",
        "name": "Creative",
        "description": "Purple & teal accents — bold and contemporary.",
    },
    {
        "id": "minimal",
        "name": "Minimal",
        "description": "Light-gray rules — understated and elegant.",
    },
    {
        "id": "executive",
        "name": "Executive",
        "description": "Charcoal headings with amber-gold rules — sharp and authoritative.",
    },
]

# ── Dummy resume for template preview thumbnails ─────────────────────────────
DUMMY_CANDIDATE = {
    "name": "Alex Johnson",
    "contact": {
        "phone": "0412 345 678",
        "email": "alex@email.com",
        "location": "Sydney, NSW",
        "linkedin": "linkedin.com/in/alexjohnson",
    },
    "professional_summary": (
        "Results-driven software engineer with 6+ years delivering scalable "
        "web applications. Proven track record leading cross-functional teams "
        "and shipping high-impact features on time and within scope."
    ),
    "key_skills": ["Python", "TypeScript", "React", "AWS", "Docker", "Agile", "CI/CD"],
    "experience": [
        {
            "title": "Senior Software Engineer",
            "company": "Atlassian",
            "location": "Sydney, NSW",
            "dates": "Jan 2021 – Present",
            "bullets": [
                "Led architecture of microservices platform serving 2M+ daily active users",
                "Reduced API response time by 40% through caching and query optimisation",
                "Mentored 3 junior engineers, improving team velocity by 25%",
            ],
        },
        {
            "title": "Software Engineer",
            "company": "Canva",
            "location": "Sydney, NSW",
            "dates": "Mar 2018 – Dec 2020",
            "bullets": [
                "Built real-time collaboration features used by 5M+ users monthly",
                "Implemented automated testing framework, cutting QA time by 35%",
            ],
        },
    ],
    "education": [
        {
            "degree": "Bachelor of Computer Science",
            "field": "Software Engineering",
            "institution": "University of New South Wales",
            "graduation_year": "2018",
        }
    ],
    "certifications": [
        "AWS Certified Solutions Architect",
        "Google Cloud Professional Developer",
    ],
    "awards": [],
    "technical_skills": [
        "Python", "JavaScript", "TypeScript", "PostgreSQL",
        "Redis", "Kubernetes", "Terraform",
    ],
}


def _get_template(template_id: str) -> Dict:
    """Return a template config dict, falling back to 'modern'."""
    return TEMPLATES.get((template_id or "modern").lower(), TEMPLATES["modern"])


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


def _add_horizontal_rule(doc: Document, color: RGBColor = None):
    """Add a thin 0.5pt border below the paragraph (acts as a rule)."""
    if color is None:
        color = RGBColor(0x1a, 0x37, 0x5e)
    para = doc.add_paragraph()
    _set_para_spacing(para, before=0, after=3)
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


def _section_heading(doc: Document, text: str, tmpl: Dict):
    """Add a styled section heading with a rule below."""
    para = doc.add_paragraph()
    _set_para_spacing(para, before=10, after=1)
    run = para.add_run(text.upper())
    run.font.name    = tmpl["heading_font"]
    run.font.size    = tmpl["section_size"]
    run.font.bold    = True
    run.font.color.rgb = tmpl["heading_color"]
    if tmpl.get("section_rule", True):
        _add_horizontal_rule(doc, tmpl["rule_color"])


def _set_doc_margins(doc: Document):
    """Set page margins to 2.0 cm top/bottom, 2.2 cm sides (A4)."""
    for section in doc.sections:
        section.page_height = Cm(29.7)
        section.page_width  = Cm(21.0)
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
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
    def build_word_document(self, output_path: str, candidate_data: Dict, template_id: str = "modern") -> str:
        """
        Build a professionally formatted Australian-style resume as a .docx file.
        Sections: Header, Professional Summary, Key Skills, Work Experience,
                  Education, Certifications, Awards, Technical Skills.

        Args:
            output_path: Where to save the .docx file.
            candidate_data: Resume data dictionary.
            template_id: One of "modern", "classic", "creative", "minimal".
        """
        tmpl = _get_template(template_id)

        doc = Document()
        _set_doc_margins(doc)

        # Apply body font to Normal style
        normal = doc.styles['Normal']
        normal.font.name = tmpl["body_font"]
        normal.font.size = tmpl["body_size"]

        contact: Dict = candidate_data.get('contact', {})

        # ── Header: Name ────────────────────────────────────────────────
        name_para = doc.add_paragraph()
        _set_para_spacing(name_para, before=0, after=2)
        name_para.alignment = tmpl["name_align"]
        name_run = name_para.add_run(candidate_data.get('name', '').strip().upper())
        name_run.font.name  = tmpl["heading_font"]
        name_run.font.size  = tmpl["name_size"]
        name_run.font.bold  = True
        name_run.font.color.rgb = tmpl["heading_color"]

        # ── Contact line ────────────────────────────────────────────────
        contact_parts = []
        if contact.get('phone'):    contact_parts.append(contact['phone'])
        if contact.get('email'):    contact_parts.append(contact['email'])
        if contact.get('location'): contact_parts.append(contact['location'])
        if contact.get('linkedin'): contact_parts.append(contact['linkedin'])

        contact_para = doc.add_paragraph()
        _set_para_spacing(contact_para, before=0, after=4)
        contact_para.alignment = tmpl["name_align"]
        contact_run = contact_para.add_run('  ·  '.join(contact_parts))
        contact_run.font.name  = tmpl["body_font"]
        contact_run.font.size  = tmpl["contact_size"]
        contact_run.font.color.rgb = tmpl["muted_color"]

        # Rule under header
        _add_horizontal_rule(doc, tmpl["rule_color"])

        # ── Professional Summary ────────────────────────────────────────
        summary = candidate_data.get('professional_summary', '').strip()
        if summary:
            _section_heading(doc, 'Professional Summary', tmpl)
            p = doc.add_paragraph()
            _set_para_spacing(p, before=3, after=6, line=276)
            r = p.add_run(summary)
            r.font.name = tmpl["body_font"]
            r.font.size = tmpl["body_size"]

        # ── Key Skills ─────────────────────────────────────────────────
        key_skills = candidate_data.get('key_skills', [])
        if key_skills:
            _section_heading(doc, 'Key Skills', tmpl)
            p = doc.add_paragraph()
            _set_para_spacing(p, before=3, after=6)
            r = p.add_run('  ·  '.join(str(s) for s in key_skills))
            r.font.name = tmpl["body_font"]
            r.font.size = tmpl["body_size"]

        # ── Work Experience ─────────────────────────────────────────────
        experience = candidate_data.get('experience', [])
        if experience:
            _section_heading(doc, 'Work Experience', tmpl)
            for i, exp in enumerate(experience):
                # Row 1: Job Title (bold) — right-aligned dates
                job_para = doc.add_paragraph()
                _set_para_spacing(job_para, before=4, after=0)
                title_run = job_para.add_run(exp.get('title', ''))
                title_run.font.name  = tmpl["body_font"]
                title_run.font.size  = tmpl["body_size"]
                title_run.font.bold  = True
                title_run.font.color.rgb = tmpl["heading_color"]

                dates = exp.get('dates', '')
                if dates:
                    tab_run = job_para.add_run('\t' + dates)
                    tab_run.font.name  = tmpl["body_font"]
                    tab_run.font.size  = tmpl["body_size"]
                    tab_run.font.bold  = False
                    tab_run.font.color.rgb = tmpl["muted_color"]
                    pPr = job_para._p.get_or_add_pPr()
                    tabs = OxmlElement('w:tabs')
                    tab = OxmlElement('w:tab')
                    tab.set(qn('w:val'), 'right')
                    tab.set(qn('w:pos'), '9360')
                    tabs.append(tab)
                    pPr.append(tabs)

                # Row 2: Company  |  Location (italic, muted)
                company  = exp.get('company', '')
                location = exp.get('location', '')
                sub_parts = [p for p in [company, location] if p]
                if sub_parts:
                    sub_para = doc.add_paragraph()
                    _set_para_spacing(sub_para, before=0, after=1)
                    sub_run = sub_para.add_run('  |  '.join(sub_parts))
                    sub_run.font.name    = tmpl["body_font"]
                    sub_run.font.size    = tmpl["body_size"]
                    sub_run.font.italic  = True
                    sub_run.font.color.rgb = tmpl["muted_color"]

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
                        br.font.name = tmpl["body_font"]
                        br.font.size = tmpl["body_size"]
                elif description:
                    dp = doc.add_paragraph()
                    _set_para_spacing(dp, before=1, after=1, line=276)
                    dr = dp.add_run(description)
                    dr.font.name = tmpl["body_font"]
                    dr.font.size = tmpl["body_size"]

                if i < len(experience) - 1:
                    sp = doc.add_paragraph()
                    _set_para_spacing(sp, before=0, after=3)

        # ── Education ──────────────────────────────────────────────────
        education = candidate_data.get('education', [])
        if education:
            _section_heading(doc, 'Education', tmpl)
            for edu in education:
                degree = edu.get('degree', '')
                field  = edu.get('field',  '')
                grad   = edu.get('graduation_year', '')
                deg_text = f"{degree}{' — ' + field if field else ''}"

                edu_para = doc.add_paragraph()
                _set_para_spacing(edu_para, before=4, after=0)
                dr = edu_para.add_run(deg_text)
                dr.font.name = tmpl["body_font"]
                dr.font.size = tmpl["body_size"]
                dr.font.bold = True
                dr.font.color.rgb = tmpl["heading_color"]
                if grad:
                    tab_run = edu_para.add_run('\t' + grad)
                    tab_run.font.name  = tmpl["body_font"]
                    tab_run.font.size  = tmpl["body_size"]
                    tab_run.font.bold  = False
                    tab_run.font.color.rgb = tmpl["muted_color"]
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
                    ir.font.name    = tmpl["body_font"]
                    ir.font.size    = tmpl["body_size"]
                    ir.font.italic  = True
                    ir.font.color.rgb = tmpl["muted_color"]

        # ── Certifications ─────────────────────────────────────────────
        certs = candidate_data.get('certifications', [])
        if certs:
            _section_heading(doc, 'Certifications', tmpl)
            for cert in certs:
                cp = doc.add_paragraph(style='List Bullet')
                _set_para_spacing(cp, before=1, after=1)
                cr = cp.add_run(str(cert))
                cr.font.name = tmpl["body_font"]
                cr.font.size = tmpl["body_size"]

        # ── Awards ─────────────────────────────────────────────────────
        awards = candidate_data.get('awards', [])
        if awards:
            _section_heading(doc, 'Awards & Recognition', tmpl)
            for award in awards:
                ap = doc.add_paragraph(style='List Bullet')
                _set_para_spacing(ap, before=1, after=1)
                ar = ap.add_run(str(award))
                ar.font.name = tmpl["body_font"]
                ar.font.size = tmpl["body_size"]

        # ── Technical Skills ───────────────────────────────────────────
        tech_skills = candidate_data.get('technical_skills', [])
        if tech_skills:
            _section_heading(doc, 'Technical Skills', tmpl)
            p = doc.add_paragraph()
            _set_para_spacing(p, before=3, after=6)
            r = p.add_run('  ·  '.join(str(s) for s in tech_skills))
            r.font.name = tmpl["body_font"]
            r.font.size = tmpl["body_size"]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
        logger.info(f'Resume saved → {output_path} (template: {template_id})')
        return output_path

    # ── HTML preview builder ─────────────────────────────────────────────
    def build_html_preview(self, candidate_data: Dict, template_id: str = "modern") -> str:
        """
        Return a self-contained HTML string that visually matches the .docx layout.
        Styled to look like an A4 document with the same sections and formatting.

        Args:
            candidate_data: Resume data dictionary.
            template_id: One of "modern", "classic", "creative", "minimal".
        """
        tmpl = _get_template(template_id)
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

        name_html    = e(candidate_data.get('name', '').strip().upper())
        contact_html = '  ·  '.join(contact_parts)

        # Determine font family string for CSS
        font_family = (
            "Georgia, 'Times New Roman', serif"
            if tmpl["body_font"] == "Georgia"
            else "Calibri, 'Segoe UI', Arial, sans-serif"
        )
        name_align = "left" if tmpl["name_align"] == WD_ALIGN_PARAGRAPH.LEFT else "center"

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Resume Preview</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: {font_family};
    font-size: {tmpl["html_body_size"]};
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
    font-size: {tmpl["html_name_size"]};
    font-weight: 700;
    color: {tmpl["html_heading"]};
    text-align: {name_align};
    letter-spacing: 0.04em;
    margin-bottom: 4px;
  }}
  .resume-contact {{
    font-size: {tmpl["html_contact_size"]};
    color: {tmpl["html_muted"]};
    text-align: {name_align};
    margin-bottom: 10px;
  }}
  .resume-contact a {{ color: {tmpl["html_muted"]}; text-decoration: none; }}
  .header-rule {{
    border: none;
    border-top: 1.5px solid {tmpl["html_rule"]};
    margin-bottom: 14px;
  }}
  /* Sections */
  .section {{ margin-bottom: 16px; }}
  .section-heading {{
    font-size: {tmpl["html_section_size"]};
    font-weight: 700;
    color: {tmpl["html_heading"]};
    letter-spacing: 0.08em;
    margin-bottom: 2px;
    margin-top: 4px;
  }}
  .section-rule {{
    border-top: 1px solid {tmpl["html_rule"]};
    margin-bottom: 8px;
  }}
  .body-text {{
    font-size: {tmpl["html_body_size"]};
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
  .exp-title  {{ font-weight: 700; font-size: {tmpl["html_body_size"]}; color: {tmpl["html_heading"]}; }}
  .exp-dates  {{ font-size: 10pt; color: {tmpl["html_muted"]}; }}
  .exp-sub    {{ font-style: italic; color: {tmpl["html_muted"]}; font-size: 10pt; margin-bottom: 4px; }}
  .exp-bullets {{
    margin-left: 1.1em;
    padding-left: 0.5em;
    font-size: {tmpl["html_body_size"]};
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
  .edu-degree {{ font-weight: 700; font-size: {tmpl["html_body_size"]}; color: {tmpl["html_heading"]}; }}
  .edu-year   {{ font-size: 10pt; color: {tmpl["html_muted"]}; }}
  .edu-inst   {{ font-style: italic; color: {tmpl["html_muted"]}; font-size: 10pt; }}
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
    for tid in ["modern", "classic", "creative", "minimal"]:
        builder.build_word_document(f'/tmp/test_resume_{tid}.docx', sample, tid)
        html_out = builder.build_html_preview(sample, tid)
        with open(f'/tmp/test_resume_{tid}.html', 'w') as f:
            f.write(html_out)
        print(f"Smoke test complete for template: {tid}")
