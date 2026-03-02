"""
Unit tests for doc_builder.py – ResumeBuilder class.
Tests cover: Word document generation, HTML preview generation, edge cases.
"""
import os
import tempfile
import pytest
from pathlib import Path
from docx import Document

from doc_builder import ResumeBuilder

# ── Fixtures ────────────────────────────────────────────────────────────────

FULL_CANDIDATE = {
    "name": "Jane Smith",
    "contact": {
        "phone": "0412 345 678",
        "email": "jane.smith@email.com",
        "location": "Melbourne, VIC",
        "linkedin": "linkedin.com/in/janesmith",
    },
    "professional_summary": (
        "Experienced software engineer with 7+ years delivering scalable "
        "web applications for the Australian financial services sector."
    ),
    "key_skills": ["Python", "React", "AWS"],
    "experience": [
        {
            "title": "Senior Software Engineer",
            "company": "ANZ Bank",
            "location": "Melbourne, VIC",
            "dates": "Jan 2020 – Present",
            "description": "",
            "bullets": [
                "Led a team of 5 engineers",
                "Reduced deployment time by 60%",
            ],
        },
        {
            "title": "Software Developer",
            "company": "Startup Co",
            "location": "Sydney, NSW",
            "dates": "Mar 2017 – Dec 2019",
            "description": "Developed REST APIs and front-end features.",
            "bullets": [],
        },
    ],
    "education": [
        {
            "degree": "Bachelor of Computer Science",
            "field": "Software Engineering",
            "institution": "University of Melbourne",
            "graduation_year": "2016",
        }
    ],
    "certifications": ["AWS Certified Solutions Architect"],
    "awards": ["Employee of the Year 2022"],
    "technical_skills": ["Python", "JavaScript", "PostgreSQL", "Docker"],
}

MINIMAL_CANDIDATE = {
    "name": "Bob Jones",
    "contact": {
        "email": "bob@example.com",
        "phone": "0400000000",
        "location": "Brisbane, QLD",
    },
    "professional_summary": "Minimal candidate for testing.",
    "key_skills": [],
    "experience": [],
    "education": [],
    "certifications": [],
    "awards": [],
    "technical_skills": [],
}


@pytest.fixture
def builder():
    return ResumeBuilder()


@pytest.fixture
def tmp_docx(tmp_path):
    return str(tmp_path / "test_resume.docx")


# ── Word document tests ─────────────────────────────────────────────────────

