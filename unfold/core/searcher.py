"""
Advanced search engine with fuzzy matching, ranking, and caching.
"""

import os
import time
from typing import Any

import textdistance
from Levenshtein import distance as levenshtein_distance

from .database import DatabaseManager


class SearchResult:
    """Represents a search result with ranking information."""

    def __init__(self, file_info: dict[str, Any], score: float, match_type: str):
        self.path = file_info["path"]
        self.name = file_info["name"]
        self.size = file_info.get("size")
        self.file_type = file_info.get("file_type")
        self.is_directory = file_info.get("is_directory", False)
        self.access_count = file_info.get("access_count", 0)
        self.last_accessed = file_info.get("last_accessed")
        self.modified_time = file_info.get("modified_time")
        self.score = score
        self.match_type = match_type

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "file_type": self.file_type,
            "is_directory": self.is_directory,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "modified_time": self.modified_time,
            "score": self.score,
            "match_type": self.match_type,
        }

    def __repr__(self) -> str:
        return f"SearchResult(path='{self.path}', score={self.score:.3f}, type='{self.match_type}')"


class FileSearcher:
    """
    Advanced file searcher with multiple ranking algorithms.
    Implements fuzzy matching, frequency/recency scoring, and result caching.
    """

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        enable_fuzzy: bool = True,
        fuzzy_threshold: float = 0.6,
        max_results: int = 50,
        cache_results: bool = True,
    ):
        self.db = db_manager or DatabaseManager()
        self.enable_fuzzy = enable_fuzzy
        self.fuzzy_threshold = fuzzy_threshold
        self.max_results = max_results
        self.cache_results = cache_results

        # Weights for different scoring factors
        self.weights = {
            "exact_match": 100.0,
            "starts_with": 80.0,
            "contains": 60.0,
            "fuzzy_high": 50.0,
            "fuzzy_medium": 30.0,
            "fuzzy_low": 15.0,
            "frequency_factor": 0.1,
            "recency_factor": 0.05,
            "file_type_bonus": 10.0,
        }

    def _calculate_string_similarity(self, query: str, target: str) -> float:
        """Calculate similarity between query and target string."""
        if not query or not target:
            return 0.0

        query_lower = query.lower()
        target_lower = target.lower()

        # Exact match
        if query_lower == target_lower:
            return 1.0

        # Starts with match
        if target_lower.startswith(query_lower):
            return 0.9

        # Contains match
        if query_lower in target_lower:
            return 0.8

        # Fuzzy matching using multiple algorithms
        if self.enable_fuzzy and len(query) > 2:
            # Levenshtein distance
            lev_sim = 1 - (
                levenshtein_distance(query_lower, target_lower)
                / max(len(query_lower), len(target_lower))
            )

            # Jaro-Winkler similarity
            jaro_sim = textdistance.jaro_winkler(query_lower, target_lower)

            # Jaccard similarity (for word-based matching)
            jaccard_sim = textdistance.jaccard(
                query_lower.split(), target_lower.split()
            )

            # Combined fuzzy score
            fuzzy_score = max(lev_sim, jaro_sim, jaccard_sim)

            if fuzzy_score >= self.fuzzy_threshold:
                return fuzzy_score * 0.7  # Penalty for fuzzy matches

        return 0.0

    def _calculate_frequency_recency_score(
        self, access_count: int, last_accessed: float | None
    ) -> float:
        """Calculate frequency and recency score (FR algorithm)."""
        current_time = time.time()

        # Frequency component
        frequency_score = min(access_count * self.weights["frequency_factor"], 10.0)

        # Recency component
        recency_score = 0.0
        if last_accessed:
            hours_since_access = (current_time - last_accessed) / 3600
            # Decay function: more recent = higher score
            recency_score = max(
                0, 10 - (hours_since_access / 24) * self.weights["recency_factor"]
            )

        return frequency_score + recency_score

    def _get_match_type_and_base_score(
        self, query: str, name: str
    ) -> tuple[str, float]:
        """Determine match type and base score."""
        similarity = self._calculate_string_similarity(query, name)

        if similarity >= 1.0:
            return "exact", self.weights["exact_match"]
        elif similarity >= 0.9:
            return "starts_with", self.weights["starts_with"]
        elif similarity >= 0.8:
            return "contains", self.weights["contains"]
        elif similarity >= 0.7:
            return "fuzzy_high", self.weights["fuzzy_high"]
        elif similarity >= 0.5:
            return "fuzzy_medium", self.weights["fuzzy_medium"]
        elif similarity >= self.fuzzy_threshold:
            return "fuzzy_low", self.weights["fuzzy_low"]
        else:
            return "no_match", 0.0

    def _apply_file_type_bonus(
        self, query: str, file_type: str | None, base_score: float
    ) -> float:
        """Apply bonus for file type preferences."""
        if not file_type:
            return base_score

        # Common application extensions get bonus when query looks like app name
        app_extensions = {".exe", ".app", ".deb", ".dmg", ".pkg"}
        if file_type in app_extensions and len(query) > 3:
            return base_score + self.weights["file_type_bonus"]

        # Programming files bonus for technical queries
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".go",
            ".rs",
        }
        if file_type in code_extensions and any(
            char in query for char in ["_", "-", "test", "spec"]
        ):
            return base_score + (self.weights["file_type_bonus"] * 0.5)

        return base_score

    def _rank_results(
        self, results: list[dict[str, Any]], query: str
    ) -> list[SearchResult]:
        """Rank search results using multiple algorithms."""
        ranked_results = []

        for result in results:
            # Base similarity score
            match_type, base_score = self._get_match_type_and_base_score(
                query, result["name"]
            )

            if base_score == 0:
                continue

            # Frequency and recency score
            fr_score = self._calculate_frequency_recency_score(
                result.get("access_count", 0), result.get("last_accessed")
            )

            # File type bonus
            final_score = self._apply_file_type_bonus(
                query, result.get("file_type"), base_score
            )

            # Combine all scores
            total_score = final_score + fr_score

            # Path length penalty (shorter paths often more relevant)
            path_length_penalty = len(result["path"].split(os.sep)) * 0.5
            total_score = max(0, total_score - path_length_penalty)

            ranked_results.append(SearchResult(result, total_score, match_type))

        # Sort by score (descending)
        ranked_results.sort(key=lambda x: x.score, reverse=True)

        return ranked_results[: self.max_results]

    def search(
        self,
        query: str,
        file_types: list[str] | None = None,
        directories_only: bool = False,
        files_only: bool = False,
    ) -> list[SearchResult]:
        """
        Perform advanced search with ranking and filtering.

        Args:
            query: Search query string
            file_types: Optional list of file extensions to filter by
            directories_only: Only return directories
            files_only: Only return files (not directories)

        Returns:
            List of ranked SearchResult objects
        """
        if not query.strip():
            return []

        # Check cache first
        cache_key = f"{query}:{file_types}:{directories_only}:{files_only}"
        if self.cache_results:
            cached = self.db.get_cached_search(cache_key)
            if cached:
                return [
                    SearchResult(result, result["score"], result["match_type"])
                    for result in cached
                ]

        # Get raw results from database
        raw_results = self.db.search_files(query, limit=self.max_results * 2)

        # Convert to list of dicts for processing
        results = [dict(row) for row in raw_results]

        # Apply filters
        if file_types:
            file_types_lower = [ft.lower() for ft in file_types]
            results = [
                r for r in results if r.get("file_type", "").lower() in file_types_lower
            ]

        if directories_only:
            results = [r for r in results if r.get("is_directory", False)]
        elif files_only:
            results = [r for r in results if not r.get("is_directory", False)]

        # Rank results
        ranked_results = self._rank_results(results, query)

        # Cache results
        if self.cache_results and ranked_results:
            cache_data = [result.to_dict() for result in ranked_results]
            self.db.cache_search(cache_key, cache_data)

        return ranked_results

    def search_by_pattern(self, pattern: str) -> list[SearchResult]:
        """Search files using glob-like patterns."""
        # This could be extended to support regex or glob patterns
        return self.search(pattern)

    def get_recent_files(self, limit: int = 20) -> list[SearchResult]:
        """Get most recently accessed files."""

        cursor = self.db.conn.cursor()

        cursor.execute(
            """
            SELECT * FROM files 
            WHERE last_accessed IS NOT NULL
            ORDER BY last_accessed DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = [dict(row) for row in cursor.fetchall()]

        # Create SearchResult objects with recency-based scoring
        search_results = []
        for i, result in enumerate(results):
            # Score based on recency rank
            score = max(100 - (i * 5), 10)
            search_results.append(SearchResult(result, score, "recent"))

        return search_results

    def get_frequent_files(self, limit: int = 20) -> list[SearchResult]:
        """Get most frequently accessed files."""

        cursor = self.db.conn.cursor()

        cursor.execute(
            """
            SELECT * FROM files 
            WHERE access_count > 0
            ORDER BY access_count DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = [dict(row) for row in cursor.fetchall()]

        # Create SearchResult objects with frequency-based scoring
        search_results = []
        for result in results:
            score = min(result["access_count"] * 10, 100)
            search_results.append(SearchResult(result, score, "frequent"))

        return search_results

    def update_access_stats(self, file_path: str) -> None:
        """Update access statistics when a file is opened."""
        self.db.update_access_stats(file_path)

    def clear_cache(self) -> None:
        """Clear search cache."""
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM search_cache")
        self.db.conn.commit()

    def get_search_stats(self) -> dict[str, Any]:
        """Get search engine statistics."""
        stats = self.db.get_stats()
        stats.update(
            {
                "fuzzy_enabled": self.enable_fuzzy,
                "fuzzy_threshold": self.fuzzy_threshold,
                "max_results": self.max_results,
                "cache_enabled": self.cache_results,
            }
        )
        return stats
