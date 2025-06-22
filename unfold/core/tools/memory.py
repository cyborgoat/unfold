"""
Memory operations tools for MCP integration.
"""

import os
from datetime import datetime
from typing import Any


class MemoryTools:
    """Tools for memory storage and retrieval operations."""

    def __init__(self, working_directory: str = None, vector_db=None):
        """Initialize memory tools."""
        self.working_directory = working_directory or os.getcwd()
        self.vector_db = vector_db

    async def store_memory(self, content: str, memory_type: str = "short_term", 
                          importance: float = 1.0, tags: str = "", source: str = "") -> dict[str, Any]:
        """Store information in memory with metadata."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available for memory storage"}

            # Parse tags
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

            # Create memory entry
            memory_entry = {
                "content": content,
                "metadata": {
                    "memory_type": memory_type,
                    "importance": importance,
                    "tags": tag_list,
                    "timestamp": datetime.now().isoformat(),
                    "source": source or "user_input",
                    "working_directory": self.working_directory
                }
            }

            # Store in vector database
            memory_id = await self.vector_db.store_memory(memory_entry)

            return {
                "success": True,
                "memory_id": memory_id,
                "content": content,
                "memory_type": memory_type,
                "importance": importance,
                "tags": tag_list,
                "timestamp": memory_entry["metadata"]["timestamp"]
            }

        except Exception as e:
            return {"success": False, "error": f"Memory storage failed: {str(e)}"}

    async def search_memory(self, query: str, memory_type: str = "all", max_results: int = 10) -> dict[str, Any]:
        """Search stored memories."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available for memory search"}

            # Search in memory collection
            results = await self.vector_db.search_memory(query, max_results)

            formatted_results = []
            for result in results:
                metadata = result.get("metadata", {})
                
                # Filter by memory type if specified
                if memory_type != "all" and metadata.get("memory_type") != memory_type:
                    continue

                formatted_results.append({
                    "content": result.get("content", ""),
                    "memory_type": metadata.get("memory_type", "unknown"),
                    "importance": metadata.get("importance", 1.0),
                    "tags": metadata.get("tags", []),
                    "timestamp": metadata.get("timestamp", ""),
                    "source": metadata.get("source", ""),
                    "score": result.get("score", 0.0)
                })

            return {
                "success": True,
                "query": query,
                "memory_type": memory_type,
                "results": formatted_results,
                "total_found": len(formatted_results)
            }

        except Exception as e:
            return {"success": False, "error": f"Memory search failed: {str(e)}"}

    async def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored memories."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available"}

            # Get basic stats
            stats = {
                "success": True,
                "total_memories": 0,
                "memory_types": {},
                "importance_distribution": {},
                "recent_memories": 0,
                "timestamp": datetime.now().isoformat()
            }

            # Try to get collection info if available
            if hasattr(self.vector_db, 'get_collection_info'):
                info = self.vector_db.get_collection_info()
                stats.update(info)

            return stats

        except Exception as e:
            return {"success": False, "error": f"Failed to get memory stats: {str(e)}"}

    async def clear_memory(self, memory_type: str = None, older_than_days: int = None) -> dict[str, Any]:
        """Clear memories based on criteria."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available"}

            cleared_count = 0
            
            # If vector DB has clear methods, use them
            if hasattr(self.vector_db, 'clear_collection'):
                if memory_type is None and older_than_days is None:
                    # Clear all
                    self.vector_db.clear_collection()
                    cleared_count = "all"
                else:
                    # Selective clearing would need custom implementation
                    return {"success": False, "error": "Selective memory clearing not implemented yet"}

            return {
                "success": True,
                "cleared_count": cleared_count,
                "memory_type": memory_type,
                "older_than_days": older_than_days,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Memory clearing failed: {str(e)}"}

    async def summarize_conversation(self, conversation_content: str, importance: float = 1.5) -> dict[str, Any]:
        """Summarize and store conversation for long-term memory."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available"}

            # Create a summary of the conversation
            summary = f"Conversation Summary: {conversation_content[:500]}..."
            
            # Store as long-term memory with high importance
            result = await self.store_memory(
                content=summary,
                memory_type="long_term",
                importance=importance,
                tags="conversation,summary",
                source="conversation_summarizer"
            )

            if result["success"]:
                result["original_length"] = len(conversation_content)
                result["summary_length"] = len(summary)

            return result

        except Exception as e:
            return {"success": False, "error": f"Conversation summarization failed: {str(e)}"}

    async def get_memory_by_tags(self, tags: list[str], max_results: int = 20) -> dict[str, Any]:
        """Retrieve memories by tags."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available"}

            # Get all memories and filter by tags
            all_memories = await self.vector_db.get_all_memories()
            
            matching_memories = []
            for memory in all_memories:
                memory_tags = memory.get("metadata", {}).get("tags", [])
                if any(tag in memory_tags for tag in tags):
                    matching_memories.append({
                        "content": memory.get("content", ""),
                        "memory_type": memory.get("metadata", {}).get("memory_type", "unknown"),
                        "importance": memory.get("metadata", {}).get("importance", 1.0),
                        "tags": memory_tags,
                        "timestamp": memory.get("metadata", {}).get("timestamp", ""),
                        "source": memory.get("metadata", {}).get("source", "")
                    })

            # Sort by importance and timestamp
            matching_memories.sort(
                key=lambda x: (x["importance"], x["timestamp"]), 
                reverse=True
            )

            return {
                "success": True,
                "tags": tags,
                "results": matching_memories[:max_results],
                "total_found": len(matching_memories)
            }

        except Exception as e:
            return {"success": False, "error": f"Tag-based memory retrieval failed: {str(e)}"}

    async def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored memories."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available"}

            # Get all memories
            all_memories = await self.vector_db.get_all_memories()
            
            if not all_memories:
                return {
                    "success": True,
                    "total_memories": 0,
                    "memory_types": {},
                    "tag_counts": {},
                    "importance_distribution": {},
                    "timestamp": datetime.now().isoformat()
                }

            # Analyze memories
            memory_types = {}
            all_tags = []
            importance_levels = {"low": 0, "medium": 0, "high": 0}
            
            for memory in all_memories:
                metadata = memory.get("metadata", {})
                
                # Count memory types
                mem_type = metadata.get("memory_type", "unknown")
                memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
                
                # Collect tags
                tags = metadata.get("tags", [])
                all_tags.extend(tags)
                
                # Categorize importance
                importance = metadata.get("importance", 1.0)
                if importance < 0.5:
                    importance_levels["low"] += 1
                elif importance < 1.5:
                    importance_levels["medium"] += 1
                else:
                    importance_levels["high"] += 1

            # Count tag occurrences
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            return {
                "success": True,
                "total_memories": len(all_memories),
                "memory_types": memory_types,
                "tag_counts": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
                "importance_distribution": importance_levels,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Memory stats retrieval failed: {str(e)}"}

    async def clear_memory(self, memory_type: str = None, older_than_days: int = None) -> dict[str, Any]:
        """Clear memories based on criteria."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available"}

            cleared_count = 0
            
            if memory_type is None and older_than_days is None:
                # Clear all memories
                cleared_count = await self.vector_db.clear_all_memories()
            else:
                # Get all memories and filter
                all_memories = await self.vector_db.get_all_memories()
                
                memories_to_clear = []
                for memory in all_memories:
                    metadata = memory.get("metadata", {})
                    
                    should_clear = True
                    
                    # Filter by memory type
                    if memory_type and metadata.get("memory_type") != memory_type:
                        should_clear = False
                    
                    # Filter by age
                    if older_than_days and should_clear:
                        try:
                            memory_date = datetime.fromisoformat(metadata.get("timestamp", ""))
                            age_days = (datetime.now() - memory_date).days
                            if age_days < older_than_days:
                                should_clear = False
                        except ValueError:
                            should_clear = False
                    
                    if should_clear:
                        memories_to_clear.append(memory)

                # Clear selected memories
                for memory in memories_to_clear:
                    await self.vector_db.delete_memory(memory.get("id"))
                    cleared_count += 1

            return {
                "success": True,
                "cleared_count": cleared_count,
                "memory_type": memory_type,
                "older_than_days": older_than_days,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Memory clearing failed: {str(e)}"}

    async def summarize_conversation(self, conversation_content: str, importance: float = 1.5) -> dict[str, Any]:
        """Summarize and store conversation for long-term memory."""
        try:
            if not conversation_content.strip():
                return {"success": False, "error": "No conversation content provided"}

            # Create summary
            summary = f"Conversation summary from {datetime.now().strftime('%Y-%m-%d %H:%M')}: {conversation_content[:500]}..."
            
            # Store in memory
            result = await self.store_memory(
                content=summary,
                memory_type="long_term",
                importance=importance,
                tags="conversation,summary",
                source="conversation_summary"
            )

            if result["success"]:
                return {
                    "success": True,
                    "summary": summary,
                    "memory_id": result["memory_id"],
                    "timestamp": result["timestamp"]
                }
            else:
                return result

        except Exception as e:
            return {"success": False, "error": f"Conversation summarization failed: {str(e)}"} 