"""
Phase 2.0.2 - Semantic Document Structure Extractor

Extracts semantic structure from linearized text (paragraphs).
Detects: headings, theorems, proofs, equations, references.

CRITICAL: This module ONLY analyzes text structure. It does NOT modify formulas.
LaTeX delimiters are preserved from Phase 1.6.3 sanitization.
"""

import re
from typing import List, Optional, Tuple, Dict
from .semantic_model import DocNode, DocNodeType, DocNodeList


def extract_semantic_structure(paragraphs: List[str]) -> DocNodeList:
    """
    Extract semantic structure from a list of paragraphs.

    Args:
        paragraphs: List of paragraph texts (already translated, polished, sanitized)

    Returns:
        List of DocNode in reading order

    Priority order:
        1. Heading (chapter/section/subsection)
        2. References/Appendix section markers
        3. Theorem-like blocks
        4. Proof blocks
        5. Equation blocks
        6. Default: PARAGRAPH
    """
    nodes = []

    # State tracking for multi-paragraph blocks
    in_proof = False
    proof_paragraphs = []
    proof_title = None
    proof_explicit_label = None  # Phase 2.0.3a: "Theorem 1.1" from "Proof of Theorem 1.1"

    in_theorem = False
    theorem_paragraphs = []
    theorem_type = None
    theorem_title = None

    in_references = False

    # Phase 2.0.3a: Track last theorem-like node for proof anchoring
    current_theorem_like: Optional[DocNode] = None

    for i, para in enumerate(paragraphs):
        para_stripped = para.strip()
        if not para_stripped:
            continue

        # Check if we should end current proof block
        if in_proof:
            # Phase 2.0.3a: Improved proof end detection with lookahead
            # If QED marker found, add this paragraph to proof and end
            if _detect_proof_end(para_stripped):
                proof_paragraphs.append(para_stripped)
                proof_text = " ".join(proof_paragraphs)

                # Build metadata with anchoring
                metadata = {
                    'source_para_start': i - len(proof_paragraphs) + 1,
                    'source_para_end': i
                }
                if proof_explicit_label:
                    metadata['explicit_label'] = proof_explicit_label
                if current_theorem_like:
                    metadata['related_to_type'] = current_theorem_like.node_type.name
                    metadata['related_to_label'] = current_theorem_like.title

                nodes.append(DocNode(
                    node_type=DocNodeType.PROOF,
                    text=proof_text,
                    title=proof_title,
                    metadata=metadata
                ))
                in_proof = False
                proof_paragraphs = []
                proof_title = None
                proof_explicit_label = None
                continue

            # Phase 2.0.3a: Use lookahead to detect if next block is semantic
            elif _is_next_block_semantic(paragraphs, i):
                # End proof before next semantic block (without including current paragraph)
                proof_text = " ".join(proof_paragraphs)

                # Build metadata with anchoring
                metadata = {
                    'source_para_start': i - len(proof_paragraphs),
                    'source_para_end': i - 1
                }
                if proof_explicit_label:
                    metadata['explicit_label'] = proof_explicit_label
                if current_theorem_like:
                    metadata['related_to_type'] = current_theorem_like.node_type.name
                    metadata['related_to_label'] = current_theorem_like.title

                nodes.append(DocNode(
                    node_type=DocNodeType.PROOF,
                    text=proof_text,
                    title=proof_title,
                    metadata=metadata
                ))
                in_proof = False
                proof_paragraphs = []
                proof_title = None
                proof_explicit_label = None
                # Don't continue - let this paragraph be processed below

        # Check if we should end current theorem block
        if in_theorem:
            if _detect_heading(para_stripped) or _detect_theorem_like(para_stripped) or _detect_proof_start(para_stripped) or _detect_references_section(para_stripped):
                # End theorem block
                theorem_text = " ".join(theorem_paragraphs)
                theorem_node = DocNode(
                    node_type=theorem_type,
                    text=theorem_text,
                    title=theorem_title,
                    metadata={'source_para_start': i - len(theorem_paragraphs), 'source_para_end': i - 1}
                )
                nodes.append(theorem_node)

                # Phase 2.0.3a: Track this theorem for proof anchoring
                current_theorem_like = theorem_node

                in_theorem = False
                theorem_paragraphs = []
                theorem_type = None
                theorem_title = None

        # Try detection in priority order

        # 1. Heading (highest priority)
        heading_result = _detect_heading(para_stripped)
        if heading_result:
            node_type, title, level = heading_result
            nodes.append(DocNode(
                node_type=node_type,
                text=para_stripped,
                title=title,
                level=level,
                metadata={'source_para': i}
            ))
            in_references = False  # Reset references mode
            continue

        # 2. References section marker
        if _detect_references_section(para_stripped):
            nodes.append(DocNode(
                node_type=DocNodeType.REFERENCES_SECTION,
                text=para_stripped,
                title="References",
                metadata={'source_para': i}
            ))
            in_references = True
            continue

        # 3. Theorem-like blocks
        theorem_result = _detect_theorem_like(para_stripped)
        if theorem_result:
            node_type, title = theorem_result
            # Start theorem block (may span multiple paragraphs)
            in_theorem = True
            theorem_type = node_type
            theorem_title = title
            theorem_paragraphs = [para_stripped]
            continue

        # 4. Proof blocks
        if _detect_proof_start(para_stripped):
            # Phase 2.0.3a: Extract explicit label if present (e.g., "Proof of Theorem 1.1")
            explicit_label = _extract_proof_target_label(para_stripped)

            # Check if proof starts and ends on same line (has QED marker)
            if _detect_proof_end(para_stripped):
                # Single-line proof
                proof_title = "Proof" if "Proof" in para_stripped[:20] else "Chứng minh"

                # Build metadata with anchoring
                metadata = {'source_para': i}
                if explicit_label:
                    metadata['explicit_label'] = explicit_label
                if current_theorem_like:
                    metadata['related_to_type'] = current_theorem_like.node_type.name
                    metadata['related_to_label'] = current_theorem_like.title

                nodes.append(DocNode(
                    node_type=DocNodeType.PROOF,
                    text=para_stripped,
                    title=proof_title,
                    metadata=metadata
                ))
                continue
            else:
                # Start multi-line proof block
                in_proof = True
                proof_title = "Proof" if "Proof" in para_stripped[:20] else "Chứng minh"
                proof_explicit_label = explicit_label  # Store for later when proof ends
                proof_paragraphs = [para_stripped]
                continue

        # 5. Equation blocks
        if _detect_equation_block(para_stripped):
            nodes.append(DocNode(
                node_type=DocNodeType.EQUATION_BLOCK,
                text=para_stripped,
                metadata={'source_para': i}
            ))
            continue

        # 6. If in proof block, accumulate
        if in_proof:
            proof_paragraphs.append(para_stripped)
            continue

        # 7. If in theorem block, accumulate
        if in_theorem:
            theorem_paragraphs.append(para_stripped)
            continue

        # 8. If in references section, treat as reference entry
        if in_references:
            nodes.append(DocNode(
                node_type=DocNodeType.REFERENCE_ENTRY,
                text=para_stripped,
                metadata={'source_para': i}
            ))
            continue

        # 9. Default: PARAGRAPH
        nodes.append(DocNode(
            node_type=DocNodeType.PARAGRAPH,
            text=para_stripped,
            metadata={'source_para': i}
        ))

    # Handle unclosed blocks at end of document
    if in_proof:
        proof_text = " ".join(proof_paragraphs)

        # Phase 2.0.3a: Add anchoring metadata even for unclosed proofs
        metadata = {}
        if proof_explicit_label:
            metadata['explicit_label'] = proof_explicit_label
        if current_theorem_like:
            metadata['related_to_type'] = current_theorem_like.node_type.name
            metadata['related_to_label'] = current_theorem_like.title

        nodes.append(DocNode(
            node_type=DocNodeType.PROOF,
            text=proof_text,
            title=proof_title,
            metadata=metadata
        ))

    if in_theorem:
        theorem_text = " ".join(theorem_paragraphs)
        theorem_node = DocNode(
            node_type=theorem_type,
            text=theorem_text,
            title=theorem_title
        )
        nodes.append(theorem_node)

        # Phase 2.0.3a: Track this theorem for proof anchoring
        current_theorem_like = theorem_node

    return nodes


