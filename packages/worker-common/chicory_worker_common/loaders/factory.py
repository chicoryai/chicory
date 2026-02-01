"""
Document loader factory.

Provides a simple interface to get the appropriate loader based on file type.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union

from .base import BaseLoader, Document
from .pdf_loader import PDFLoader, SimplePDFLoader
from .unstructured_loader import (
    CSVLoader,
    JSONLoader,
    TextLoader,
    UnstructuredLoader,
)

logger = logging.getLogger(__name__)

# File extension to loader mapping
LOADER_MAPPING: Dict[str, Type] = {
    # Text files
    ".txt": TextLoader,
    ".text": TextLoader,
    ".log": TextLoader,
    # Code files (use text loader)
    ".py": TextLoader,
    ".js": TextLoader,
    ".ts": TextLoader,
    ".jsx": TextLoader,
    ".tsx": TextLoader,
    ".java": TextLoader,
    ".go": TextLoader,
    ".rs": TextLoader,
    ".rb": TextLoader,
    ".php": TextLoader,
    ".c": TextLoader,
    ".cpp": TextLoader,
    ".h": TextLoader,
    ".hpp": TextLoader,
    ".cs": TextLoader,
    ".swift": TextLoader,
    ".kt": TextLoader,
    ".scala": TextLoader,
    ".r": TextLoader,
    ".sql": TextLoader,
    ".sh": TextLoader,
    ".bash": TextLoader,
    ".zsh": TextLoader,
    ".yaml": TextLoader,
    ".yml": TextLoader,
    ".toml": TextLoader,
    ".ini": TextLoader,
    ".cfg": TextLoader,
    ".conf": TextLoader,
    # Data files
    ".json": JSONLoader,
    ".csv": CSVLoader,
    # Documents (use unstructured)
    ".pdf": PDFLoader,
    ".docx": UnstructuredLoader,
    ".doc": UnstructuredLoader,
    ".pptx": UnstructuredLoader,
    ".ppt": UnstructuredLoader,
    ".xlsx": UnstructuredLoader,
    ".xls": UnstructuredLoader,
    # Markup
    ".md": UnstructuredLoader,
    ".markdown": UnstructuredLoader,
    ".rst": UnstructuredLoader,
    ".html": UnstructuredLoader,
    ".htm": UnstructuredLoader,
    ".xml": UnstructuredLoader,
    # Images (for OCR)
    ".png": UnstructuredLoader,
    ".jpg": UnstructuredLoader,
    ".jpeg": UnstructuredLoader,
    ".tiff": UnstructuredLoader,
    ".bmp": UnstructuredLoader,
}


def get_loader(
    file_path: str,
    loader_class: Optional[Type] = None,
    **kwargs: Any,
) -> Union[BaseLoader, Any]:
    """
    Get the appropriate loader for a file.

    Args:
        file_path: Path to the file to load.
        loader_class: Optional specific loader class to use.
        **kwargs: Additional arguments passed to the loader.

    Returns:
        An instance of the appropriate loader.

    Raises:
        ValueError: If no loader is available for the file type.
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    if loader_class is not None:
        logger.debug(f"Using specified loader: {loader_class.__name__}")
        return loader_class(file_path, **kwargs)

    if extension in LOADER_MAPPING:
        loader_cls = LOADER_MAPPING[extension]
        logger.debug(f"Using loader {loader_cls.__name__} for {extension}")
        return loader_cls(file_path, **kwargs)

    # Fallback to UnstructuredLoader for unknown types
    logger.warning(
        f"No specific loader for {extension}, falling back to UnstructuredLoader"
    )
    return UnstructuredLoader(file_path, **kwargs)


def load_document(file_path: str, **kwargs: Any) -> list[Document]:
    """
    Convenience function to load a document directly.

    Args:
        file_path: Path to the file to load.
        **kwargs: Additional arguments passed to the loader.

    Returns:
        List of Document objects.
    """
    loader = get_loader(file_path, **kwargs)
    return loader.load()


def load_documents(file_paths: list[str], **kwargs: Any) -> list[Document]:
    """
    Load multiple documents.

    Args:
        file_paths: List of file paths to load.
        **kwargs: Additional arguments passed to each loader.

    Returns:
        List of all Document objects from all files.
    """
    all_docs = []
    for path in file_paths:
        try:
            docs = load_document(path, **kwargs)
            all_docs.extend(docs)
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")
            continue
    return all_docs
