import re
import io
from typing import Optional

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class DocumentParser:
    """
    Parses PDF or plain text documents and splits them into logical sections.
    Uses heading detection heuristics: numbered clauses, ALL CAPS headings, etc.
    """

    HEADING_PATTERNS = [
        # Numbered sections: "1.", "1.1", "Section 3", "Article IV"
        re.compile(r"^(?:section|article|clause|part)\s+[\dIVXivx]+[.\s]", re.IGNORECASE),
        re.compile(r"^\d+(\.\d+)*\s+[A-Z]"),
        # ALL CAPS lines (likely headings if < 80 chars)
        re.compile(r"^[A-Z][A-Z\s\-]{5,79}$"),
        # Title Case short lines
        re.compile(r"^([A-Z][a-z]+\s+){2,6}$"),
    ]

    def parse_pdf(self, content: bytes) -> list[dict]:
        """Extract text from PDF bytes and split into sections."""
        if not HAS_PYPDF:
            raise ImportError("pypdf is not installed. Run: pip install pypdf")

        reader = pypdf.PdfReader(io.BytesIO(content))
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return self._split_sections(full_text)

    def parse_text(self, text: str) -> list[dict]:
        """Split plain text into sections."""
        return self._split_sections(text)

    def _split_sections(self, text: str) -> list[dict]:
        """
        Split document text into sections based on heading detection.
        Falls back to fixed-size chunking if no structure is detected.
        """
        lines = text.split("\n")
        sections = []
        current_title = "Preamble"
        current_lines = []
        section_idx = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_lines.append("")
                continue

            if self._is_heading(stripped):
                # Save the previous section
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append(self._make_section(section_idx, current_title, body))
                    section_idx += 1
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(stripped)

        # Don't forget the last section
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(self._make_section(section_idx, current_title, body))

        # If we couldn't detect any structure, chunk by ~500 words
        if len(sections) <= 1:
            sections = self._chunk_by_words(text, chunk_size=500)

        return sections

    def _is_heading(self, line: str) -> bool:
        if len(line) > 120:
            return False
        for pattern in self.HEADING_PATTERNS:
            if pattern.match(line):
                return True
        return False

    def _make_section(self, idx: int, title: str, text: str) -> dict:
        return {
            "id": f"sec_{idx:03d}",
            "title": title[:100],
            "text": text,
        }

    def _chunk_by_words(self, text: str, chunk_size: int = 500) -> list[dict]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(self._make_section(
                len(chunks),
                f"Section {len(chunks) + 1}",
                chunk
            ))
        return chunks
