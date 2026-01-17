"""
Smart Title Formatter
=====================

Extracts and formats book/document titles from filenames intelligently.
Handles Vietnamese and international naming conventions.

Examples:
- "nam-cao_chi_pheo.pdf" → "Chí Phèo - Nam Cao"
- "the_little_prince.pdf" → "The Little Prince"
- "Translate document.pdf" → "Document"
- "1984_george_orwell.pdf" → "1984 - George Orwell"

Author: AI Publisher Pro
"""

import re
from typing import Optional, Tuple
from pathlib import Path


# Vietnamese literature mappings (common works)
VIETNAMESE_WORKS = {
    # Nam Cao
    'chi_pheo': ('Chí Phèo', 'Nam Cao'),
    'chi-pheo': ('Chí Phèo', 'Nam Cao'),
    'chipheo': ('Chí Phèo', 'Nam Cao'),
    'doi_thua': ('Đời Thừa', 'Nam Cao'),
    'lang': ('Lão Hạc', 'Nam Cao'),
    'lao_hac': ('Lão Hạc', 'Nam Cao'),
    'song_mon': ('Sống Mòn', 'Nam Cao'),

    # Nguyễn Du
    'truyen_kieu': ('Truyện Kiều', 'Nguyễn Du'),
    'kieu': ('Truyện Kiều', 'Nguyễn Du'),

    # Ngô Tất Tố
    'tat_den': ('Tắt Đèn', 'Ngô Tất Tố'),

    # Vũ Trọng Phụng
    'so_do': ('Số Đỏ', 'Vũ Trọng Phụng'),
    'gion_toc': ('Giông Tố', 'Vũ Trọng Phụng'),

    # Khái Hưng
    'nua_chung_xuan': ('Nửa Chừng Xuân', 'Khái Hưng'),
    'hon_buom_mo_tien': ('Hồn Bướm Mơ Tiên', 'Khái Hưng'),

    # Thạch Lam
    'gio_lanh_dau_mua': ('Gió Lạnh Đầu Mùa', 'Thạch Lam'),

    # Modern
    'noi_buon_chien_tranh': ('Nỗi Buồn Chiến Tranh', 'Bảo Ninh'),
}

# Author name mappings
AUTHOR_NAMES = {
    'nam_cao': 'Nam Cao',
    'nam-cao': 'Nam Cao',
    'namcao': 'Nam Cao',
    'nguyen_du': 'Nguyễn Du',
    'ngo_tat_to': 'Ngô Tất Tố',
    'vu_trong_phung': 'Vũ Trọng Phụng',
    'khai_hung': 'Khái Hưng',
    'thach_lam': 'Thạch Lam',
    'bao_ninh': 'Bảo Ninh',
    'george_orwell': 'George Orwell',
    'antoine_saint_exupery': 'Antoine de Saint-Exupéry',
    'saint_exupery': 'Antoine de Saint-Exupéry',
}


def extract_title_from_filename(filename: str) -> Tuple[str, Optional[str]]:
    """
    Extract book title and author from filename.

    Args:
        filename: File name (with or without path, with or without extension)

    Returns:
        Tuple of (title, author) - author may be None if not detected

    Examples:
        >>> extract_title_from_filename("nam-cao_chi_pheo.pdf")
        ('Chí Phèo', 'Nam Cao')
        >>> extract_title_from_filename("the_little_prince.pdf")
        ('The Little Prince', None)
    """
    # Get base name without extension
    name = Path(filename).stem

    # Remove common prefixes
    name = re.sub(r'^(Translate|translate|TRANSLATE)\s*', '', name)
    name = re.sub(r'^(translated|output|input|temp)[-_]?', '', name, flags=re.IGNORECASE)

    # Normalize separators
    name_lower = name.lower().replace('-', '_').replace(' ', '_')

    # Check Vietnamese works database first
    for pattern, (title, author) in VIETNAMESE_WORKS.items():
        if pattern in name_lower:
            return (title, author)

    # Try to detect author_title or title_author pattern
    parts = re.split(r'[_-]', name)

    if len(parts) >= 2:
        # Check if first part is author
        first_part_normalized = '_'.join(parts[:2]).lower()
        if first_part_normalized in AUTHOR_NAMES:
            author = AUTHOR_NAMES[first_part_normalized]
            title_parts = parts[2:]
            if title_parts:
                title = _format_title_words(title_parts)
                return (title, author)

        # Check if last parts are author
        last_part_normalized = '_'.join(parts[-2:]).lower()
        if last_part_normalized in AUTHOR_NAMES:
            author = AUTHOR_NAMES[last_part_normalized]
            title_parts = parts[:-2]
            if title_parts:
                title = _format_title_words(title_parts)
                return (title, author)

        # Single author name
        first_lower = parts[0].lower()
        if first_lower in AUTHOR_NAMES:
            author = AUTHOR_NAMES[first_lower]
            title = _format_title_words(parts[1:])
            return (title, author)

    # No author detected, just format the title
    title = _format_title_words(parts)
    return (title, None)


