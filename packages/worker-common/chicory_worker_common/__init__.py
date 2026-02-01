"""
Chicory Worker Common - Shared utilities for inference and training workers.

This package consolidates shared code between inference-worker and training-worker,
eliminating ~90% code duplication.

Modules:
- cache: Redis and memory caching utilities
- integration: External service integrations (S3, databases, etc.)
- utils: Common utilities (config, logging, directory management)
- loaders: Document loading utilities (replaces LangChain loaders)
- agent: Claude Agent SDK utilities and builders
"""

__version__ = "0.1.0"
