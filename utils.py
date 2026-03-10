"""
Utility functions for common operations across the application.
Reduces code duplication and ensures consistency.
"""
import re
import logging
from pathlib import Path
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Constants
MAX_FILES = 5
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}
MAX_PROMPTS_GUEST = 3        # Edits allowed without an account
MAX_PROMPTS_FREE = 3         # Same cap for free-tier accounts
MAX_PROMPTS_PRO = 50         # Paid tier
MAX_PROMPTS_ENTERPRISE = 50  # Enterprise tier


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal and other security issues.
    Returns a safe filename.
    """
    if not filename:
        return "file"
    
    # Remove path components
    filename = Path(filename).name
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem[:250], Path(filename).suffix
        filename = name + ext
    
    return filename or "file"


def validate_file_extension(filename: str) -> bool:
    """Check if file extension is allowed."""
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def get_max_prompts_for_tier(tier: str) -> int:
    """Get maximum prompts allowed for a membership tier."""
    tier_map = {
        'guest': MAX_PROMPTS_GUEST,
        'free': MAX_PROMPTS_FREE,
        'pro': MAX_PROMPTS_PRO,
        'enterprise': MAX_PROMPTS_ENTERPRISE,
    }
    return tier_map.get(tier, MAX_PROMPTS_FREE)


def handle_database_error(error: Exception, operation: str) -> HTTPException:
    """
    Standardized database error handling.
    Returns appropriate HTTPException based on error type.
    """
    error_str = str(error)
    
    if "SSL connection" in error_str or "closed unexpectedly" in error_str:
        logger.error(f"Database connection error during {operation}: {error_str}")
        return HTTPException(
            status_code=503,
            detail="Database connection issue. Please try again in a moment."
        )
    elif "not found" in error_str.lower() or "does not exist" in error_str.lower():
        logger.warning(f"Resource not found during {operation}: {error_str}")
        return HTTPException(status_code=404, detail=f"Resource not found")
    else:
        logger.error(f"Database error during {operation}: {error_str}")
        return HTTPException(
            status_code=500,
            detail=f"An error occurred while {operation}. Please try again."
        )


def standardize_response(data: dict, status: str = "success") -> dict:
    """Standardize API response format."""
    return {
        "status": status,
        **data
    }


def validate_user_id(user_id: Optional[int]) -> bool:
    """Validate that user_id is a positive integer if provided."""
    if user_id is None:
        return True
    return isinstance(user_id, int) and user_id > 0
