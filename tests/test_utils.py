"""
Tests for utility functions in utils.py
"""
import pytest
from utils import (
    sanitize_filename, validate_file_extension, get_max_prompts_for_tier,
    validate_user_id, MAX_FILES,
    MAX_PROMPTS_GUEST, MAX_PROMPTS_FREE, MAX_PROMPTS_PRO, MAX_PROMPTS_ENTERPRISE,
)


class TestSanitizeFilename:
    def test_removes_path_components(self):
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("folder/file.txt") == "file.txt"
    
    def test_removes_dangerous_characters(self):
        assert "<script>" not in sanitize_filename("<script>.txt")
        assert ":" not in sanitize_filename("file:name.txt")
        assert "/" not in sanitize_filename("file/name.txt")
    
    def test_limits_length(self):
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
    
    def test_handles_empty_string(self):
        assert sanitize_filename("") == "file"
        assert sanitize_filename(None) == "file"


class TestValidateFileExtension:
    def test_allows_valid_extensions(self):
        assert validate_file_extension("resume.pdf")
        assert validate_file_extension("resume.docx")
        assert validate_file_extension("resume.doc")
        assert validate_file_extension("resume.txt")
    
    def test_rejects_invalid_extensions(self):
        assert not validate_file_extension("resume.exe")
        assert not validate_file_extension("resume.sh")
        assert not validate_file_extension("resume")
    
    def test_case_insensitive(self):
        assert validate_file_extension("resume.PDF")
        assert validate_file_extension("resume.DOCX")


class TestGetMaxPromptsForTier:
    def test_guest_tier(self):
        assert get_max_prompts_for_tier("guest") == MAX_PROMPTS_GUEST
        assert MAX_PROMPTS_GUEST == 3

    def test_free_tier(self):
        assert get_max_prompts_for_tier("free") == MAX_PROMPTS_FREE
        assert MAX_PROMPTS_FREE == 3

    def test_pro_tier(self):
        assert get_max_prompts_for_tier("pro") == MAX_PROMPTS_PRO
        assert MAX_PROMPTS_PRO == 50

    def test_enterprise_tier(self):
        assert get_max_prompts_for_tier("enterprise") == MAX_PROMPTS_ENTERPRISE
        assert MAX_PROMPTS_ENTERPRISE == 50

    def test_unknown_tier_defaults_to_free(self):
        assert get_max_prompts_for_tier("unknown") == MAX_PROMPTS_FREE
        assert get_max_prompts_for_tier("") == MAX_PROMPTS_FREE


class TestValidateUserId:
    def test_valid_user_id(self):
        assert validate_user_id(1)
        assert validate_user_id(100)
    
    def test_none_is_valid(self):
        assert validate_user_id(None)
    
    def test_invalid_user_id(self):
        assert not validate_user_id(0)
        assert not validate_user_id(-1)
        assert not validate_user_id("1")
        assert not validate_user_id(1.5)
