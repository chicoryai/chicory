"""
File Validation Utilities

Provides validation functions for file uploads, folder structures,
and security checks for the Chicory platform.
"""
import os
import logging
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any, NamedTuple

logger = logging.getLogger(__name__)


class ValidationResult(NamedTuple):
    """Result of a validation check"""
    valid: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# File size limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
MAX_FOLDER_SIZE = 500 * 1024 * 1024  # 500MB total
MAX_FOLDER_DEPTH = 10
MAX_FILES_PER_FOLDER = 1000

# Blocked extensions - security risk (executables and installers only)
BLOCKED_EXTENSIONS = frozenset([
    '.exe', '.dll', '.so', '.dylib',  # Executables
    '.msi', '.dmg', '.pkg', '.deb', '.rpm',  # Installers
    '.com', '.scr', '.pif',            # Windows executables
    '.vbs', '.vbe', '.jse', '.ws', '.wsf',  # Windows scripts
    '.hta', '.cpl',                     # Windows components
    '.jar', '.app', '.elf', '.bin', '.run',  # Additional executables
])
# Note: .js, .sh, .bat, .cmd, .ps1 are allowed for code uploads

# Allowed extensions by category
# Document category now accepts ALL file types (code, docs, data) for unified uploads
ALLOWED_EXTENSIONS_BY_CATEGORY = {
    'document': frozenset([
        # Documents
        '.pdf', '.doc', '.docx', '.txt', '.md', '.rtf',
        '.odt', '.xls', '.xlsx', '.csv', '.ppt', '.pptx',
        '.html', '.htm', '.xml', '.json', '.yaml', '.yml',
        # Images
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp',
        # Media
        '.mp3', '.mp4', '.wav', '.avi', '.mov', '.webm',
        # Code files (unified upload - all code goes through documents now)
        '.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs',
        '.java', '.go', '.rs', '.cpp', '.c', '.h', '.hpp', '.cc',
        '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.lua',
        '.css', '.scss', '.sass', '.less', '.styl',
        '.toml', '.ini', '.cfg', '.conf', '.properties',
        '.rst', '.sql', '.graphql', '.prisma',
        '.sh', '.bash', '.zsh', '.fish', '.bat', '.cmd', '.ps1',
        '.dockerfile', '.gitignore', '.gitattributes', '.editorconfig',
        '.env', '.env.example', '.env.local',
        '.lock', '.sum', '.mod', '.gradle', '.maven',
        '.vue', '.svelte', '.astro', '.mdx',
        '.r', '.R', '.rmd', '.Rmd', '.jl',  # R and Julia
        '.tf', '.hcl', '.tfvars',  # Terraform
        '.proto', '.thrift', '.avsc',  # Schema files
    ]),
    'code': frozenset([
        # Kept for backwards compatibility, but uploads now go through document
        '.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs',
        '.java', '.go', '.rs', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.rb', '.php', '.swift', '.kt', '.scala',
        '.html', '.css', '.scss', '.sass', '.less',
        '.json', '.yaml', '.yml', '.toml', '.xml',
        '.md', '.txt', '.rst', '.sql',
        '.sh', '.bash', '.zsh', '.bat', '.cmd', '.ps1',
        '.dockerfile', '.gitignore', '.env.example',
        '.lock', '.sum', '.mod',
    ]),
    'data': frozenset([
        '.csv', '.xlsx', '.xls', '.json', '.xml',
        '.parquet', '.avro', '.orc',
        '.tsv', '.txt', '.dat',
        '.sql', '.db', '.sqlite',
    ])
}

# MIME type mappings for common extensions
MIME_TYPE_MAP = {
    '.py': 'text/x-python',
    '.js': 'application/javascript',
    '.ts': 'text/typescript',
    '.tsx': 'text/typescript-jsx',
    '.jsx': 'text/javascript-jsx',
    '.json': 'application/json',
    '.yaml': 'application/x-yaml',
    '.yml': 'application/x-yaml',
    '.md': 'text/markdown',
    '.html': 'text/html',
    '.css': 'text/css',
    '.scss': 'text/x-scss',
    '.sql': 'application/sql',
    '.csv': 'text/csv',
    '.txt': 'text/plain',
    '.xml': 'application/xml',
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
}

