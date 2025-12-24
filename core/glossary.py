#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GlossaryManager - Quản lý thuật ngữ để đảm bảo consistency
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class GlossaryManager:
    """Quản lý thuật ngữ để đảm bảo consistency"""

    def __init__(self, glossary_dir: Path, glossary_name: Optional[str] = None):
        self.glossary_dir = Path(glossary_dir)
        self.glossary_dir.mkdir(exist_ok=True, parents=True)
        self.terms = {}
        self.regex_cache = {}
        self.domain = 'default'  # Track current domain
        self.description = ""

        # Load default glossary
        default_glossary = self.glossary_dir / "default.json"
        if default_glossary.exists():
            self.load_glossary(default_glossary)

        # Load specific glossary nếu được chỉ định
        if glossary_name:
            glossary_path = self.glossary_dir / f"{glossary_name}.json"
            if glossary_path.exists():
                self.load_glossary(glossary_path)
                self.domain = glossary_name  # Set domain based on loaded glossary

    def load_glossary(self, path: Path):
        """Load glossary từ JSON file"""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.terms.update(data.get("terms", {}))

            # Extract domain and description if available
            if 'domain' in data:
                self.domain = data['domain']
            if 'description' in data:
                self.description = data['description']

            print(f"📚 Loaded {len(data.get('terms', {}))} terms from {path.name}")
            if self.domain != 'default':
                print(f"   Domain: {self.domain}")
        except Exception as e:
            print(f"⚠️ Cannot load glossary {path}: {e}")

    def save_glossary(self, path: Path):
        """Save glossary to JSON file"""
        try:
            data = {
                "version": "1.0",
                "domain": self.domain,
                "description": self.description,
                "terms": self.terms
            }
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"💾 Saved glossary to {path}")
        except Exception as e:
            print(f"⚠️ Cannot save glossary: {e}")

    def add_term(self, en_term: str, vi_term: str):
        """Add or update a term"""
        self.terms[en_term] = vi_term

    def remove_term(self, en_term: str):
        """Remove a term"""
        if en_term in self.terms:
            del self.terms[en_term]

    def build_prompt_section(self) -> str:
        """Tạo prompt section cho glossary"""
        if not self.terms:
            return ""

        lines = ["THUẬT NGỮ BẮT BUỘC:"]
        for en, vi in list(self.terms.items())[:50]:  # Limit to avoid token overflow
            lines.append(f"- {en} → {vi}")
        return "\n".join(lines)

    def validate_translation(self, source: str, translated: str) -> Tuple[float, List[str]]:
        """Kiểm tra consistency của thuật ngữ"""
        score = 1.0
        warnings = []

        for en_term, vi_term in self.terms.items():
            # Case-insensitive search
            if re.search(r'\b' + re.escape(en_term) + r'\b', source, re.IGNORECASE):
                if vi_term.lower() not in translated.lower():
                    warnings.append(f"Missing term: {en_term} → {vi_term}")
                    score -= 0.1

        return max(0.0, score), warnings

    def get_terms(self) -> Dict[str, str]:
        """Get all terms"""
        return self.terms.copy()

    def get_term_count(self) -> int:
        """Get number of terms"""
        return len(self.terms)
