"""
Unit tests for doc_builder.py – ResumeBuilder class.
Tests cover: Word document generation, HTML preview generation, layout
structure, and edge cases.
"""
import os
import tempfile
import pytest
from pathlib import Path
from docx import Document

from doc_builder import ResumeBuilder, STYLE


# ── Fixtures ────────────────────────────────────────────────────────────────

FULL_CANDIDATE = {
    "name": "Jane Smith",
    "contact": {
        "phone":    "0412 345 678",
        "email":    "jane.smith@email.com",
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
            "title":    "Senior Software Engineer",
            "company":  "ANZ Bank",
            "location": "Melbourne, VIC",
            "dates":    "Jan 2020 – Present",
            "description": "",
            "bullets": [
                "Led a team of 5 engineers",
                "Reduced deployment time by 60%",
            ],
        },
        {
            "title":    "Software Developer",
            "company":  "Startup Co",
            "location": "Sydney, NSW",
            "dates":    "Mar 2017 – Dec 2019",
            "description": "Developed REST APIs and front-end features.",
            "bullets": [],
        },
    ],
    "education": [
        {
            "degree":          "Bachelor of Computer Science",
            "field":           "Software Engineering",
            "institution":     "University of Melbourne",
            "graduation_year": "2016",
        }
    ],
    "certifications":  ["AWS Certified Solutions Architect"],
    "awards":          ["Employee of the Year 2022"],
    "technical_skills": ["Python", "JavaScript", "PostgreSQL", "Docker"],
}

MINIMAL_CANDIDATE = {
    "name": "Bob Jones",
    "contact": {
        "email":    "bob@example.com",
        "phone":    "0400000000",
        "location": "Brisbane, QLD",
    },
    "professional_summary": "Minimal candidate for testing.",
    "key_skills":       [],
    "experience":       [],
    "education":        [],
    "certifications":   [],
    "awards":           [],
    "technical_skills": [],
}


@pytest.fixture
def builder():
    return ResumeBuilder()


@pytest.fixture
def tmp_docx(tmp_path):
    return str(tmp_path / "test_resume.docx")


# ── Helper ───────────────────────────────────────────────────────────────────

def _get_all_text(doc: Document) -> str:
    """
    Extract all text from a Document, including paragraphs inside table cells.
    The layout stores content in table cells which doc.paragraphs does not expose.
    """
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.extend(p.text for p in cell.paragraphs)
    return " ".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# Word document tests