# Preview-supported extensions
PREVIEW_SUPPORTED_EXTENSIONS = frozenset([
    '.txt', '.md', '.json', '.yaml', '.yml', '.xml',
    '.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css',
    '.java', '.go', '.rs', '.cpp', '.c', '.h',
    '.csv', '.sql', '.sh', '.bash',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',
    '.pdf',
])


def validate_file_extension(filename: str, category: Optional[str] = None) -> ValidationResult:
    """
    Validate a file's extension.

    Args:
        filename: The filename to validate
        category: Optional category (document, code, data) for stricter validation

    Returns:
        ValidationResult with valid=True if extension is allowed
    """
    ext = Path(filename).suffix.lower()

    # Check blocked extensions first
    if ext in BLOCKED_EXTENSIONS:
        return ValidationResult(
            valid=False,
            error=f"File type '{ext}' is not allowed for security reasons"
        )

    # If category specified, validate against allowed extensions
    if category and category in ALLOWED_EXTENSIONS_BY_CATEGORY:
        allowed = ALLOWED_EXTENSIONS_BY_CATEGORY[category]
        # For code category, be more permissive - allow files without extensions
        if category == 'code' and not ext:
            return ValidationResult(valid=True)
        # Allow common extensions even if not in category-specific list
        if ext not in allowed and ext not in BLOCKED_EXTENSIONS:
            # Only warn, don't block - could be a valid file type we don't know
            safe_filename = filename.replace('\n', '\\n').replace('\r', '\\r')
            logger.warning(f"Extension '{ext}' not in typical {category} files for file: {safe_filename}")
            return ValidationResult(
                valid=True,
                details={"warning": f"Extension '{ext}' not in typical {category} files"}
            )

    return ValidationResult(valid=True)


def validate_file_size(file_size: int, max_size: int = MAX_FILE_SIZE) -> ValidationResult:
    """
    Validate a file's size.

    Args:
        file_size: Size in bytes
        max_size: Maximum allowed size in bytes

    Returns:
        ValidationResult with valid=True if size is within limits
    """
    if file_size <= 0:
        return ValidationResult(
            valid=False,
            error="File size must be greater than 0"
        )

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        return ValidationResult(
            valid=False,
            error=f"File size ({file_mb:.2f}MB) exceeds maximum allowed ({max_mb:.0f}MB)"
        )

    return ValidationResult(valid=True)


def validate_file(
    filename: str,
    file_size: int,
    category: Optional[str] = None
) -> ValidationResult:
    """
    Validate a single file for upload.

    Args:
        filename: The filename to validate
        file_size: Size in bytes
        category: Optional category for extension validation

    Returns:
        ValidationResult with valid=True if file passes all checks
    """
    # Validate extension
    ext_result = validate_file_extension(filename, category)
    if not ext_result.valid:
        return ext_result

    # Validate size
    size_result = validate_file_size(file_size)
    if not size_result.valid:
        return size_result

    return ValidationResult(valid=True, details=ext_result.details)


def validate_relative_path(relative_path: str) -> ValidationResult:
    """
    Validate a relative path for security issues.

    Args:
        relative_path: The relative path to validate

    Returns:
        ValidationResult with valid=True if path is safe
    """
    # Check for null bytes first
    if '\x00' in relative_path:
        return ValidationResult(valid=False, error="Null bytes in path are not allowed")

    # Check path length
    if len(relative_path) > 500:
        return ValidationResult(valid=False, error="Path too long (max 500 characters)")

    # Normalize and check for traversal
    try:
        normalized = str(Path(relative_path))
    except (ValueError, OSError):
        return ValidationResult(valid=False, error="Invalid path format")

    if '..' in Path(normalized).parts:
        return ValidationResult(valid=False, error="Path traversal (..) is not allowed")

    if Path(normalized).is_absolute():
        return ValidationResult(valid=False, error="Absolute paths are not allowed")

    return ValidationResult(valid=True)


