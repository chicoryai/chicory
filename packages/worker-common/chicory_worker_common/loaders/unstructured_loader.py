"""
Universal document loader using the unstructured library.

Supports: PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, images, and more.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Document

logger = logging.getLogger(__name__)


class UnstructuredLoader:
    """
    Universal loader using the unstructured library.

    This replaces multiple LangChain loaders:
    - TextLoader
    - UnstructuredMarkdownLoader
    - UnstructuredPowerPointLoader
    - UnstructuredExcelLoader
    - etc.
    """

    def __init__(
        self,
        file_path: str,
        mode: str = "single",
        strategy: str = "auto",
        **unstructured_kwargs: Any,
    ):
        """
        Initialize the loader.

        Args:
            file_path: Path to the file to load.
            mode: How to combine elements. "single" for one document,
                  "elements" for one document per element.
            strategy: Parsing strategy - "auto", "fast", "hi_res", "ocr_only".
            **unstructured_kwargs: Additional arguments passed to unstructured.
        """
        self.file_path = file_path
        self.mode = mode
        self.strategy = strategy
        self.unstructured_kwargs = unstructured_kwargs

    def load(self) -> List[Document]:
        """Load the document and return as Document objects."""
        try:
            from unstructured.partition.auto import partition
        except ImportError:
            raise ImportError(
                "unstructured is required for UnstructuredLoader. "
                "Install with: pip install unstructured"
            )

        path = Path(self.file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        logger.debug(f"Loading file with unstructured: {self.file_path}")

        # Partition the document
        elements = partition(
            filename=str(path),
            strategy=self.strategy,
            **self.unstructured_kwargs,
        )

        if self.mode == "single":
            # Combine all elements into a single document
            text = "\n\n".join(str(el) for el in elements)
            return [
                Document(
                    page_content=text,
                    metadata={
                        "source": str(path),
                        "filename": path.name,
                        "file_type": path.suffix.lower(),
                        "element_count": len(elements),
                    },
                )
            ]
        else:
            # One document per element
            documents = []
            for i, el in enumerate(elements):
                metadata = {
                    "source": str(path),
                    "filename": path.name,
                    "file_type": path.suffix.lower(),
                    "element_index": i,
                    "element_type": type(el).__name__,
                }
                # Add element metadata if available
                if hasattr(el, "metadata"):
                    el_meta = el.metadata
                    if hasattr(el_meta, "page_number"):
                        metadata["page"] = el_meta.page_number
                    if hasattr(el_meta, "coordinates"):
                        metadata["coordinates"] = el_meta.coordinates

                documents.append(
                    Document(page_content=str(el), metadata=metadata)
                )
            return documents

    def lazy_load(self) -> List[Document]:
        """Lazy load (currently same as load)."""
        return self.load()


class TextLoader:
    """Simple text file loader."""

    def __init__(
        self,
        file_path: str,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = True,
    ):
        self.file_path = file_path
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding

    def load(self) -> List[Document]:
        """Load the text file."""
        path = Path(self.file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        encoding = self.encoding
        if encoding is None and self.autodetect_encoding:
            try:
                import chardet
                with open(path, "rb") as f:
                    result = chardet.detect(f.read())
                    encoding = result.get("encoding", "utf-8")
            except ImportError:
                encoding = "utf-8"

        with open(path, "r", encoding=encoding or "utf-8") as f:
            text = f.read()

        return [
            Document(
                page_content=text,
                metadata={
                    "source": str(path),
                    "filename": path.name,
                    "encoding": encoding,
                },
            )
        ]


class JSONLoader:
    """JSON file loader."""

    def __init__(
        self,
        file_path: str,
        jq_schema: Optional[str] = None,
        text_content: bool = True,
    ):
        self.file_path = file_path
        self.jq_schema = jq_schema
        self.text_content = text_content

    def load(self) -> List[Document]:
        """Load the JSON file."""
        import json

        path = Path(self.file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # If jq_schema is provided, try to extract specific fields
        if self.jq_schema and isinstance(data, list):
            documents = []
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    # Simple key extraction (not full jq support)
                    key = self.jq_schema.lstrip(".")
                    content = item.get(key, str(item))
                else:
                    content = str(item)

                documents.append(
                    Document(
                        page_content=str(content),
                        metadata={
                            "source": str(path),
                            "filename": path.name,
                            "index": i,
                        },
                    )
                )
            return documents

        # Default: entire JSON as one document
        if self.text_content:
            content = json.dumps(data, indent=2)
        else:
            content = str(data)

        return [
            Document(
                page_content=content,
                metadata={
                    "source": str(path),
                    "filename": path.name,
                },
            )
        ]


class CSVLoader:
    """CSV file loader."""

    def __init__(
        self,
        file_path: str,
        source_column: Optional[str] = None,
        encoding: Optional[str] = None,
    ):
        self.file_path = file_path
        self.source_column = source_column
        self.encoding = encoding

    def load(self) -> List[Document]:
        """Load the CSV file, one document per row."""
        import csv

        path = Path(self.file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        documents = []
        with open(path, "r", encoding=self.encoding or "utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Combine row into text
                content = "\n".join(f"{k}: {v}" for k, v in row.items() if v)

                metadata = {
                    "source": str(path),
                    "filename": path.name,
                    "row": i,
                }
                if self.source_column and self.source_column in row:
                    metadata["source_value"] = row[self.source_column]

                documents.append(Document(page_content=content, metadata=metadata))

        return documents
