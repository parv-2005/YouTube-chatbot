"""
Test: Chunking Service
======================
Tests transcript chunking with timestamp preservation.
"""

import pytest
from app.services.chunking_service import create_chunks


class TestCreateChunks:
    """Test chunking with various inputs."""

    def test_basic_chunking(self):
        """Test that segments are chunked correctly."""
        segments = [
            {"text": "Hello world " * 50, "start_time": 0.0, "end_time": 5.0},
            {"text": "More text " * 50, "start_time": 5.0, "end_time": 10.0},
        ]

        chunks = create_chunks(segments, "test_video")
        assert len(chunks) > 0

        for chunk in chunks:
            assert "text" in chunk
            assert "video_id" in chunk
            assert "start_time" in chunk
            assert "end_time" in chunk
            assert chunk["video_id"] == "test_video"

    def test_preserves_timestamps(self):
        """Test that timestamps are preserved in chunks."""
        segments = [
            {"text": "Short text", "start_time": 72.5, "end_time": 75.0},
        ]

        chunks = create_chunks(segments, "test_video")
        assert len(chunks) == 1
        assert chunks[0]["start_time"] == 72.5
        assert chunks[0]["end_time"] == 75.0

    def test_empty_segments(self):
        """Test with no segments."""
        chunks = create_chunks([], "test_video")
        assert chunks == []

    def test_chunk_text_not_empty(self):
        """Test that no chunk has empty text."""
        segments = [
            {"text": "Content " * 100, "start_time": 0.0, "end_time": 60.0},
        ]

        chunks = create_chunks(segments, "test_video")
        for chunk in chunks:
            assert len(chunk["text"].strip()) > 0
