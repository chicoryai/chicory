"""
PDF document loader with page-level granularity.

Uses unstructured for parsing, with optional OCR support.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Document

logger = logging.getLogger(__name__)


class PDFLoader:
    """
    PDF loader with page-level document extraction.

    Replaces LangChain's PyPDFLoader and UnstructuredPDFLoader.
    """

    def __init__(
        self,
        file_path: str,
        strategy: str = "fast",
        extract_images: bool = False,
        infer_table_structure: bool = True,
        **unstructured_kwargs: Any,
    ):
        """
        Initialize the PDF loader.

        Args:
            file_path: Path to the PDF file.
            strategy: Parsing strategy:
                - "fast": Quick text extraction
                - "hi_res": High resolution with layout analysis
                - "ocr_only": Force OCR
            extract_images: Whether to extract images from PDF.
            infer_table_structure: Whether to detect tables.
            **unstructured_kwargs: Additional args for unstructured.
        """
        self.file_path = file_path
        self.strategy = strategy
        self.extract_images = extract_images
        self.infer_table_structure = infer_table_structure
        self.unstructured_kwargs = unstructured_kwargs

    def load(self) -> List[Document]:
        """Load PDF and return one Document per page."""
        try:
            from unstructured.partition.pdf import partition_pdf
        except ImportError:
            raise ImportError(
                "unstructured is required for PDFLoader. "
                "Install with: pip install 'unstructured[pdf]'"
            )

        path = Path(self.file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        logger.debug(f"Loading PDF with strategy={self.strategy}: {self.file_path}")

        # Partition the PDF
        elements = partition_pdf(
            filename=str(path),
            strategy=self.strategy,
            extract_images_in_pdf=self.extract_images,
            infer_table_structure=self.infer_table_structure,
            **self.unstructured_kwargs,
        )

        # Group elements by page
        pages: Dict[int, List[str]] = {}
        for el in elements:
            page_num = 0
            if hasattr(el, "metadata") and hasattr(el.metadata, "page_number"):
                page_num = el.metadata.page_number or 0

            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(str(el))

        # Create documents per page
        documents = []
        for page_num in sorted(pages.keys()):
            content = "\n\n".join(pages[page_num])
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": str(path),
                        "filename": path.name,
                        "page": page_num,
                        "total_pages": len(pages),
                    },
                )
            )

        logger.debug(f"Loaded {len(documents)} pages from PDF")
        return documents

    def load_and_split(self, text_splitter: Any = None) -> List[Document]:
        """
        Load and optionally split documents.

        Args:
            text_splitter: Optional text splitter to chunk documents.
        """
        documents = self.load()

        if text_splitter is None:
            return documents

        # Apply splitter to each document
        split_docs = []
        for doc in documents:
            if hasattr(text_splitter, "split_text"):
                chunks = text_splitter.split_text(doc.page_content)
                for i, chunk in enumerate(chunks):
                    split_docs.append(
                        Document(
                            page_content=chunk,
                            metadata={
                                **doc.metadata,
                                "chunk_index": i,
                            },
                        )
                    )
            else:
                split_docs.append(doc)

        return split_docs


class SimplePDFLoader:
    """
    Simple PDF loader using pypdf (no unstructured dependency).

    Useful for basic text extraction without OCR or layout analysis.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        """Load PDF using pypdf."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError(
                "pypdf is required for SimplePDFLoader. "
                "Install with: pip install pypdf"
            )

        path = Path(self.file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        reader = PdfReader(str(path))
        documents = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": str(path),
                        "filename": path.name,
                        "page": i + 1,
                        "total_pages": len(reader.pages),
                    },
                )
            )

        return documents