def _detect_heading(text: str) -> Optional[Tuple[DocNodeType, str, int]]:
    """
    Detect if text is a heading (chapter/section/subsection).

    Returns:
        (node_type, title, level) if heading detected, else None

    Patterns:
    - CHAPTER: "Chapter 1", "CHAPTER 1", "Chương 1"
    - SECTION: "1. Introduction", "1.1 Background", "Section 1.1"
    - SUBSECTION: "1.1.1 Details"
    """
    # English Chapter patterns
    chapter_patterns = [
        r'^Chapter\s+(\d+|[IVXLCDM]+)\b',
        r'^CHAPTER\s+(\d+|[IVXLCDM]+)\b',
    ]

    for pattern in chapter_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return (DocNodeType.CHAPTER, text, 1)

    # Vietnamese Chapter patterns
    vn_chapter_patterns = [
        r'^Chương\s+(\d+|[IVXLCDM]+)\b',
        r'^CHƯƠNG\s+(\d+|[IVXLCDM]+)\b',
    ]

    for pattern in vn_chapter_patterns:
        match = re.search(pattern, text)
        if match:
            return (DocNodeType.CHAPTER, text, 1)

    # Section patterns (numbered headings)
    # Match: "1. Title", "1.1 Title", "Section 1.1", "Mục 1.1"
    section_patterns = [
        r'^(\d+)\.\s+[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ]',  # "1. Title"
        r'^(\d+\.\d+)\s+[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ]',  # "1.1 Title"
        r'^Section\s+(\d+(\.\d+)*)\b',
        r'^Mục\s+(\d+(\.\d+)*)\b',
    ]

    for pattern in section_patterns:
        match = re.search(pattern, text)
        if match:
            # Determine level based on numbering depth
            number = match.group(1)
            dots = number.count('.')
            if dots == 0:
                level = 2  # Section (1.)
            elif dots == 1:
                level = 3  # Subsection (1.1)
            else:
                level = 3  # Still subsection for deeper levels

            node_type = DocNodeType.SECTION if level == 2 else DocNodeType.SUBSECTION
            return (node_type, text, level)

    # All-caps short lines (likely headings) - but be conservative
    if text.isupper() and len(text.split()) <= 8 and len(text) <= 100:
        # Check if it's not a common false positive
        if not any(x in text.lower() for x in ['proof', 'theorem', 'lemma', 'definition', 'chứng minh', 'định lý']):
            return (DocNodeType.SECTION, text, 2)

    return None


