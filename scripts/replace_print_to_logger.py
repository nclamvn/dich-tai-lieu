#!/usr/bin/env python3
"""
Script to replace print() statements with logger calls.
Safe, reversible, and comprehensive.
"""
import re
from pathlib import Path
from typing import Tuple, List

def replace_prints_in_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    Replace print() statements with appropriate logger calls.

    Returns:
        Tuple of (replacement_count, list of changes made)
    """
    content = file_path.read_text(encoding='utf-8')
    original = content
    changes = []

    # Skip if already converted to new logger
    if 'from config.logging_config import' in content:
        return 0, ["Already converted - skipping"]

    # Step 1: Update logger import
    old_import_pattern = r'import logging\n\n# Initialize logger\nlogger = logging\.getLogger\(__name__\)'
    new_import = 'from config.logging_config import get_logger\n\nlogger = get_logger(__name__)'

    if re.search(old_import_pattern, content):
        content = re.sub(old_import_pattern, new_import, content)
        changes.append("Updated logger import")
    elif 'import logging' in content and 'logger = logging.getLogger' in content:
        # Alternative pattern
        content = re.sub(r'import logging', 'from config.logging_config import get_logger', content)
        content = re.sub(r'logger = logging\.getLogger\(__name__\)', 'logger = get_logger(__name__)', content)
        changes.append("Updated logger import (alt pattern)")
    else:
        # No existing logger - add import after other imports
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i

        import_line = "\nfrom config.logging_config import get_logger\nlogger = get_logger(__name__)\n"
        lines.insert(last_import_idx + 1, import_line)
        content = '\n'.join(lines)
        changes.append("Added new logger import")

    # Step 2: Replace print() patterns
    count = 0

    # Pattern categories with their replacements
    patterns = [
        # FORENSIC/Debug prints (to stderr) → logger.debug
        (r'print\(f"🔧 FORENSIC:([^"]+)"[^)]*\)', r'logger.debug(f"FORENSIC:\1")'),
        (r'print\(f"🔧([^"]+)"[^)]*\)', r'logger.debug(f"\1")'),
        (r'print\(f"🔍 FORENSIC:([^"]+)"[^)]*\)', r'logger.debug(f"FORENSIC:\1")'),

        # Error patterns → logger.error
        (r'print\(f"❌([^"]+)"\)', r'logger.error(f"\1")'),
        (r'print\(f"   ❌([^"]+)"\)', r'logger.error(f"\1")'),
        (r'print\("❌([^"]+)"\)', r'logger.error("\1")'),

        # Warning patterns → logger.warning
        (r'print\(f"⚠️([^"]+)"\)', r'logger.warning(f"\1")'),
        (r'print\(f"   ⚠️([^"]+)"\)', r'logger.warning(f"\1")'),
        (r'print\("⚠️([^"]+)"\)', r'logger.warning("\1")'),

        # Success patterns → logger.info
        (r'print\(f"✅([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"✓([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"   ✓([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\("✅([^"]+)"\)', r'logger.info("\1")'),
        (r'print\("✓([^"]+)"\)', r'logger.info("\1")'),

        # Progress/status patterns → logger.info
        (r'print\(f"🚀([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"📦([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"📄([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"📚([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"📕([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"💾([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"🗑️([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"🔄([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"🔬([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"🌊([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"👁️([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"⏱️([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"⏰([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"📋([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"✨([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"🎨([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"🔗([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\(f"   •([^"]+)"\)', r'logger.info(f"•\1")'),

        # Stop/cancel patterns → logger.info
        (r'print\(f"🛑([^"]+)"\)', r'logger.info(f"\1")'),
        (r'print\("🛑([^"]+)"\)', r'logger.info("\1")'),

        # Indented continuation lines → logger.info
        (r'print\(f"   ([^"]+)"\)', r'logger.info(f"  \1")'),

        # Generic f-string prints → logger.info
        (r'print\(f"([^"]+)"\)', r'logger.info(f"\1")'),

        # Generic string prints → logger.info
        (r'print\("([^"]+)"\)', r'logger.info("\1")'),
    ]

    for pattern, replacement in patterns:
        content, n = re.subn(pattern, replacement, content)
        if n > 0:
            count += n
            changes.append(f"Pattern '{pattern[:30]}...': {n} replacements")

    # Step 3: Clean up emoji from logger messages
    emoji_pattern = r'logger\.(info|error|warning|debug)\(f?"[✅✓✗❌⚠️🔄📊🎯🚀📦📄📚📕💾🗑️🔬🌊👁️⏱️⏰📋✨🎨🔗🛑]+\s*'

    # Step 4: Handle special cases - multiline prints with flush=True
    content = re.sub(
        r'print\(f"([^"]+)",\s*flush=True\)',
        r'logger.info(f"\1")',
        content
    )

    # Handle print to stderr
    content = re.sub(
        r'print\(f"([^"]+)",\s*file=sys\.stderr,\s*flush=True\)',
        r'logger.debug(f"\1")',
        content
    )

    if content != original:
        file_path.write_text(content, encoding='utf-8')

    return count, changes


def main():
    """Process batch 1 files."""
    files = [
        'core/batch_processor.py',
        'core/translator.py',
        'core/parallel.py',
        'core/cache/legacy_cache.py',
        'core/ocr/__init__.py',
        'core/ocr/pipeline.py',
        'core/ocr/smart_detector.py',
    ]

    total = 0
    print("=" * 60)
    print("REPLACE PRINT() → LOGGER - BATCH 1")
    print("=" * 60)

    for f in files:
        path = Path(f)
        if path.exists():
            count, changes = replace_prints_in_file(path)
            total += count
            print(f"\n✅ {f}: {count} replacements")
            for change in changes[:5]:  # Show first 5 changes
                print(f"   • {change}")
            if len(changes) > 5:
                print(f"   ... and {len(changes) - 5} more")
        else:
            print(f"\n⚠️  {f}: File not found")

    print("\n" + "=" * 60)
    print(f"📊 TOTAL: {total} print() replaced with logger")
    print("=" * 60)


if __name__ == '__main__':
    main()
