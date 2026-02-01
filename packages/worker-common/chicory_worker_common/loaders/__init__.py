"""
Document loaders - replaces LangChain document_loaders.

Uses unstructured library directly for document parsing.
"""

from .base import Document, BaseLoader
from .unstructured_loader import (
    UnstructuredLoader,
    TextLoader,
    JSONLoader,
    CSVLoader,
    PythonLoader,
    MarkdownLoader,
    RSTLoader,
)
from .pdf_loader import PDFLoader
from .web_loader import (
    WebLoader,
    AsyncWebLoader,
    RawHtmlLoader,
    BeautifulSoupTransformer,
)
from .factory import get_loader

__all__ = [
    # Base
    "Document",
    "BaseLoader",
    # File loaders
    "UnstructuredLoader",
    "PDFLoader",
    "TextLoader",
    "JSONLoader",
    "CSVLoader",
    "PythonLoader",
    "MarkdownLoader",
    "RSTLoader",
    # Web loaders
    "WebLoader",
    "AsyncWebLoader",
    "RawHtmlLoader",
    "BeautifulSoupTransformer",
    # Factory
    "get_loader",
]
