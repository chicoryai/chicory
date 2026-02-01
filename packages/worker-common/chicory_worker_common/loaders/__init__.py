"""
Document loaders - replaces LangChain document_loaders.

Uses unstructured library directly for document parsing.
"""

from .base import Document, BaseLoader
from .unstructured_loader import UnstructuredLoader
from .pdf_loader import PDFLoader
from .factory import get_loader

__all__ = [
    "Document",
    "BaseLoader",
    "UnstructuredLoader",
    "PDFLoader",
    "get_loader",
]