# ══════════════════════════════════════════════════════════════════════════════

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
        assert "JANE SMITH" in _get_all_text(doc)

    def test_docx_contains_contact_info(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = _get_all_text(doc)
        assert "jane.smith@email.com" in full_text
        assert "0412 345 678" in full_text
        assert "Melbourne, VIC" in full_text

    def test_docx_contains_professional_summary(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        assert "financial services sector" in _get_all_text(doc)

    def test_docx_contains_key_skills(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = _get_all_text(doc)
        assert "Python" in full_text
        assert "React" in full_text

    def test_docx_contains_experience_title(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = _get_all_text(doc)
        assert "Senior Software Engineer" in full_text
        assert "ANZ Bank" in full_text

    def test_docx_contains_experience_bullets(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        assert "Led a team of 5 engineers" in _get_all_text(doc)

    def test_docx_contains_experience_description(self, builder, tmp_docx):
        """Second experience entry uses description (no bullets)."""
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        assert "Developed REST APIs" in _get_all_text(doc)

    def test_docx_contains_education(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = _get_all_text(doc)
        assert "Bachelor of Computer Science" in full_text
        assert "University of Melbourne" in full_text

    def test_docx_contains_certifications(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        assert "AWS Certified Solutions Architect" in _get_all_text(doc)

    def test_docx_contains_awards(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        assert "Employee of the Year 2022" in _get_all_text(doc)

    def test_docx_contains_technical_skills(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        assert "PostgreSQL" in _get_all_text(doc)

    def test_missing_optional_sections_skipped(self, builder, tmp_docx):
        """When no certifications/awards, those headings should not appear."""
        builder.build_word_document(tmp_docx, MINIMAL_CANDIDATE)
        doc = Document(tmp_docx)
        full_text = _get_all_text(doc).upper()
        assert "CERTIFICATIONS" not in full_text
        assert "AWARDS" not in full_text

    def test_creates_parent_directory(self, builder, tmp_path):
        nested_path = str(tmp_path / "nested" / "dir" / "resume.docx")
        builder.build_word_document(nested_path, MINIMAL_CANDIDATE)
        assert Path(nested_path).exists()

    def test_linkedin_included_in_contact(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        assert "linkedin.com/in/janesmith" in _get_all_text(doc)

    def test_no_linkedin_still_works(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, MINIMAL_CANDIDATE)
        assert Path(tmp_docx).exists()


# ── HTML preview tests ───────────────────────────────────────────────────────

class TestBuildHtmlPreview:
    def test_returns_string(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert isinstance(result, str)

    def test_contains_html_structure(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "<!DOCTYPE html>" in result
        assert "<body>" in result
        assert "</html>" in result

    def test_contains_candidate_name_uppercased(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "JANE SMITH" in result

    def test_contains_contact_email(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "jane.smith@email.com" in result

    def test_contains_phone_and_location(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "0412 345 678" in result
        assert "Melbourne, VIC" in result

    def test_contains_linkedin_link(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "linkedin.com/in/janesmith" in result

    def test_contains_professional_summary(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "financial services sector" in result

    def test_contains_key_skills(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "Python" in result
        assert "React" in result

    def test_contains_experience_entries(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "Senior Software Engineer" in result
        assert "ANZ Bank" in result

    def test_contains_bullets(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "Led a team of 5 engineers" in result

    def test_contains_description_fallback(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "Developed REST APIs" in result

    def test_contains_education(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "Bachelor of Computer Science" in result
        assert "University of Melbourne" in result

    def test_contains_certifications(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "AWS Certified Solutions Architect" in result

    def test_contains_awards(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "Employee of the Year 2022" in result

    def test_contains_technical_skills(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "PostgreSQL" in result

    def test_html_escapes_special_chars(self, builder):
        candidate = dict(MINIMAL_CANDIDATE)
        candidate["name"] = '<Script>alert("xss")</Script>'
        result = builder.build_html_preview(candidate)
        assert "<Script>" not in result
        assert "<SCRIPT>" not in result
        assert "&lt;SCRIPT&gt;" in result

    def test_minimal_candidate_produces_valid_html(self, builder):
        result = builder.build_html_preview(MINIMAL_CANDIDATE)
        assert "BOB JONES" in result

    def test_optional_sections_absent_when_empty(self, builder):
        result = builder.build_html_preview(MINIMAL_CANDIDATE).upper()
        assert "CERTIFICATIONS" not in result
        assert "AWARDS" not in result
        assert "KEY SKILLS" not in result


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


# ── Layout structure tests ───────────────────────────────────────────────────

class TestWordLayout:
    def test_uses_table(self, builder, tmp_docx):
        """Content is rendered inside tables (header + two-column body)."""
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        assert len(Document(tmp_docx).tables) >= 2

    def test_sidebar_contains_contact(self, builder, tmp_docx):
        """Sidebar cell (column 0) should contain contact information."""
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        # doc.tables[0] is the full-width header table; doc.tables[1] is the body table
        sidebar_text = " ".join(p.text for p in doc.tables[1].cell(0, 0).paragraphs)
        assert "jane.smith@email.com" in sidebar_text

    def test_main_contains_experience(self, builder, tmp_docx):
        """Main cell (column 1) should contain work experience."""
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        doc = Document(tmp_docx)
        main_text = " ".join(p.text for p in doc.tables[1].cell(0, 1).paragraphs)
        assert "Senior Software Engineer" in main_text

    def test_uses_calibri(self, builder, tmp_docx):
        builder.build_word_document(tmp_docx, FULL_CANDIDATE)
        assert Document(tmp_docx).styles["Normal"].font.name == STYLE["body_font"]

    def test_bytes_match_file_content(self, builder):
        from io import BytesIO
        doc = Document(BytesIO(builder.build_word_document_bytes(FULL_CANDIDATE)))
        assert "JANE SMITH" in _get_all_text(doc).upper()


class TestHtmlLayout:
    def test_has_sidebar_and_main(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert 'class="sidebar"' in result
        assert 'class="main"' in result

    def test_sidebar_contains_contact(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        sidebar_block = result[result.find('class="sidebar"'):result.find('class="main"')]
        assert "jane.smith@email.com" in sidebar_block

    def test_main_contains_experience(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert "Senior Software Engineer" in result[result.find('class="main"'):]

    def test_has_navy_sidebar(self, builder):
        result = builder.build_html_preview(FULL_CANDIDATE)
        assert STYLE["html_sidebar_bg"] in result
