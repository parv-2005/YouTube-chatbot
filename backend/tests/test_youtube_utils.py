"""
Test: YouTube URL Utilities
===========================
Tests URL parsing and video ID extraction.
"""

import pytest
from app.utils.youtube_utils import extract_video_id, is_valid_youtube_url


class TestExtractVideoId:
    """Test video ID extraction from various YouTube URL formats."""

    def test_standard_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_no_www(self):
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert extract_video_id("not a youtube url") is None

    def test_empty_string(self):
        assert extract_video_id("") is None

    def test_random_website(self):
        assert extract_video_id("https://google.com") is None


class TestIsValidYoutubeUrl:
    """Test URL validation."""

    def test_valid_url(self):
        assert is_valid_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_invalid_url(self):
        assert not is_valid_youtube_url("https://google.com")
