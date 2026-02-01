"""
Minimal base database provider interface - infrastructure only.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DatabaseProvider(ABC):
    """
    Minimal base class for database providers.
    
    Provides common infrastructure without forcing database operation abstractions.
    Each provider implements its own database-specific methods with appropriate parameters.
    """
    
    def __init__(self):
        self.credentials: Optional[Dict[str, Any]] = None
        self._initialized = False
        self.provider_type: str = self.__class__.__name__.lower().replace('provider', '')
    
    @abstractmethod
    async def initialize(self, credentials: Dict[str, Any]) -> None:
        """
        Initialize the provider with credentials.
        
        Args:
            credentials: Database connection credentials
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    async def cleanup(self) -> None:
        """
        Clean up resources and close connections.
        Default implementation - can be overridden by providers.
        """
        try:
            # Reset initialization state
            self._initialized = False
            self.credentials = None
            
            logger.info(f"{self.provider_type} provider cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during {self.provider_type} provider cleanup: {e}")
    
    @property
    def is_initialized(self) -> bool:
        """Check if the provider is initialized."""
        return self._initialized
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get basic provider information.
        
        Returns:
            Dictionary with provider metadata
        """
        return {
            "provider_type": self.provider_type,
            "initialized": self._initialized,
            "has_credentials": self.credentials is not None
        }
