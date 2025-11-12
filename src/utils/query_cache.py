"""
Query Result Cache - Cache query results for improved performance
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class QueryResultCache:
    """Cache query results with TTL (Time To Live) support"""

    def __init__(self, cache_dir: str = "data", ttl_minutes: int = 60):
        """
        Initialize query result cache.

        Args:
            cache_dir: Directory to store cache files
            ttl_minutes: Time to live for cached results in minutes (default: 60)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "query_cache.json"
        self.ttl_minutes = ttl_minutes
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self._writes_since_last_save = 0
        self._load_cache()

    def _generate_cache_key(self, sql: str, params: Optional[Dict] = None) -> str:
        """Generate a unique cache key for a query"""
        # Normalize SQL (remove extra whitespace, convert to uppercase for comparison)
        normalized_sql = " ".join(sql.upper().split())
        
        # Include parameters if provided
        cache_data = {"sql": normalized_sql}
        if params:
            cache_data["params"] = sorted(params.items())
        
        # Generate hash
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _load_cache(self):
        """Load cache from disk"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert timestamp strings back to datetime objects for validation
                    now = datetime.now()
                    for key, value in data.items():
                        # Check if cache entry is still valid
                        cached_at = datetime.fromisoformat(value["cached_at"])
                        if (now - cached_at).total_seconds() < (self.ttl_minutes * 60):
                            self.memory_cache[key] = value
                    logger.info(f"Loaded {len(self.memory_cache)} valid cache entries")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self.memory_cache = {}

    def _save_cache(self):
        """Save cache to disk"""
        try:
            # Clean expired entries before saving
            self._clean_expired_entries()
            
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_cache, f, indent=2, default=str)
            logger.debug(f"Saved {len(self.memory_cache)} cache entries to disk")
            self._writes_since_last_save = 0
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _clean_expired_entries(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = []
        
        for key, value in self.memory_cache.items():
            cached_at = datetime.fromisoformat(value["cached_at"])
            if (now - cached_at).total_seconds() >= (self.ttl_minutes * 60):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned {len(expired_keys)} expired cache entries")

    def _is_expired(self, cached_entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is expired"""
        cached_at = datetime.fromisoformat(cached_entry["cached_at"])
        now = datetime.now()
        return (now - cached_at).total_seconds() >= (self.ttl_minutes * 60)

    def get_cached_result(
        self, sql: str, params: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        Get cached result if available and valid.

        Args:
            sql: SQL query string
            params: Optional query parameters

        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._generate_cache_key(sql, params)
        
        if cache_key in self.memory_cache:
            cached_entry = self.memory_cache[cache_key]
            
            # Check if expired
            if not self._is_expired(cached_entry):
                logger.info(f"Cache HIT for query: {sql[:50]}...")
                return cached_entry["result"]
            else:
                # Remove expired entry
                del self.memory_cache[cache_key]
                logger.debug(f"Cache entry expired for query: {sql[:50]}...")
        
        logger.debug(f"Cache MISS for query: {sql[:50]}...")
        return None

    def cache_result(
        self, sql: str, result: Any, params: Optional[Dict] = None
    ) -> None:
        """
        Cache query result.

        Args:
            sql: SQL query string
            result: Query result to cache
            params: Optional query parameters
        """
        cache_key = self._generate_cache_key(sql, params)
        
        # Prepare result for caching (handle non-serializable objects)
        try:
            # Try to serialize result to ensure it can be cached
            json.dumps(result, default=str)
            serializable_result = result
        except (TypeError, ValueError):
            # If result contains non-serializable objects, convert to string representation
            logger.warning("Result contains non-serializable objects, converting to string")
            serializable_result = str(result)
        
        cache_entry = {
            "sql": sql,
            "result": serializable_result,
            "cached_at": datetime.now().isoformat(),
            "params": params,
        }
        
        self.memory_cache[cache_key] = cache_entry
        logger.info(f"Cached result for query: {sql[:50]}...")
        self._writes_since_last_save += 1
        
        # Persist more aggressively but batch a few writes together
        if self._writes_since_last_save >= 3:
            self._save_cache()

    def invalidate_cache(self, sql: Optional[str] = None):
        """
        Invalidate cache entries.

        Args:
            sql: Specific SQL query to invalidate, or None to clear all cache
        """
        if sql is None:
            # Clear all cache
            self.memory_cache.clear()
            logger.info("Cleared all cache entries")
        else:
            # Clear specific query cache
            cache_key = self._generate_cache_key(sql)
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                logger.info(f"Invalidated cache for query: {sql[:50]}...")
        
        self._save_cache()

    def refresh(self):
        """Public helper to drop expired entries and persist the current cache."""
        self._clean_expired_entries()
        self._save_cache()

    def clear(self):
        """Public helper to remove all cache entries."""
        self.invalidate_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self._clean_expired_entries()
        
        return {
            "total_entries": len(self.memory_cache),
            "ttl_minutes": self.ttl_minutes,
            "cache_file": str(self.cache_file),
            "cache_size_mb": self._get_cache_size_mb(),
        }

    def _get_cache_size_mb(self) -> float:
        """Get cache file size in MB"""
        try:
            if self.cache_file.exists():
                size_bytes = self.cache_file.stat().st_size
                return round(size_bytes / (1024 * 1024), 2)
            return 0.0
        except Exception:
            return 0.0


# Global cache instance
_query_cache: Optional[QueryResultCache] = None


def get_query_cache(ttl_minutes: int = 60) -> QueryResultCache:
    """Get or create global query cache instance"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryResultCache(ttl_minutes=ttl_minutes)
    return _query_cache


