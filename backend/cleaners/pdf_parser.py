"""
PDF Parser - PDF text extraction and chunking
"""
import hashlib
from typing import List, Tuple


class PDFParser:
    def __init__(self, chunk_min_chars: int = 500, chunk_max_chars: int = 1500, target_chunk_chars: int = 600):
        self.chunk_min_chars = chunk_min_chars
        self.chunk_max_chars = chunk_max_chars
        self.target_chunk_chars = target_chunk_chars


def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()