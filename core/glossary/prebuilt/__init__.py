"""
Pre-built Glossaries
Ready-to-use glossaries for common domains.

Available glossaries:
- medical_vi.json: Medical terms EN-VI
- legal_vi.json: Legal terms EN-VI
- tech_vi.json: Technology terms EN-VI
- finance_vi.json: Finance terms EN-VI
- academic_vi.json: Academic terms EN-VI
"""

from pathlib import Path

PREBUILT_DIR = Path(__file__).parent

__all__ = ["PREBUILT_DIR"]