def _detect_theorem_like(text: str) -> Optional[Tuple[DocNodeType, str]]:
    """
    Detect theorem-like blocks.

    Returns:
        (node_type, title) if theorem-like detected, else None

    Patterns:
    - Theorem, Lemma, Proposition, Corollary, Definition, Remark, Example
    - Vietnamese: Định lý, Bổ đề, Mệnh đề, Hệ quả, Định nghĩa, Nhận xét, Ví dụ
    - Extract label: "Theorem 1.1", "Định lý 3.2"
    """
    # English patterns
    en_patterns = [
        (r'^(Theorem)\s+(\d+(\.\d+)*)', DocNodeType.THEOREM),
        (r'^(Lemma)\s+(\d+(\.\d+)*)', DocNodeType.LEMMA),
        (r'^(Proposition)\s+(\d+(\.\d+)*)', DocNodeType.PROPOSITION),
        (r'^(Corollary)\s+(\d+(\.\d+)*)', DocNodeType.COROLLARY),
        (r'^(Definition)\s+(\d+(\.\d+)*)', DocNodeType.DEFINITION),
        (r'^(Remark)\s+(\d+(\.\d+)*)', DocNodeType.REMARK),
        (r'^(Example)\s+(\d+(\.\d+)*)', DocNodeType.REMARK),  # Treat Example as Remark
    ]

    for pattern, node_type in en_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            label = f"{match.group(1)} {match.group(2)}"
            return (node_type, label)

    # Also match without numbers
    en_patterns_no_num = [
        (r'^(Theorem)[\.:]\s', DocNodeType.THEOREM),
        (r'^(Lemma)[\.:]\s', DocNodeType.LEMMA),
        (r'^(Proposition)[\.:]\s', DocNodeType.PROPOSITION),
        (r'^(Corollary)[\.:]\s', DocNodeType.COROLLARY),
        (r'^(Definition)[\.:]\s', DocNodeType.DEFINITION),
        (r'^(Remark)[\.:]\s', DocNodeType.REMARK),
        (r'^(Example)[\.:]\s', DocNodeType.REMARK),
    ]

    for pattern, node_type in en_patterns_no_num:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return (node_type, match.group(1))

    # Vietnamese patterns
    vn_patterns = [
        (r'^(Định lý)\s+(\d+(\.\d+)*)', DocNodeType.THEOREM),
        (r'^(Bổ đề)\s+(\d+(\.\d+)*)', DocNodeType.LEMMA),
        (r'^(Mệnh đề)\s+(\d+(\.\d+)*)', DocNodeType.PROPOSITION),
        (r'^(Hệ quả)\s+(\d+(\.\d+)*)', DocNodeType.COROLLARY),
        (r'^(Định nghĩa)\s+(\d+(\.\d+)*)', DocNodeType.DEFINITION),
        (r'^(Nhận xét)\s+(\d+(\.\d+)*)', DocNodeType.REMARK),
        (r'^(Ví dụ)\s+(\d+(\.\d+)*)', DocNodeType.REMARK),
    ]

    for pattern, node_type in vn_patterns:
        match = re.search(pattern, text)
        if match:
            label = f"{match.group(1)} {match.group(2)}"
            return (node_type, label)

    # Vietnamese without numbers
    vn_patterns_no_num = [
        (r'^(Định lý)[\.:]\s', DocNodeType.THEOREM),
        (r'^(Bổ đề)[\.:]\s', DocNodeType.LEMMA),
        (r'^(Mệnh đề)[\.:]\s', DocNodeType.PROPOSITION),
        (r'^(Hệ quả)[\.:]\s', DocNodeType.COROLLARY),
        (r'^(Định nghĩa)[\.:]\s', DocNodeType.DEFINITION),
        (r'^(Nhận xét)[\.:]\s', DocNodeType.REMARK),
        (r'^(Ví dụ)[\.:]\s', DocNodeType.REMARK),
    ]

    for pattern, node_type in vn_patterns_no_num:
        match = re.search(pattern, text)
        if match:
            return (node_type, match.group(1))

    return None


