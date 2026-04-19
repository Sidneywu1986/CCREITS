"""
PDF Parser - PDF text extraction and chunking
"""
import hashlib
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF text extraction and chunking for announcement content"""

    def __init__(self, chunk_min_chars: int = 500, chunk_max_chars: int = 1500, target_chunk_chars: int = 600):
        self.chunk_min_chars = chunk_min_chars
        self.chunk_max_chars = chunk_max_chars
        self.target_chunk_chars = target_chunk_chars

    def parse_and_chunk(self, pdf_path: str) -> List[Tuple[int, str, int]]:
        """
        Parse PDF and split into chunks
        Returns: [(chunk_index, content_text, char_count), ...]
        """
        chunks = []
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    text = self._clean_text(text)
                    full_text += text + "\n"

            # Split by paragraphs
            paragraphs = self._split_into_paragraphs(full_text)
            chunks = self._merge_paragraphs(paragraphs)

        except Exception as e:
            logger.error(f"PDF parsing failed for {pdf_path}: {e}")
            raise

        return chunks

    def _clean_text(self, text: str) -> str:
        """Remove headers, footers, extra whitespace, and special characters"""
        # Remove common header/footer patterns
        text = re.sub(r'第\d+页', '', text)
        text = re.sub(r'Page \d+', '', text)
        text = re.sub(r'共\d+页', '', text)
        # Remove extra blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Keep Chinese, English, numbers, common punctuation
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。、！？；：""''（）【】《》·]', '', text)
        return text.strip()

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs by blank lines"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]

    def _merge_paragraphs(self, paragraphs: List[str]) -> List[Tuple[int, str, int]]:
        """Merge paragraphs into chunks of target size"""
        chunks = []
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            # If single paragraph exceeds max, split it first
            if len(para) > self.chunk_max_chars:
                sub_chunks = self._split_long_paragraph(para)
                for sub in sub_chunks:
                    if current_chunk.strip():
                        chunks.append((chunk_index, current_chunk.strip(), len(current_chunk)))
                        chunk_index += 1
                    current_chunk = sub + "\n"
            elif len(current_chunk) + len(para) < self.target_chunk_chars:
                current_chunk += para + "\n"
            else:
                if current_chunk.strip():
                    chunks.append((chunk_index, current_chunk.strip(), len(current_chunk)))
                    chunk_index += 1
                current_chunk = para + "\n"

        if current_chunk.strip():
            chunks.append((chunk_index, current_chunk.strip(), len(current_chunk)))

        return chunks

    def _split_long_paragraph(self, text: str) -> List[str]:
        """Split long paragraph by sentences"""
        # Split by Chinese sentence endings
        sentences = re.split(r'([。！？])', text)
        merged = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                merged.append(sentences[i] + sentences[i + 1])
            else:
                merged.append(sentences[i])

        # Merge into target size chunks
        result = []
        current = ""
        for s in merged:
            if len(current) + len(s) < self.target_chunk_chars:
                current += s
            else:
                if current:
                    result.append(current)
                current = s
        if current:
            result.append(current)

        return result


def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash for content deduplication"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
