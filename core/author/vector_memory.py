"""
Vector Memory for Author Engine (Phase 4.3)

Semantic memory using vector embeddings for context retrieval.
Uses ChromaDB for efficient similarity search.
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import hashlib

from config.logging_config import get_logger
logger = get_logger(__name__)


@dataclass
class MemoryChunk:
    """A chunk of text stored in vector memory"""
    chunk_id: str
    text: str
    chapter: int
    metadata: Dict[str, str]
    embedding: Optional[List[float]] = None


class VectorMemory:
    """
    Semantic memory using vector embeddings

    Stores chapter content as embeddings for semantic search.
    Enables retrieving relevant context from previous chapters.
    """

    def __init__(
        self,
        project_path: Path,
        collection_name: str = "author_memory",
        embedding_function = None
    ):
        """
        Initialize vector memory

        Args:
            project_path: Path to project directory
            collection_name: Name for ChromaDB collection
            embedding_function: Optional custom embedding function
        """
        self.project_path = project_path
        self.vector_db_path = project_path / "vector_db"
        self.vector_db_path.mkdir(exist_ok=True)
        self.collection_name = collection_name

        # Try to import ChromaDB
        self.client = None
        self.collection = None
        self.use_chromadb = False

        try:
            import chromadb
            from chromadb.config import Settings

            self.client = chromadb.PersistentClient(
                path=str(self.vector_db_path),
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Author project memory"}
            )

            self.use_chromadb = True

        except ImportError:
            logger.warning("ChromaDB not installed. Vector memory will use fallback mode. Install with: pip install chromadb")
            # Fallback: Store in simple dict (no semantic search)
            self.fallback_store: Dict[str, MemoryChunk] = {}

    def add_chapter_content(
        self,
        chapter: int,
        content: str,
        chunk_size: int = 1000
    ) -> int:
        """
        Add chapter content to vector memory

        Splits content into chunks and stores with embeddings.

        Args:
            chapter: Chapter number
            content: Full chapter text
            chunk_size: Size of each chunk in characters

        Returns:
            Number of chunks added
        """
        if not content.strip():
            return 0

        # Split into chunks
        chunks = self._chunk_text(content, chunk_size)

        if self.use_chromadb:
            return self._add_chunks_chromadb(chapter, chunks)
        else:
            return self._add_chunks_fallback(chapter, chunks)

    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        overlap = chunk_size // 4  # 25% overlap

        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)

        return chunks

    def _add_chunks_chromadb(self, chapter: int, chunks: List[str]) -> int:
        """Add chunks using ChromaDB"""
        if not self.collection:
            return 0

        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = self._generate_chunk_id(chapter, i, chunk)

            documents.append(chunk)
            metadatas.append({
                "chapter": str(chapter),
                "chunk_index": str(i),
                "length": str(len(chunk))
            })
            ids.append(chunk_id)

        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        return len(chunks)

    def _add_chunks_fallback(self, chapter: int, chunks: List[str]) -> int:
        """Add chunks using fallback storage (no embeddings)"""
        for i, chunk in enumerate(chunks):
            chunk_id = self._generate_chunk_id(chapter, i, chunk)

            self.fallback_store[chunk_id] = MemoryChunk(
                chunk_id=chunk_id,
                text=chunk,
                chapter=chapter,
                metadata={
                    "chapter": str(chapter),
                    "chunk_index": str(i)
                }
            )

        return len(chunks)

    def _generate_chunk_id(self, chapter: int, index: int, text: str) -> str:
        """Generate unique ID for chunk"""
        content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"ch{chapter:03d}_idx{index:03d}_{content_hash}"

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_chapters: Optional[List[int]] = None
    ) -> List[Tuple[str, float, Dict]]:
        """
        Search for relevant content

        Args:
            query: Search query
            n_results: Number of results to return
            filter_chapters: Optional list of chapters to search within

        Returns:
            List of (text, similarity_score, metadata) tuples
        """
        if self.use_chromadb:
            return self._search_chromadb(query, n_results, filter_chapters)
        else:
            return self._search_fallback(query, n_results, filter_chapters)

    def _search_chromadb(
        self,
        query: str,
        n_results: int,
        filter_chapters: Optional[List[int]]
    ) -> List[Tuple[str, float, Dict]]:
        """Search using ChromaDB semantic search"""
        if not self.collection:
            return []

        # Build filter
        where_filter = None
        if filter_chapters:
            where_filter = {
                "chapter": {"$in": [str(ch) for ch in filter_chapters]}
            }

        # Query
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )

        # Format results
        output = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i] if results['distances'] else 0.0
                similarity = 1.0 - distance  # Convert distance to similarity

                metadata = results['metadatas'][0][i] if results['metadatas'] else {}

                output.append((doc, similarity, metadata))

        return output

    def _search_fallback(
        self,
        query: str,
        n_results: int,
        filter_chapters: Optional[List[int]]
    ) -> List[Tuple[str, float, Dict]]:
        """Fallback search using simple keyword matching"""
        query_lower = query.lower()
        results = []

        for chunk in self.fallback_store.values():
            # Filter by chapter if specified
            if filter_chapters and chunk.chapter not in filter_chapters:
                continue

            # Simple keyword matching
            chunk_lower = chunk.text.lower()
            score = sum(1 for word in query_lower.split() if word in chunk_lower)

            if score > 0:
                results.append((chunk.text, float(score), chunk.metadata))

        # Sort by score and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:n_results]

    def get_chapter_summary(self, chapter: int) -> Optional[str]:
        """Get summary of a specific chapter"""
        if self.use_chromadb and self.collection:
            # Get all chunks from this chapter
            results = self.collection.get(
                where={"chapter": str(chapter)},
                limit=10
            )

            if results['documents']:
                # Return first chunk as summary
                return results['documents'][0]

        else:
            # Fallback
            for chunk in self.fallback_store.values():
                if chunk.chapter == chapter:
                    return chunk.text

        return None

    def get_recent_context(
        self,
        current_chapter: int,
        n_chapters: int = 3,
        max_chars: int = 2000
    ) -> str:
        """
        Get recent context from previous chapters

        Args:
            current_chapter: Current chapter being written
            n_chapters: Number of recent chapters to include
            max_chars: Maximum characters to return

        Returns:
            Concatenated recent context
        """
        context_parts = []
        total_chars = 0

        # Get content from recent chapters
        for ch in range(max(1, current_chapter - n_chapters), current_chapter):
            summary = self.get_chapter_summary(ch)

            if summary:
                # Truncate if needed
                remaining = max_chars - total_chars
                if remaining <= 0:
                    break

                if len(summary) > remaining:
                    summary = summary[:remaining] + "..."

                context_parts.append(f"[Chapter {ch}]\n{summary}")
                total_chars += len(summary)

        return "\n\n".join(context_parts) if context_parts else ""

    def search_for_character(self, character_name: str, n_results: int = 5) -> List[str]:
        """Search for mentions of a character"""
        results = self.search(character_name, n_results=n_results)
        return [text for text, score, metadata in results]

    def search_for_theme(self, theme: str, n_results: int = 10) -> List[Tuple[str, int]]:
        """
        Search for theme/motif occurrences

        Returns:
            List of (text, chapter) tuples
        """
        results = self.search(theme, n_results=n_results)

        return [
            (text, int(metadata.get('chapter', 0)))
            for text, score, metadata in results
        ]

    def clear(self) -> None:
        """Clear all vector memory"""
        if self.use_chromadb and self.client:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Author project memory"}
                )
            except Exception as e:
                logger.warning(f"Could not clear ChromaDB collection: {e}")

        else:
            self.fallback_store.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get memory statistics"""
        if self.use_chromadb and self.collection:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "backend": "chromadb"
            }
        else:
            return {
                "total_chunks": len(self.fallback_store),
                "backend": "fallback"
            }
