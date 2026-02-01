"""
Configuration management for DB MCP Server.
"""

import os
from typing import Optional


class Config:
    """Configuration settings for the DB MCP Server."""
    
    def __init__(self):
        # API Configuration
        self.API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # HTTP Transport Configuration
        self.MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "http")  # "http" or "stdio"
        self.MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
        self.MCP_PORT = int(os.getenv("MCP_PORT", "8080"))
        
        # Cache Configuration
        self.CONNECTION_CACHE_TTL = int(os.getenv("CONNECTION_CACHE_TTL", "3600"))  # 1 hour default
        self.CONNECTION_CACHE_MAX_SIZE = int(os.getenv("CONNECTION_CACHE_MAX_SIZE", "100"))
        
        # Query Limits
        self.DEFAULT_QUERY_LIMIT = int(os.getenv("DEFAULT_QUERY_LIMIT", "100"))
        self.MAX_QUERY_LIMIT = int(os.getenv("MAX_QUERY_LIMIT", "1000"))
        self.DEFAULT_SAMPLE_LIMIT = int(os.getenv("DEFAULT_SAMPLE_LIMIT", "10"))
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Cleanup interval (in seconds)
        self.CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "300"))  # 5 minutes
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        if not self.API_BASE_URL:
            raise ValueError("API_BASE_URL is required")
        
        if self.CONNECTION_CACHE_TTL <= 0:
            raise ValueError("CONNECTION_CACHE_TTL must be positive")
        
        if self.CONNECTION_CACHE_MAX_SIZE <= 0:
            raise ValueError("CONNECTION_CACHE_MAX_SIZE must be positive")
        
        if self.DEFAULT_QUERY_LIMIT <= 0 or self.DEFAULT_QUERY_LIMIT > self.MAX_QUERY_LIMIT:
            raise ValueError("DEFAULT_QUERY_LIMIT must be positive and <= MAX_QUERY_LIMIT")
        
        return True