def _format_title_words(parts: list) -> str:
    """Format title parts into proper title case."""
    if not parts:
        return "Document"

    # Join and clean
    words = []
    for part in parts:
        # Handle camelCase
        part = re.sub(r'([a-z])([A-Z])', r'\1 \2', part)
        words.extend(part.split())

    # Title case with exceptions
    small_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor',
                   'on', 'at', 'to', 'from', 'by', 'of', 'in', 'with'}

    formatted = []
    for i, word in enumerate(words):
        word_lower = word.lower()
        if i == 0 or word_lower not in small_words:
            formatted.append(word.capitalize())
        else:
            formatted.append(word_lower)

    return ' '.join(formatted)


def format_document_title(
    filename: str,
    include_author: bool = True,
    separator: str = " - "
) -> str:
    """
    Format a complete document title from filename.

    Args:
        filename: Source filename
        include_author: Whether to include author in title
        separator: Separator between title and author

    Returns:
        Formatted title string

    Examples:
        >>> format_document_title("nam-cao_chi_pheo.pdf")
        'Chí Phèo - Nam Cao'
        >>> format_document_title("nam-cao_chi_pheo.pdf", include_author=False)
        'Chí Phèo'
    """
    title, author = extract_title_from_filename(filename)

    if include_author and author:
        return f"{title}{separator}{author}"
    return title


def clean_header_text(text: str) -> str:
    """
    Clean header text from artifacts like "Translate *.pdf".
    Also tries to extract a proper title if input looks like a filename.

    Args:
        text: Raw header text (may be filename or title)

    Returns:
        Cleaned, properly formatted header text
    """
    if not text:
        return "Document"

    original = text.strip()

    # If text looks like "Translate filename.pdf", extract and format the filename
    translate_match = re.match(r'^Translate\s+([\w\-_\.]+\.pdf)\s*$', original, flags=re.IGNORECASE)
    if translate_match:
        filename = translate_match.group(1)
        title, author = extract_title_from_filename(filename)
        if author:
            return f"{title} • {author}"
        return title

    # If text looks like a filename (contains .pdf or .docx), extract title
    if re.search(r'\.(pdf|docx?)$', original, flags=re.IGNORECASE):
        title, author = extract_title_from_filename(original)
        if author:
            return f"{title} • {author}"
        return title

    # Remove common prefixes
    text = re.sub(r'^(Translate|translate|TRANSLATE)\s+', '', original)

    # Remove file extensions if present
    text = re.sub(r'\.(pdf|docx?)\s*$', '', text, flags=re.IGNORECASE)

    # Only replace underscores with spaces (keep dashes for "Title - Author" format)
    text = text.replace('_', ' ')

    # Clean excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Title case if all lowercase
    if text.islower():
        text = text.title()

    return text if text else "Document"


def format_running_header(
    title: str,
    author: Optional[str] = None,
    max_length: int = 50
) -> str:
    """
    Format title for running header (page header).

    Running headers should be short and elegant.

    Args:
        title: Book title
        author: Optional author name
        max_length: Maximum characters

    Returns:
        Formatted running header
    """
    if author:
        # Format: "Title • Author" or just "Title" if too long
        full = f"{title} • {author}"
        if len(full) <= max_length:
            return full

    # Just title, possibly truncated
    if len(title) <= max_length:
        return title

    # Truncate with ellipsis
    return title[:max_length-3] + "..."


# Convenience functions for common use cases
def smart_title(filename: str) -> str:
    """Get smart formatted title from filename."""
    return format_document_title(filename, include_author=True)


def smart_title_only(filename: str) -> str:
    """Get just the title without author."""
    title, _ = extract_title_from_filename(filename)
    return title


def smart_author(filename: str) -> Optional[str]:
    """Get author name from filename if detectable."""
    _, author = extract_title_from_filename(filename)
    return author


# Testing
if __name__ == "__main__":
    test_cases = [
        "nam-cao_chi_pheo.pdf",
        "nam_cao_chi_pheo.pdf",
        "chi_pheo.pdf",
        "Translate nam-cao_chi_pheo.pdf",
        "the_little_prince.pdf",
        "1984_george_orwell.pdf",
        "truyen_kieu.pdf",
        "george_orwell_1984.pdf",
        "my_document.pdf",
        "report_2024.pdf",
    ]

    print("Title Formatter Test Results:")
    print("=" * 60)

    for filename in test_cases:
        title, author = extract_title_from_filename(filename)
        formatted = format_document_title(filename)
        print(f"\n{filename}")
        print(f"  → Title: {title}")
        print(f"  → Author: {author or '(not detected)'}")
        print(f"  → Formatted: {formatted}")
