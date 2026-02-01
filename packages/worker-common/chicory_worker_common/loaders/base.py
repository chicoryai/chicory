"""
Base classes for document loading.

Replaces langchain_core.documents.Document with a simpler implementation.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


@dataclass
class Document:
    """
    A document with content and metadata.

    Compatible with the LangChain Document interface for easy migration.

    Attributes:
        page_content: The text content of the document.
        metadata: Arbitrary metadata about the document (source, page number, etc.).
    """
    page_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.page_content

    def __repr__(self) -> str:
        return f"Document(page_content={self.page_content[:50]}..., metadata={self.metadata})"


class BaseLoader(Protocol):
    """
    Protocol for document loaders.

    All loaders must implement the load() method that returns a list of Documents.
    """

    def load(self) -> List[Document]:
        """Load and return documents."""
        ...

    def lazy_load(self) -> List[Document]:
        """Lazily load documents (default: same as load)."""
        return self.load()
