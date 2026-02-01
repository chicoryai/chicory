"""
Connection cache manager for database clients.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Union
import threading

logger = logging.getLogger(__name__)


class ConnectionCacheManager:
    """Manages cached database connections with TTL and cleanup."""
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 100):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_started = False
    
    def _start_cleanup_task(self):
        """Start the background cleanup task."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
                self._cleanup_started = True
        except RuntimeError:
            # No event loop running, cleanup task will be started later
            pass
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired connections."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                self.cleanup_expired()
            except asyncio.CancelledError:
                logger.info("Cache cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def _generate_connection_key(self, provider_name: str, connection_params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a unique connection key based on provider name and connection parameters."""
        if connection_params is None:
            return provider_name
        
        # Create a hash of the connection parameters for uniqueness
        param_str = str(sorted(connection_params.items()))
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{provider_name}_{param_hash}"
    
    def cache_connection(self, project_id: str, provider_name: str, client: Any, 
                        connection_params: Optional[Dict[str, Any]] = None) -> str:
        """Cache a database connection and return the connection key."""
        connection_key = self._generate_connection_key(provider_name, connection_params)
        
        with self.lock:
            # Start cleanup task if not already started
            if not self._cleanup_started:
                self._start_cleanup_task()
            
            # Count total connections across all projects
            total_connections = sum(len(project_cache) for project_cache in self.cache.values())
            
            # Enforce max size by removing oldest entries
            if total_connections >= self.max_size:
                # Find the oldest connection across all projects
                oldest_project = None
                oldest_key = None
                oldest_time = datetime.now()
                
                for proj_id, proj_cache in self.cache.items():
                    for conn_key, entry in proj_cache.items():
                        if entry['created_at'] < oldest_time:
                            oldest_time = entry['created_at']
                            oldest_project = proj_id
                            oldest_key = conn_key
                
                if oldest_project and oldest_key:
                    self._remove_connection(oldest_project, oldest_key)

            if project_id not in self.cache:
                self.cache[project_id] = {}

            self.cache[project_id][connection_key] = {
                'client': client,
                'provider_name': provider_name,
                'connection_params': connection_params,
                'created_at': datetime.now(),
                'last_used': datetime.now()
            }
            
            logger.info(f"Cached connection for project: {project_id}, key: {connection_key}")
            return connection_key
    
    def get_connection(self, project_id: str, provider_name: str, 
                      connection_params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get a cached database connection if valid."""
        connection_key = self._generate_connection_key(provider_name, connection_params)
        
        with self.lock:
            if project_id not in self.cache:
                return None

            if connection_key not in self.cache[project_id]:
                return None
            
            entry = self.cache[project_id][connection_key]
            
            # Check if expired
            if self._is_expired(entry):
                self._remove_connection(project_id, connection_key)
                return None
            
            # Update last used time
            entry['last_used'] = datetime.now()
            
            logger.debug(f"Retrieved cached connection for project: {project_id}, key: {connection_key}")
            return entry['client']
    
    def get_connection_by_key(self, project_id: str, connection_key: str) -> Optional[Any]:
        """Get a cached database connection by its key if valid."""
        with self.lock:
            if project_id not in self.cache:
                return None

            if connection_key not in self.cache[project_id]:
                return None
            
            entry = self.cache[project_id][connection_key]
            
            # Check if expired
            if self._is_expired(entry):
                self._remove_connection(project_id, connection_key)
                return None
            
            # Update last used time
            entry['last_used'] = datetime.now()
            
            logger.debug(f"Retrieved cached connection for project: {project_id}, key: {connection_key}")
            return entry['client']
    
    def remove_connection(self, project_id: str, provider_name: str, 
                         connection_params: Optional[Dict[str, Any]] = None) -> bool:
        """Remove a specific connection from cache."""
        connection_key = self._generate_connection_key(provider_name, connection_params)
        with self.lock:
            return self._remove_connection(project_id, connection_key)
    
    def remove_connection_by_key(self, project_id: str, connection_key: str) -> bool:
        """Remove a specific connection from cache by its key."""
        with self.lock:
            return self._remove_connection(project_id, connection_key)
    
    def _remove_connection(self, project_id: str, connection_key: str) -> bool:
        """Internal method to remove connection (assumes lock is held)."""
        if project_id in self.cache and connection_key in self.cache[project_id]:
            entry = self.cache[project_id].pop(connection_key)
            
            # Remove project if no more connections
            if not self.cache[project_id]:
                del self.cache[project_id]
            
            # Cleanup the client if it has a cleanup method
            client = entry.get('client')
            if hasattr(client, 'cleanup'):
                try:
                    if asyncio.iscoroutinefunction(client.cleanup):
                        asyncio.create_task(client.cleanup())
                    else:
                        client.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up client for {project_id}:{connection_key}: {e}")
            
            logger.info(f"Removed cached connection for project: {project_id}, key: {connection_key}")
            return True
        return False
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is expired."""
        age = datetime.now() - entry['created_at']
        return age > timedelta(seconds=self.ttl_seconds)
    
    def cleanup_expired(self) -> int:
        """Clean up expired connections and return count of removed entries."""
        with self.lock:
            expired_connections = []
            
            for project_id, project_cache in self.cache.items():
                for connection_key, entry in project_cache.items():
                    if self._is_expired(entry):
                        expired_connections.append((project_id, connection_key))
            
            for project_id, connection_key in expired_connections:
                self._remove_connection(project_id, connection_key)
            
            if expired_connections:
                logger.info(f"Cleaned up {len(expired_connections)} expired connections")
            
            return len(expired_connections)
    
    def cleanup(self) -> None:
        """Clean up all connections and stop background tasks."""
        with self.lock:
            # Cancel cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
            
            # Clean up all connections
            all_connections = []
            for project_id, project_cache in self.cache.items():
                for connection_key in project_cache.keys():
                    all_connections.append((project_id, connection_key))
            
            for project_id, connection_key in all_connections:
                self._remove_connection(project_id, connection_key)
            
            logger.info("Cache manager cleanup completed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            now = datetime.now()
            total_connections = sum(len(project_cache) for project_cache in self.cache.values())
            
            stats = {
                'total_connections': total_connections,
                'total_projects': len(self.cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'projects': {}
            }
            
            for project_id, project_cache in self.cache.items():
                project_stats = {
                    'connection_count': len(project_cache),
                    'connections': {}
                }
                
                for connection_key, entry in project_cache.items():
                    age = now - entry['created_at']
                    last_used_age = now - entry['last_used']
                    project_stats['connections'][connection_key] = {
                        'provider_name': entry['provider_name'],
                        'age_seconds': int(age.total_seconds()),
                        'last_used_seconds_ago': int(last_used_age.total_seconds()),
                        'expired': self._is_expired(entry)
                    }
                
                stats['projects'][project_id] = project_stats
            
            return stats
    
    def list_connections(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """List all connections, optionally filtered by project."""
        with self.lock:
            result = {}
            
            projects_to_check = [project_id] if project_id else list(self.cache.keys())
            
            for proj_id in projects_to_check:
                if proj_id in self.cache:
                    result[proj_id] = {}
                    for connection_key, entry in self.cache[proj_id].items():
                        result[proj_id][connection_key] = {
                            'provider_name': entry['provider_name'],
                            'connection_params': entry.get('connection_params'),
                            'created_at': entry['created_at'].isoformat(),
                            'last_used': entry['last_used'].isoformat()
                        }
            
            return result
