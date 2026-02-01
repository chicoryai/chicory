"""
Base provider for analytics services.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ToolsProvider(ABC):
    """
    Base class for analytics service providers.

    This minimal base class provides essential infrastructure without forcing
    database abstractions. Each provider implements its own natural interface.
    """

    def __init__(self):
        self.credentials: Optional[Dict[str, Any]] = None
        self.is_initialized = False
        self._client = None

    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """
        Initialize the provider with credentials.

        Args:
            credentials: Provider-specific credential configuration
        """
        self.credentials = credentials
        logger.info(f"Initializing {self.__class__.__name__}")

        try:
            await self._initialize_client()
            self.is_initialized = True
            logger.info(f"{self.__class__.__name__} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            raise

    @abstractmethod
    async def _initialize_client(self) -> None:
        """
        Provider-specific client initialization.
        Must be implemented by each provider.
        """
        pass

    async def cleanup(self) -> None:
        """
        Clean up provider resources.
        Override in providers that need custom cleanup.
        """
        logger.info(f"Cleaning up {self.__class__.__name__}")
        self._client = None
        self.is_initialized = False

    def _ensure_initialized(self) -> None:
        """Check that provider is initialized before operations."""
        if not self.is_initialized:
            raise RuntimeError(f"{self.__class__.__name__} not initialized")

    def _log_operation(self, operation: str, **kwargs) -> None:
        """Log provider operations for debugging."""
        logger.debug(f"{self.__class__.__name__}.{operation}: {kwargs}")

    def _get_metadata(self) -> Dict[str, Any]:
        """Get provider metadata for debugging."""
        return {
            "provider": self.__class__.__name__,
            "initialized": self.is_initialized,
            "has_credentials": self.credentials is not None,
            "has_client": self._client is not None
        }
