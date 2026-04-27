"""
PDF Parser Tests (TDD)
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaners.pdf_parser import PDFParser, calculate_content_hash


def test_pdf_parser_init():
    """Test PDFParser initialization with default parameters"""
    parser = PDFParser()
    assert parser.chunk_min_chars == 500
    assert parser.chunk_max_chars == 1500
    assert parser.target_chunk_chars == 600


def test_pdf_parser_custom_params():
    """Test PDFParser with custom chunk parameters"""
    parser = PDFParser(chunk_min_chars=300, chunk_max_chars=1000, target_chunk_chars=400)
    assert parser.chunk_min_chars == 300
    assert parser.chunk_max_chars == 1000
    assert parser.target_chunk_chars == 400


def test_calculate_content_hash():
    """Test content hash calculation - same content produces same hash"""
    hash1 = calculate_content_hash("test content")
    hash2 = calculate_content_hash("test content")
    assert hash1 == hash2
    hash3 = calculate_content_hash("different content")
    assert hash1 != hash3


def test_calculate_content_hash_deterministic():
    """Test content hash is deterministic"""
    text = "这是测试内容"
    hash_a = calculate_content_hash(text)
    hash_b = calculate_content_hash(text)
    assert hash_a == hash_b
    assert len(hash_a) == 64  # SHA256 produces 64 character hex string