class TestBuildWordDocument:
    def test_creates_file(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        assert Path(tmp_docx).exists()
        assert Path(tmp_docx).stat().st_size > 0

    def test_minimal_candidate_creates_file(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, MINIMAL_CANDIDATE)
        assert Path(tmp_docx).exists()

    def test_returns_output_path(self, builder, tmp_docx):
        result = builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        assert result == tmp_docx

    def test_docx_contains_candidate_name(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        # Name is uppercased in the document
        assert "JANE SMITH" in full_text

    def test_docx_contains_contact_info(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "jane.smith@email.com" in full_text
        assert "0412 345 678" in full_text
        assert "Melbourne, VIC" in full_text

    def test_docx_contains_professional_summary(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "financial services sector" in full_text

    def test_docx_contains_key_skills(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "Python" in full_text
        assert "React" in full_text

    def test_docx_contains_experience_title(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "Senior Software Engineer" in full_text
        assert "ANZ Bank" in full_text

    def test_docx_contains_experience_bullets(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "Led a team of 5 engineers" in full_text

    def test_docx_contains_experience_description(self, builder, tmp_docx):
        """Second experience entry uses description (no bullets)."""
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "Developed REST APIs" in full_text

    def test_docx_contains_education(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "Bachelor of Computer Science" in full_text
        assert "University of Melbourne" in full_text

    def test_docx_contains_certifications(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "AWS Certified Solutions Architect" in full_text

    def test_docx_contains_awards(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "Employee of the Year 2022" in full_text

    def test_docx_contains_technical_skills(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "PostgreSQL" in full_text

    def test_missing_optional_sections_skipped(self, builder, tmp_docx):
        """When no certifications/awards, those headings should not appear."""
        builder.build_word_document(tmp_docx, MINIMAL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs).upper()
        assert "CERTIFICATIONS" not in full_text
        assert "AWARDS" not in full_text

    def test_creates_parent_directory(self, builder, tmp_path):
        nested_path = str(tmp_path / "nested" / "dir" / "resume.docx")
        builder.build_word_document(nested_path, MINIMAL_CANDIDATE)
        assert Path(nested_path).exists()

    def test_linkedin_included_in_contact(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = " ".join(p.text for p in doc.paragraphs)
        assert "linkedin.com/in/janesmith" in full_text

    def test_no_linkedin_still_works(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, MINIMAL_CANDIDATE)
        assert Path(tmp_docx).exists()


# ── HTML preview tests ───────────────────────────────────────────────────────

class TestBuildHtmlPreview:
    def test_returns_string(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert isinstance(html, str)

    def test_contains_html_structure(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "<!DOCTYPE html>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_contains_candidate_name_uppercased(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "JANE SMITH" in html

    def test_contains_contact_email(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "jane.smith@email.com" in html

    def test_contains_phone_and_location(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "0412 345 678" in html
        assert "Melbourne, VIC" in html

    def test_contains_linkedin_link(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "linkedin.com/in/janesmith" in html

    def test_contains_professional_summary(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "financial services sector" in html

    def test_contains_key_skills(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "Python" in html
        assert "React" in html

    def test_contains_experience_entries(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "Senior Software Engineer" in html
        assert "ANZ Bank" in html

    def test_contains_bullets(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "Led a team of 5 engineers" in html

    def test_contains_description_fallback(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "Developed REST APIs" in html

    def test_contains_education(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "Bachelor of Computer Science" in html
        assert "University of Melbourne" in html

    def test_contains_certifications(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "AWS Certified Solutions Architect" in html

    def test_contains_awards(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "Employee of the Year 2022" in html

    def test_contains_technical_skills(self, builder):
        html = builder.build_html_preview(FULL_CANDIDATE)
        assert "PostgreSQL" in html

    def test_html_escapes_special_chars(self, builder):
        candidate = dict(MINIMAL_CANDIDATE)
        candidate["name"] = '<Script>alert("xss")</Script>'
        html = builder.build_html_preview(candidate)
        # Name is uppercased before escaping, raw tags must not appear in output
        assert "<Script>" not in html
        assert "<SCRIPT>" not in html
        # Escaped form must be present
        assert "&lt;SCRIPT&gt;" in html

    def test_minimal_candidate_produces_valid_html(self, builder):
        html = builder.build_html_preview(MINIMAL_CANDIDATE)
        assert "BOB JONES" in html

    def test_optional_sections_absent_when_empty(self, builder):
        html = builder.build_html_preview(MINIMAL_CANDIDATE).upper()
        assert "CERTIFICATIONS" not in html
        assert "AWARDS" not in html
        assert "KEY SKILLS" not in html


# ── Legacy methods ──────────────────────────────────────────────────────────

class TestLegacyMethods:
    def test_collect_personal_info(self, builder):
        builder.collect_personal_info("Alice", {"email": "a@b.com"})
        assert builder.resume_data["name"] == "Alice"

    def test_collect_experience(self, builder):
        exp = [{"title": "Dev", "company": "Acme"}]
        builder.collect_experience(exp)
        assert builder.resume_data["experience"] == exp

    def test_build_resume_text(self, builder):
        builder.collect_personal_info("Alice", {"email": "a@b.com", "phone": "0400", "location": "Sydney"})
        builder.collect_experience([{"title": "Dev", "company": "Acme", "dates": "2020"}])
        builder.collect_education([{"degree": "B.Sc.", "institution": "UNSW"}])
        text = builder.build_resume_text()
        assert "Alice" in text
        assert "Dev" in text