def _detect_proof_start(text: str) -> bool:
    """
    Detect if text starts a proof block.

    Phase 2.0.3a: Enhanced with comprehensive EN/VI patterns

    English Patterns:
    - "Proof.", "Proof:", "Proof of Theorem 1.1"
    - "Sketch of proof", "Outline of proof"
    - "Sketch.", "Outline."

    Vietnamese Patterns:
    - "Chứng minh.", "Chứng minh:", "Chứng minh Định lý 1.1"
    - "Phác thảo chứng minh.", "Phần chứng minh."
    """
    proof_patterns = [
        # English patterns
        r'^Proof[\.:]\s',                      # "Proof." or "Proof:"
        r'^Proof\s+of\b',                      # "Proof of Theorem..."
        r'^Sketch\s+of\s+(the\s+)?proof',      # "Sketch of proof" / "Sketch of the proof"
        r'^Outline\s+of\s+(the\s+)?proof',     # "Outline of proof" / "Outline of the proof"
        r'^Sketch[\.:]\s',                     # "Sketch." or "Sketch:"
        r'^Outline[\.:]\s',                    # "Outline." or "Outline:"

        # Vietnamese patterns
        r'^Chứng minh[\.:]\s',                 # "Chứng minh." or "Chứng minh:"
        r'^Chứng minh\s+Định lý',              # "Chứng minh Định lý..."
        r'^Chứng minh\s+Bổ đề',                # "Chứng minh Bổ đề..."
        r'^Phác thảo chứng minh[\.:]\s',       # "Phác thảo chứng minh."
        r'^Phần chứng minh[\.:]\s',            # "Phần chứng minh."
    ]

    for pattern in proof_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


