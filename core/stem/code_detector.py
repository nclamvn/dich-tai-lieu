"""
Code Detection Module

Detects and extracts code blocks from text, including:
- Fenced code blocks: ```...```
- Indented code blocks (4+ spaces)
- Inline code: `...`
- Programming language detection
"""

import re
import regex
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class CodeType(Enum):
    """Types of code blocks"""
    FENCED = "fenced"  # ```...```
    INDENTED = "indented"  # 4+ spaces
    INLINE = "inline"  # `...`


@dataclass
class CodeMatch:
    """Represents a detected code block"""
    content: str
    start: int
    end: int
    code_type: CodeType
    language: Optional[str] = None  # For fenced blocks
    indent_level: int = 0  # For indented blocks

    def __repr__(self) -> str:
        type_str = self.code_type.value
        if self.language:
            type_str += f"[{self.language}]"
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"CodeMatch(type={type_str}, pos={self.start}-{self.end}, content='{preview}')"


class CodeDetector:
    """Detects code blocks in text"""

    # Common programming languages for fenced blocks
    KNOWN_LANGUAGES = {
        'python', 'py', 'javascript', 'js', 'typescript', 'ts', 'java',
        'c', 'cpp', 'c++', 'csharp', 'c#', 'go', 'rust', 'ruby', 'rb',
        'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'octave',
        'bash', 'sh', 'shell', 'powershell', 'sql', 'html', 'css',
        'xml', 'json', 'yaml', 'yml', 'markdown', 'md', 'tex', 'latex',
        'dockerfile', 'makefile', 'cmake', 'diff', 'patch'
    }

    def __init__(self):
        """Initialize the code detector"""
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for code detection"""

        # Fenced code blocks: ```lang\n code \n```
        self.fenced_pattern = regex.compile(
            r'```(?P<lang>[a-zA-Z0-9_+-]*)\n(?P<code>.*?)```',
            regex.DOTALL | regex.MULTILINE
        )

        # Alternative fenced blocks with tildes: ~~~lang\n code \n~~~
        self.fenced_tilde_pattern = regex.compile(
            r'~~~(?P<lang>[a-zA-Z0-9_+-]*)\n(?P<code>.*?)~~~',
            regex.DOTALL | regex.MULTILINE
        )

        # Inline code: `code`
        self.inline_pattern = regex.compile(
            r'`([^`\n]+?)`',
            regex.MULTILINE
        )

        # Indented code blocks (4+ spaces or 1+ tab at line start)
        # Must be multiple consecutive lines
        self.indented_pattern = regex.compile(
            r'^(?P<indent>(?:    |\t)+)(?P<code>.+?)$',
            regex.MULTILINE
        )

    def detect_code(self, text: str) -> List[CodeMatch]:
        """
        Detect all types of code blocks in text

        Args:
            text: Input text to scan for code blocks

        Returns:
            List of CodeMatch objects, sorted by position
        """
        matches = []

        # Detect fenced code blocks (highest priority)
        matches.extend(self._detect_fenced_blocks(text))

        # Detect inline code
        matches.extend(self._detect_inline_code(text))

        # Detect indented code blocks
        matches.extend(self._detect_indented_blocks(text))

        # Remove overlapping matches
        matches = self._remove_overlaps(matches)

        # Sort by position
        matches.sort(key=lambda m: m.start)

        return matches

    def _detect_fenced_blocks(self, text: str) -> List[CodeMatch]:
        """Detect fenced code blocks with ``` or ~~~"""
        matches = []

        # Detect ``` blocks
        for match in self.fenced_pattern.finditer(text):
            lang = match.group('lang').strip().lower() if match.group('lang') else None
            code_content = match.group('code')

            # Validate language hint
            if lang and lang not in self.KNOWN_LANGUAGES:
                # Unknown language, but still treat as code
                pass

            matches.append(CodeMatch(
                content=match.group(0),
                start=match.start(),
                end=match.end(),
                code_type=CodeType.FENCED,
                language=lang
            ))

        # Detect ~~~ blocks
        for match in self.fenced_tilde_pattern.finditer(text):
            lang = match.group('lang').strip().lower() if match.group('lang') else None
            code_content = match.group('code')

            matches.append(CodeMatch(
                content=match.group(0),
                start=match.start(),
                end=match.end(),
                code_type=CodeType.FENCED,
                language=lang
            ))

        return matches

    def _detect_inline_code(self, text: str) -> List[CodeMatch]:
        """Detect inline code with `code`"""
        matches = []

        for match in self.inline_pattern.finditer(text):
            # Only include if it looks like code (has special chars or is technical)
            code_content = match.group(1)

            # Heuristic: inline code usually contains:
            # - Special chars: ., _, -, (), [], {}, <>, /
            # - CamelCase or snake_case
            # - Technical keywords
            if self._looks_like_code(code_content):
                matches.append(CodeMatch(
                    content=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    code_type=CodeType.INLINE
                ))

        return matches

    def _detect_indented_blocks(self, text: str) -> List[CodeMatch]:
        """Detect indented code blocks (4+ spaces or tabs)"""
        matches = []

        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if line is indented with 4+ spaces or tab
            if line.startswith('    ') or line.startswith('\t'):
                # Found start of indented block
                block_start = sum(len(l) + 1 for l in lines[:i])
                block_lines = [line]
                indent_level = len(line) - len(line.lstrip())

                # Collect consecutive indented lines
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]

                    # Empty lines are OK within code blocks
                    if not next_line.strip():
                        block_lines.append(next_line)
                        j += 1
                        continue

                    # Check if still indented
                    if next_line.startswith('    ') or next_line.startswith('\t'):
                        block_lines.append(next_line)
                        j += 1
                    else:
                        break

                # Only consider as code block if:
                # 1. Multiple lines (2+)
                # 2. Contains code-like content
                block_content = '\n'.join(block_lines)
                if len(block_lines) >= 2 and self._looks_like_code_block(block_content):
                    block_end = block_start + len(block_content)

                    matches.append(CodeMatch(
                        content=block_content,
                        start=block_start,
                        end=block_end,
                        code_type=CodeType.INDENTED,
                        indent_level=indent_level
                    ))

                i = j
            else:
                i += 1

        return matches

    def _looks_like_code(self, text: str) -> bool:
        """
        Improved heuristic to determine if inline text looks like code

        Uses high symbol density and code-like patterns to identify code
        while avoiding false positives from normal prose.
        """
        # Short strings - need stricter criteria
        if len(text) <= 3:
            return False

        # Very short - only if has typical code chars
        if len(text) <= 5:
            return any(c in '()[]{}._' for c in text)

        # Calculate symbol density
        symbol_chars = '()[]{}.<>_/\\-=+*&|!@#$%^;:'
        symbol_count = sum(1 for c in text if c in symbol_chars)
        symbol_density = symbol_count / len(text)

        # High symbol density (>30%) is strong indicator of code
        if symbol_density > 0.3:
            return True

        # Contains typical code chars (but lower threshold)
        code_chars = set('()[]{}.<>_/\\')
        if sum(1 for c in text if c in code_chars) >= 2:
            return True

        # CamelCase (e.g., myFunction, className)
        if re.search(r'[a-z][A-Z]', text):
            return True

        # snake_case with multiple underscores
        if text.count('_') >= 2:
            return True

        # All caps with underscores (constants like MAX_VALUE)
        if text.isupper() and '_' in text and len(text) > 3:
            return True

        # Contains function call pattern: name(
        if re.search(r'\w+\(', text):
            return True

        # Contains assignment or comparison: =, ==, !=, <=, >=
        if re.search(r'[=!<>]=?', text):
            return True

        # Contains arrow functions: ->, =>
        if '->' in text or '=>' in text:
            return True

        # Contains dot notation: obj.property
        if re.search(r'\w+\.\w+', text):
            return True

        # Contains numbers and letters mixed (like var1, func2)
        if re.search(r'\w*\d+\w*', text) and not text.isdigit():
            return True

        # Avoid common English words that might match above patterns
        common_words = {
            'e.g.', 'i.e.', 'etc.', 'vs.', 'Dr.', 'Mr.', 'Mrs.', 'Ms.',
            'a.m.', 'p.m.', 'U.S.', 'U.K.', 'Ph.D.'
        }
        if text.lower() in common_words:
            return False

        return False

    def _looks_like_code_block(self, text: str) -> bool:
        """Heuristic to determine if block looks like code"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        if not lines:
            return False

        code_indicators = 0

        for line in lines:
            # Contains typical code patterns
            if any(pattern in line for pattern in [
                '(', ')', '{', '}', '[', ']', ';', '=', '==', '!=',
                '->', '=>', '::', '...', '||', '&&', '++', '--'
            ]):
                code_indicators += 1

            # Contains keywords
            if re.search(r'\b(def|class|function|var|let|const|import|from|return|if|else|for|while)\b', line):
                code_indicators += 1

            # Assignment patterns
            if re.search(r'\w+\s*[=:]\s*', line):
                code_indicators += 1

        # If >30% of lines look like code, consider it a code block
        return code_indicators / len(lines) > 0.3

    def _remove_overlaps(self, matches: List[CodeMatch]) -> List[CodeMatch]:
        """Remove overlapping matches, prioritizing fenced > inline > indented"""
        if not matches:
            return []

        # Sort by priority (fenced first), then by start position
        priority = {CodeType.FENCED: 0, CodeType.INLINE: 1, CodeType.INDENTED: 2}
        matches.sort(key=lambda m: (priority[m.code_type], m.start))

        non_overlapping = []
        for match in matches:
            overlaps = False
            for accepted in non_overlapping:
                if (match.start < accepted.end and match.end > accepted.start):
                    overlaps = True
                    break

            if not overlaps:
                non_overlapping.append(match)

        return non_overlapping

    def has_code(self, text: str) -> bool:
        """
        Quick check if text contains any code blocks

        Args:
            text: Text to check

        Returns:
            True if code blocks are detected
        """
        if self.fenced_pattern.search(text):
            return True
        if self.fenced_tilde_pattern.search(text):
            return True
        if self.inline_pattern.search(text):
            return True

        return False

    def count_code_blocks(self, text: str) -> dict:
        """
        Count code blocks by type

        Args:
            text: Text to analyze

        Returns:
            Dictionary with counts per code type
        """
        matches = self.detect_code(text)

        counts = {ctype: 0 for ctype in CodeType}
        for match in matches:
            counts[match.code_type] += 1

        # Count by language for fenced blocks
        language_counts = {}
        for match in matches:
            if match.code_type == CodeType.FENCED and match.language:
                language_counts[match.language] = language_counts.get(match.language, 0) + 1

        return {
            'total': len(matches),
            'by_type': {k.value: v for k, v in counts.items() if v > 0},
            'by_language': language_counts if language_counts else None
        }
