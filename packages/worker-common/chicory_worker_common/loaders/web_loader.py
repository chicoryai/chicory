"""
Web document loaders - replaces LangChain web loaders.

Provides sync and async URL loading with BeautifulSoup processing.
"""
import logging
from typing import Any, Dict, List, Optional

from .base import Document

logger = logging.getLogger(__name__)


class WebLoader:
    """
    Synchronous web page loader using requests and BeautifulSoup.

    Replaces LangChain's WebBaseLoader.
    """

    def __init__(
        self,
        url: str,
        verify_ssl: bool = False,
        headers: Optional[Dict[str, str]] = None,
        parser: str = "html.parser",
    ):
        """
        Initialize the web loader.

        Args:
            url: URL to load.
            verify_ssl: Whether to verify SSL certificates.
            headers: Optional HTTP headers.
            parser: BeautifulSoup parser to use.
        """
        self.url = url
        self.verify_ssl = verify_ssl
        self.headers = headers or {}
        self.parser = parser

    def load(self) -> List[Document]:
        """Load the web page and return as Document objects."""
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "requests and beautifulsoup4 are required for WebLoader. "
                "Install with: pip install requests beautifulsoup4"
            )

        logger.debug(f"Loading URL: {self.url}")

        response = requests.get(
            self.url,
            headers=self.headers,
            verify=self.verify_ssl,
            timeout=30,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, self.parser)

        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Get text with preserved structure
        text = soup.get_text(separator="\n", strip=True)

        # Remove excessive newlines
        lines = (line.strip() for line in text.splitlines())
        text = "\n".join(line for line in lines if line)

        return [
            Document(
                page_content=text,
                metadata={
                    "source": self.url,
                    "title": soup.title.string if soup.title else "",
                    "content_type": response.headers.get("content-type", ""),
                },
            )
        ]


class AsyncWebLoader:
    """
    Asynchronous web page loader using aiohttp and BeautifulSoup.

    Replaces LangChain's AsyncHtmlLoader.
    """

    def __init__(
        self,
        urls: List[str],
        verify_ssl: bool = False,
        headers: Optional[Dict[str, str]] = None,
        parser: str = "html.parser",
    ):
        """
        Initialize the async web loader.

        Args:
            urls: List of URLs to load.
            verify_ssl: Whether to verify SSL certificates.
            headers: Optional HTTP headers.
            parser: BeautifulSoup parser to use.
        """
        self.urls = urls if isinstance(urls, list) else [urls]
        self.verify_ssl = verify_ssl
        self.headers = headers or {}
        self.parser = parser

    async def aload(self) -> List[Document]:
        """Asynchronously load web pages and return as Document objects."""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "aiohttp and beautifulsoup4 are required for AsyncWebLoader. "
                "Install with: pip install aiohttp beautifulsoup4"
            )

        import ssl

        ssl_context = None if self.verify_ssl else ssl.create_default_context()
        if not self.verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        documents = []
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            for url in self.urls:
                try:
                    logger.debug(f"Async loading URL: {url}")
                    async with session.get(
                        url,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        content = await response.text()

                        soup = BeautifulSoup(content, self.parser)

                        # Remove script and style elements
                        for element in soup(["script", "style", "noscript"]):
                            element.decompose()

                        # Get text with preserved structure
                        text = soup.get_text(separator="\n", strip=True)

                        # Remove excessive newlines
                        lines = (line.strip() for line in text.splitlines())
                        text = "\n".join(line for line in lines if line)

                        documents.append(
                            Document(
                                page_content=text,
                                metadata={
                                    "source": url,
                                    "title": soup.title.string if soup.title else "",
                                    "content_type": response.headers.get("content-type", ""),
                                },
                            )
                        )
                except Exception as e:
                    logger.error(f"Error loading {url}: {e}")
                    documents.append(
                        Document(
                            page_content=f"Error loading URL: {e}",
                            metadata={"source": url, "error": str(e)},
                        )
                    )

        return documents

    def load(self) -> List[Document]:
        """Synchronous wrapper for async load."""
        import asyncio
        return asyncio.run(self.aload())


class RawHtmlLoader:
    """
    Loader that returns raw HTML content without parsing.

    Useful when you need the original HTML structure.
    """

    def __init__(
        self,
        urls: List[str],
        verify_ssl: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.urls = urls if isinstance(urls, list) else [urls]
        self.verify_ssl = verify_ssl
        self.headers = headers or {}

    async def aload(self) -> List[Document]:
        """Asynchronously load raw HTML from URLs."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError(
                "aiohttp is required for RawHtmlLoader. "
                "Install with: pip install aiohttp"
            )

        import ssl

        ssl_context = None if self.verify_ssl else ssl.create_default_context()
        if not self.verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        documents = []
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            for url in self.urls:
                try:
                    logger.debug(f"Loading raw HTML from: {url}")
                    async with session.get(
                        url,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        content = await response.text()
                        documents.append(
                            Document(
                                page_content=content,
                                metadata={
                                    "source": url,
                                    "content_type": response.headers.get("content-type", ""),
                                },
                            )
                        )
                except Exception as e:
                    logger.error(f"Error loading {url}: {e}")
                    documents.append(
                        Document(
                            page_content=f"Error loading URL: {e}",
                            metadata={"source": url, "error": str(e)},
                        )
                    )

        return documents

    def load(self) -> List[Document]:
        """Synchronous wrapper for async load."""
        import asyncio
        return asyncio.run(self.aload())


class BeautifulSoupTransformer:
    """
    Transform HTML documents by extracting text with BeautifulSoup.

    Replaces LangChain's BeautifulSoupTransformer.
    """

    def __init__(self, parser: str = "html.parser"):
        self.parser = parser

    def transform_documents(
        self,
        documents: List[Document],
        tags_to_extract: Optional[List[str]] = None,
        remove_unwanted_tags: Optional[List[str]] = None,
    ) -> List[Document]:
        """
        Transform documents by extracting text from HTML.

        Args:
            documents: List of documents with HTML content.
            tags_to_extract: If specified, only extract text from these tags.
            remove_unwanted_tags: Tags to remove before extraction.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "beautifulsoup4 is required for BeautifulSoupTransformer. "
                "Install with: pip install beautifulsoup4"
            )

        remove_tags = remove_unwanted_tags or ["script", "style", "noscript"]
        transformed = []

        for doc in documents:
            soup = BeautifulSoup(doc.page_content, self.parser)

            # Remove unwanted tags
            for tag in remove_tags:
                for element in soup(tag):
                    element.decompose()

            # Extract text from specific tags or all
            if tags_to_extract:
                text_parts = []
                for tag in tags_to_extract:
                    for element in soup.find_all(tag):
                        text_parts.append(element.get_text(separator="\n", strip=True))
                text = "\n\n".join(text_parts)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive newlines
            lines = (line.strip() for line in text.splitlines())
            text = "\n".join(line for line in lines if line)

            transformed.append(
                Document(
                    page_content=text,
                    metadata=doc.metadata,
                )
            )

        return transformed