def _detect_proof_end(text: str) -> bool:
    """
    Detect if text ends a proof block.

    Phase 2.0.3a: Enhanced with comprehensive EN/VI QED markers

    English QED Markers:
    - Symbols: "∎", "□", "■", "◻", "▪"
    - Text: "QED", "Q.E.D.", "qed", "q.e.d."
    - Phrases: "This completes the proof", "This concludes the proof"

    Vietnamese QED Markers:
    - Phrases: "Hết chứng minh", "Kết thúc chứng minh", "Hoàn thành chứng minh"
    - "Ta có điều phải chứng minh" (idiomatic ending)
    """
    # Normalize text for pattern matching
    text_lower = text.lower().strip()
    text_trimmed = text.rstrip('.,:; \t\n')

    # Check for QED symbols (at end of text)
    qed_symbols = ['∎', '□', '■', '◻', '▪']
    if any(text_trimmed.endswith(symbol) for symbol in qed_symbols):
        return True

    # Check for English text QED markers
    en_qed_patterns = [
        r'\bQED\b',
        r'\bQ\.E\.D\.\b',
        r'\bqed\b',
        r'\bq\.e\.d\.\b',
        r'This completes the proof',
        r'This concludes the proof',
        r'completes? the proof',
        r'concludes? the proof',
        r'ends? the proof',
    ]

    for pattern in en_qed_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Check for Vietnamese QED markers
    vn_qed_patterns = [
        r'Hết chứng minh',
        r'Kết thúc chứng minh',
        r'Hoàn thành chứng minh',
        r'Ta có điều phải chứng minh',
        r'Điều phải chứng minh được hoàn thành',
    ]

    for pattern in vn_qed_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


def _detect_references_section(text: str) -> bool:
    """
    Detect if text is a references section heading.

    Patterns:
    - "References", "Bibliography", "Tài liệu tham khảo", "Phụ lục"
    """
    references_patterns = [
        r'^References\s*$',
        r'^REFERENCES\s*$',
        r'^Bibliography\s*$',
        r'^BIBLIOGRAPHY\s*$',
        r'^Tài liệu tham khảo\s*$',
        r'^TÀI LIỆU THAM KHẢO\s*$',
        r'^Appendix\b',
        r'^APPENDIX\b',
        r'^Phụ lục\b',
        r'^PHỤ LỤC\b',
    ]

    for pattern in references_patterns:
        if re.search(pattern, text):
            return True

    return False


def _detect_equation_block(text: str) -> bool:
    """
    Detect if text is primarily an equation block.

    Checks for:
    - Display math markers: $$...$$, \\[...\\]
    - Standalone equation (high ratio of math symbols to text)

    CRITICAL: This function does NOT modify text, only detects.
    """
    # Check for display math delimiters
    if '$$' in text:
        return True

    if '\\[' in text and '\\]' in text:
        return True

    # Check if paragraph is very short and math-heavy
    if len(text) < 200:
        # Count math vs text characters
        # Simple heuristic: if many special math chars, likely equation
        math_chars = sum(1 for c in text if c in r'\{}[]^_=+-*/<>≤≥≠∈∉⊂⊃∩∪∀∃∞∑∏∫')
        if len(text) > 0 and math_chars / len(text) > 0.2:  # >20% math symbols
            return True

    return False


def _is_next_block_semantic(paragraphs: List[str], current_idx: int) -> bool:
    """
    Check if next paragraph starts a new semantic block (heading/theorem/section).

    Phase 2.0.3a: Used to detect when current proof should end (lookahead detection).

    Args:
        paragraphs: Full list of paragraphs
        current_idx: Index of current paragraph

    Returns:
        True if next paragraph is a semantic block (heading, theorem, references, etc.)

    Usage:
        If in proof and next block is semantic → end proof before processing next block
    """
    # If at end of document, treat as semantic boundary
    if current_idx + 1 >= len(paragraphs):
        return True

    next_para = paragraphs[current_idx + 1].strip()
    if not next_para:
        return False

    # Check if next paragraph is any semantic block type
    if _detect_heading(next_para):
        return True
    if _detect_theorem_like(next_para):
        return True
    if _detect_references_section(next_para):
        return True

    return False