def validate_folder_structure(
    files: List[Dict[str, Any]],
    max_files: int = MAX_FILES_PER_FOLDER,
    max_size: int = MAX_FOLDER_SIZE,
    max_depth: int = MAX_FOLDER_DEPTH
) -> ValidationResult:
    """
    Validate an entire folder structure for upload.

    Args:
        files: List of file entries with 'relative_path' and 'file_size' keys
        max_files: Maximum number of files allowed
        max_size: Maximum total size in bytes
        max_depth: Maximum directory depth allowed

    Returns:
        ValidationResult with valid=True if structure passes all checks
    """
    if not files:
        return ValidationResult(
            valid=False,
            error="No files provided"
        )

    # Check file count
    if len(files) > max_files:
        return ValidationResult(
            valid=False,
            error=f"Too many files ({len(files)}). Maximum allowed: {max_files}"
        )

    # Calculate totals and check each file
    total_size = 0
    actual_max_depth = 0
    invalid_files = []

    for file_entry in files:
        relative_path = file_entry.get('relative_path', '')
        file_size = file_entry.get('file_size', 0)

        # Validate path
        path_result = validate_relative_path(relative_path)
        if not path_result.valid:
            invalid_files.append({
                'path': relative_path,
                'error': path_result.error
            })
            continue

        # Calculate depth
        depth = relative_path.count('/')
        actual_max_depth = max(actual_max_depth, depth)

        # Validate individual file
        filename = os.path.basename(relative_path)
        file_result = validate_file(filename, file_size)
        if not file_result.valid:
            invalid_files.append({
                'path': relative_path,
                'error': file_result.error
            })
            continue

        total_size += file_size

    # Check for invalid files
    if invalid_files:
        return ValidationResult(
            valid=False,
            error=f"{len(invalid_files)} file(s) failed validation",
            details={"invalid_files": invalid_files}
        )

    # Check total size
    if total_size > max_size:
        max_mb = max_size / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        return ValidationResult(
            valid=False,
            error=f"Total size ({total_mb:.2f}MB) exceeds maximum allowed ({max_mb:.0f}MB)"
        )

    # Check depth
    if actual_max_depth > max_depth:
        return ValidationResult(
            valid=False,
            error=f"Folder depth ({actual_max_depth}) exceeds maximum allowed ({max_depth})"
        )

    return ValidationResult(
        valid=True,
        details={
            "total_files": len(files),
            "total_size": total_size,
            "max_depth": actual_max_depth
        }
    )


def get_content_type(filename: str) -> str:
    """
    Get the MIME type for a file.

    Args:
        filename: The filename to get MIME type for

    Returns:
        MIME type string
    """
    ext = Path(filename).suffix.lower()

    # Check our custom map first
    if ext in MIME_TYPE_MAP:
        return MIME_TYPE_MAP[ext]

    # Fall back to mimetypes
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def is_preview_supported(filename: str) -> bool:
    """
    Check if a file type supports preview.

    Args:
        filename: The filename to check

    Returns:
        True if preview is supported
    """
    ext = Path(filename).suffix.lower()
    return ext in PREVIEW_SUPPORTED_EXTENSIONS


def calculate_depth(relative_path: str) -> int:
    """
    Calculate the directory depth of a path.

    Args:
        relative_path: The relative path

    Returns:
        Directory depth (0 for root level files)
    """
    if not relative_path:
        return 0
    return relative_path.rstrip('/').count('/')


def get_parent_path(relative_path: str) -> str:
    """
    Get the parent directory path.

    Args:
        relative_path: The relative path

    Returns:
        Parent directory path or empty string for root level
    """
    if '/' not in relative_path:
        return ''
    parent = str(Path(relative_path).parent)
    return '' if parent == '.' else parent
