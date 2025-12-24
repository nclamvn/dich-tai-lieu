"""
Streaming Translation Module

Provides incremental translation results for improved user experience
and memory-efficient processing of large documents.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Callable, Any, List
from pathlib import Path
from enum import Enum


class StreamState(Enum):
    """States of a streaming translation"""
    INITIALIZING = "initializing"
    STREAMING = "streaming"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StreamChunk:
    """
    A single chunk of streamed translation

    Attributes:
        chunk_id: Unique chunk identifier
        chunk_index: Sequential chunk number
        original_text: Original text for this chunk
        translated_text: Translated text for this chunk
        confidence: Translation confidence score (0.0 - 1.0)
        timestamp: When this chunk was produced
        metadata: Additional chunk metadata
    """
    chunk_id: str
    chunk_index: int
    original_text: str
    translated_text: str
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class StreamProgress:
    """
    Progress information for streaming translation

    Attributes:
        total_chunks: Total number of chunks to process
        completed_chunks: Number of completed chunks
        current_chunk_index: Index of chunk being processed
        state: Current stream state
        elapsed_time_sec: Time elapsed since start
        estimated_remaining_sec: Estimated time to completion
        error_message: Error message if state is FAILED
    """
    total_chunks: int
    completed_chunks: int
    current_chunk_index: int
    state: StreamState
    elapsed_time_sec: float = 0.0
    estimated_remaining_sec: float = 0.0
    error_message: Optional[str] = None

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100.0


class StreamingTranslator:
    """
    Streaming translation with incremental result delivery

    This translator provides:
    - Faster first-token latency (results stream as they're ready)
    - Memory-efficient processing (writes to disk incrementally)
    - Real-time progress updates
    - Pause/resume capability
    - Checkpoint support for recovery

    Example:
        translator = StreamingTranslator(base_translator)

        # Stream translation with progress updates
        async for chunk in translator.stream_translate(
            text=document_text,
            output_file=Path("output.txt")
        ):
            print(f"Chunk {chunk.chunk_index}: {chunk.translated_text[:50]}...")

        # Or process with callback
        def on_chunk(chunk: StreamChunk):
            print(f"Progress: {chunk.chunk_index} chunks")

        result = await translator.translate_streaming(
            text=document_text,
            on_chunk_callback=on_chunk
        )
    """

    def __init__(
        self,
        base_translator: Any,
        write_interval: int = 5,
        buffer_size: int = 10
    ):
        """
        Initialize streaming translator

        Args:
            base_translator: Base TranslatorEngine instance
            write_interval: Write to disk every N chunks
            buffer_size: Number of chunks to buffer in memory
        """
        self.base_translator = base_translator
        self.write_interval = write_interval
        self.buffer_size = buffer_size

        # Stream state
        self._state = StreamState.INITIALIZING
        self._chunks_buffer: List[StreamChunk] = []
        self._total_chunks = 0
        self._completed_chunks = 0
        self._start_time = 0.0
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        self._cancel_flag = False

    async def stream_translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        output_file: Optional[Path] = None,
        chunk_size: int = 1000
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream translation results as they become available

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            output_file: Optional file to write results to
            chunk_size: Characters per chunk

        Yields:
            StreamChunk objects as translation progresses

        Example:
            async for chunk in translator.stream_translate(text, "en", "vi"):
                print(f"Received: {chunk.translated_text}")
        """
        self._initialize_stream(text, chunk_size)

        # Open output file if specified
        file_handle = None
        if output_file:
            file_handle = open(output_file, 'w', encoding='utf-8')

        try:
            # Import chunker
            from ..chunker import SmartChunker

            # Create chunks
            chunker = SmartChunker(max_chars=chunk_size, context_window=100)
            text_chunks = chunker.create_chunks(text)
            self._total_chunks = len(text_chunks)

            self._state = StreamState.STREAMING

            # Process and stream each chunk
            for idx, text_chunk in enumerate(text_chunks):
                # Check for cancellation
                if self._cancel_flag:
                    self._state = StreamState.CANCELLED
                    break

                # Wait if paused
                await self._pause_event.wait()

                # Translate chunk
                try:
                    translated = await self.base_translator.translate_text(
                        text=text_chunk.text,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )

                    # Create stream chunk
                    stream_chunk = StreamChunk(
                        chunk_id=f"chunk_{idx}",
                        chunk_index=idx,
                        original_text=text_chunk.text,
                        translated_text=translated,
                        confidence=1.0,
                        metadata={'original_chunk_id': text_chunk.id}
                    )

                    # Buffer chunk
                    self._chunks_buffer.append(stream_chunk)
                    self._completed_chunks += 1

                    # Write to file if interval reached
                    if file_handle and len(self._chunks_buffer) >= self.write_interval:
                        await self._flush_buffer(file_handle)

                    # Yield chunk
                    yield stream_chunk

                except Exception as e:
                    self._state = StreamState.FAILED
                    raise Exception(f"Translation failed at chunk {idx}: {e}")

            # Flush remaining buffer
            if file_handle and self._chunks_buffer:
                await self._flush_buffer(file_handle)

            self._state = StreamState.COMPLETED

        finally:
            if file_handle:
                file_handle.close()

    async def translate_streaming(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        output_file: Optional[Path] = None,
        on_chunk_callback: Optional[Callable[[StreamChunk], None]] = None,
        on_progress_callback: Optional[Callable[[StreamProgress], None]] = None,
        chunk_size: int = 1000
    ) -> str:
        """
        Perform streaming translation with callbacks

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            output_file: Optional file to write results to
            on_chunk_callback: Called when each chunk completes
            on_progress_callback: Called with progress updates
            chunk_size: Characters per chunk

        Returns:
            Complete translated text

        Example:
            def on_chunk(chunk):
                print(f"Chunk {chunk.chunk_index} done")

            result = await translator.translate_streaming(
                text=text,
                source_lang="en",
                target_lang="vi",
                on_chunk_callback=on_chunk
            )
        """
        all_chunks = []

        async for chunk in self.stream_translate(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            output_file=output_file,
            chunk_size=chunk_size
        ):
            all_chunks.append(chunk)

            # Call chunk callback
            if on_chunk_callback:
                on_chunk_callback(chunk)

            # Call progress callback
            if on_progress_callback:
                progress = self.get_progress()
                on_progress_callback(progress)

        # Combine all translated chunks
        return " ".join(chunk.translated_text for chunk in all_chunks)

    def _initialize_stream(self, text: str, chunk_size: int):
        """Initialize streaming state"""
        self._state = StreamState.INITIALIZING
        self._chunks_buffer.clear()
        self._total_chunks = 0
        self._completed_chunks = 0
        self._start_time = time.time()
        self._cancel_flag = False
        self._pause_event.set()

    async def _flush_buffer(self, file_handle):
        """Flush buffered chunks to file"""
        for chunk in self._chunks_buffer:
            file_handle.write(chunk.translated_text + "\n")
        file_handle.flush()
        self._chunks_buffer.clear()

    def get_progress(self) -> StreamProgress:
        """
        Get current stream progress

        Returns:
            StreamProgress with current state
        """
        elapsed = time.time() - self._start_time

        # Estimate remaining time
        if self._completed_chunks > 0:
            avg_time_per_chunk = elapsed / self._completed_chunks
            remaining_chunks = self._total_chunks - self._completed_chunks
            estimated_remaining = avg_time_per_chunk * remaining_chunks
        else:
            estimated_remaining = 0.0

        return StreamProgress(
            total_chunks=self._total_chunks,
            completed_chunks=self._completed_chunks,
            current_chunk_index=self._completed_chunks,
            state=self._state,
            elapsed_time_sec=elapsed,
            estimated_remaining_sec=estimated_remaining
        )

    def pause(self):
        """Pause streaming translation"""
        if self._state == StreamState.STREAMING:
            self._state = StreamState.PAUSED
            self._pause_event.clear()

    def resume(self):
        """Resume paused streaming translation"""
        if self._state == StreamState.PAUSED:
            self._state = StreamState.STREAMING
            self._pause_event.set()

    def cancel(self):
        """Cancel streaming translation"""
        self._cancel_flag = True
        self._state = StreamState.CANCELLED
        self._pause_event.set()  # Unpause if paused

    def get_state(self) -> StreamState:
        """Get current stream state"""
        return self._state

    def get_statistics(self) -> dict:
        """
        Get streaming statistics

        Returns:
            Dictionary with performance metrics
        """
        progress = self.get_progress()

        throughput = 0.0
        if progress.elapsed_time_sec > 0:
            throughput = progress.completed_chunks / progress.elapsed_time_sec

        return {
            'state': self._state.value,
            'total_chunks': self._total_chunks,
            'completed_chunks': self._completed_chunks,
            'progress_percentage': progress.progress_percentage,
            'elapsed_time_sec': progress.elapsed_time_sec,
            'estimated_remaining_sec': progress.estimated_remaining_sec,
            'throughput_chunks_per_sec': throughput,
            'buffer_size': len(self._chunks_buffer)
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    print("Streaming Translator - Demo")
    print("=" * 80)

    # Mock translator for demo
    class MockTranslator:
        async def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
            """Mock translation with simulated latency"""
            await asyncio.sleep(0.1)  # Simulate API call
            return f"[TRANSLATED: {text[:50]}...]"

    async def demo_streaming():
        # Sample text
        sample_text = """
        Artificial intelligence (AI) is intelligence demonstrated by machines,
        in contrast to the natural intelligence displayed by humans and animals.
        Leading AI textbooks define the field as the study of "intelligent agents":
        any device that perceives its environment and takes actions that maximize
        its chance of successfully achieving its goals.

        Machine learning is a subset of artificial intelligence that provides
        systems the ability to automatically learn and improve from experience
        without being explicitly programmed. Machine learning focuses on the
        development of computer programs that can access data and use it to
        learn for themselves.
        """ * 10  # Repeat to make it longer

        # Create streaming translator
        base_translator = MockTranslator()
        streaming_translator = StreamingTranslator(
            base_translator=base_translator,
            write_interval=3,
            buffer_size=5
        )

        print(f"Input text length: {len(sample_text)} characters")
        print("\nStarting streaming translation...\n")

        # Define callbacks
        chunk_count = [0]  # Use list to modify in callback

        def on_chunk(chunk: StreamChunk):
            chunk_count[0] += 1
            print(f"  📦 Chunk {chunk.chunk_index + 1}: {len(chunk.translated_text)} chars")

        def on_progress(progress: StreamProgress):
            print(f"  📊 Progress: {progress.progress_percentage:.1f}% "
                  f"({progress.completed_chunks}/{progress.total_chunks} chunks)")

        # Output file
        output_file = Path("/tmp/streaming_demo_output.txt")

        # Perform streaming translation
        start_time = time.time()

        result = await streaming_translator.translate_streaming(
            text=sample_text,
            source_lang="en",
            target_lang="vi",
            output_file=output_file,
            on_chunk_callback=on_chunk,
            chunk_size=500
        )

        elapsed_time = time.time() - start_time

        # Get final statistics
        stats = streaming_translator.get_statistics()

        print("\n" + "=" * 80)
        print("Streaming Complete!")
        print("=" * 80)
        print(f"\nStatistics:")
        print(f"  State: {stats['state']}")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Completed: {stats['completed_chunks']}")
        print(f"  Progress: {stats['progress_percentage']:.1f}%")
        print(f"  Elapsed time: {stats['elapsed_time_sec']:.2f}s")
        print(f"  Throughput: {stats['throughput_chunks_per_sec']:.2f} chunks/sec")
        print(f"\nOutput:")
        print(f"  Result length: {len(result)} characters")
        print(f"  Output file: {output_file}")
        print(f"\n✓ Processed {chunk_count[0]} chunks in {elapsed_time:.2f}s")

    # Run demo
    asyncio.run(demo_streaming())