def _extract_proof_target_label(text: str) -> Optional[str]:
    """
    Extract theorem label from proof titles like "Proof of Theorem 1.1".

    Phase 2.0.3a: Used for explicit proof-theorem anchoring.

    Args:
        text: Proof start paragraph (e.g., "Proof of Theorem 4.2. We now show...")

    Returns:
        Extracted label (e.g., "Theorem 4.2") or None if no explicit label

    Examples:
        - "Proof of Theorem 1.1. ..." → "Theorem 1.1"
        - "Chứng minh Định lý 3.2. ..." → "Định lý 3.2"
        - "Proof. We show..." → None
    """
    # English patterns
    en_patterns = [
        r'Proof\s+of\s+(Theorem\s+\d+(?:\.\d+)*)',
        r'Proof\s+of\s+(Lemma\s+\d+(?:\.\d+)*)',
        r'Proof\s+of\s+(Proposition\s+\d+(?:\.\d+)*)',
        r'Proof\s+of\s+(Corollary\s+\d+(?:\.\d+)*)',
        r'Sketch\s+of\s+(Theorem\s+\d+(?:\.\d+)*)',
        r'Sketch\s+of\s+(Lemma\s+\d+(?:\.\d+)*)',
    ]

    for pattern in en_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    # Vietnamese patterns
    vn_patterns = [
        r'Chứng minh\s+(Định lý\s+\d+(?:\.\d+)*)',
        r'Chứng minh\s+(Bổ đề\s+\d+(?:\.\d+)*)',
        r'Chứng minh\s+(Mệnh đề\s+\d+(?:\.\d+)*)',
        r'Chứng minh\s+(Hệ quả\s+\d+(?:\.\d+)*)',
        r'Phác thảo chứng minh\s+(Định lý\s+\d+(?:\.\d+)*)',
    ]

    for pattern in vn_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None


# ==============================================================================
# Phase 3.0: Book-specific detection functions
# ==============================================================================

def _detect_blockquote(text: str) -> bool:
    """
    Detect if text is a blockquote (quoted text block in books).

    Phase 3.0: For commercial book translation.

    Heuristics:
    - Starts with quotation marks (" or ")
    - Is surrounded by quotation marks
    - Has attribution pattern (e.g., "— Author Name")
    - Short paragraph with quote-like characteristics

    Args:
        text: Paragraph text to analyze

    Returns:
        True if appears to be a blockquote, False otherwise

    Examples:
        - '"Success is not final, failure is not fatal..."'
        - '"The only way to do great work is to love what you do." — Steve Jobs'
    """
    s = text.strip()

    # Check for surrounding quote marks
    if (s.startswith('"') and s.endswith('"')) or \
       (s.startswith('"') and s.endswith('"')) or \
       (s.startswith('«') and s.endswith('»')):
        return True

    # Check for attribution pattern (— Author or - Author)
    if re.search(r'[—–-]\s*[A-Z][\w\s]+$', s):
        return True

    # Conservative: don't auto-detect without clear markers
    return False


def _detect_scene_break(text: str) -> bool:
    """
    Detect if text is a scene break marker (visual separator in fiction/books).

    Phase 3.0: For commercial book translation.

    Common patterns:
    - "* * *" (asterisks with spaces)
    - "***" (asterisks without spaces)
    - "---" (dashes)
    - "◆" or "•" (decorative symbols)
    - "# # #" (hashes)

    Args:
        text: Paragraph text to analyze

    Returns:
        True if appears to be a scene break, False otherwise

    Examples:
        - "* * *"
        - "***"
        - "---"
        - "◆"
    """
    s = text.strip()

    # Empty or very short
    if len(s) == 0:
        return False

    # Pattern 1: Asterisks (with or without spaces)
    if re.fullmatch(r'\*+(\s+\*+)*', s):
        return True

    # Pattern 2: Dashes
    if re.fullmatch(r'-{3,}', s):
        return True

    # Pattern 3: Hashes
    if re.fullmatch(r'#+(\s+#+)*', s):
        return True

    # Pattern 4: Single decorative symbol (centered)
    decorative_symbols = ['◆', '•', '●', '❖', '※', '⁂', '☙', '❦']
    if s in decorative_symbols:
        return True

    # Pattern 5: Multiple decorative symbols with spacing
    if all(c in decorative_symbols + [' '] for c in s) and any(c in decorative_symbols for c in s):
        return True

    return False
