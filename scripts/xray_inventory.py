#!/usr/bin/env python3
"""
X-RAY INVENTORY SCRIPT

Creates comprehensive inventory of the entire codebase.
Output: Detailed report for restructuring decision.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import json
import ast
import re

PROJECT_ROOT = Path(__file__).parent.parent

# Categories for classification
CATEGORIES = {
    "KEEP_AS_IS": [],      # Working well, Claude can't do better
    "TRANSFORM": [],        # Useful but needs restructuring
    "CLAUDE_REPLACE": [],   # Claude does this natively better
    "REMOVE": [],           # Redundant or obsolete
    "INFRASTRUCTURE": [],   # Supporting code (keep)
}


def count_lines(file_path: Path) -> dict:
    """Count lines in a file"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')

        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        in_multiline = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#') or stripped.startswith('//'):
                comment_lines += 1
            elif '"""' in stripped or "'''" in stripped:
                comment_lines += 1
                in_multiline = not in_multiline
            elif in_multiline:
                comment_lines += 1
            else:
                code_lines += 1

        return {
            "total": len(lines),
            "code": code_lines,
            "comments": comment_lines,
            "blank": blank_lines,
        }
    except:
        return {"total": 0, "code": 0, "comments": 0, "blank": 0}


def analyze_python_file(file_path: Path) -> dict:
    """Analyze a Python file for classes, functions, imports"""
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):
                    functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return {
            "classes": classes,
            "functions": functions[:20],  # Limit
            "imports": list(set(imports))[:20],
        }
    except:
        return {"classes": [], "functions": [], "imports": []}


def get_file_purpose(file_path: Path, content: str) -> str:
    """Extract purpose from docstring or filename"""
    # Try to get docstring
    match = re.search(r'^"""(.*?)"""', content, re.DOTALL)
    if match:
        docstring = match.group(1).strip()
        first_line = docstring.split('\n')[0]
        return first_line[:100]

    # Fallback to filename-based guess
    name = file_path.stem
    purposes = {
        "batch_processor": "Batch processing orchestrator",
        "translator": "Translation engine wrapper",
        "chunker": "Text chunking utilities",
        "adn": "Content DNA extraction",
        "renderer": "Document rendering",
        "exporter": "Export to various formats",
        "cache": "Caching layer",
        "validator": "Quality validation",
    }

    for key, purpose in purposes.items():
        if key in name.lower():
            return purpose

    return "Unknown purpose"


def classify_component(file_path: Path, analysis: dict) -> str:
    """
    Classify component into categories.

    ANTHROPIC SENIOR DEV perspective:
    - What can Claude do natively?
    - What requires traditional code?
    """
    name = file_path.stem.lower()
    path_str = str(file_path).lower()

    # INFRASTRUCTURE - Keep as supporting code
    if any(x in path_str for x in ['api/', 'routes/', 'config', 'utils', 'models', '__init__']):
        return "INFRASTRUCTURE"

    # UI - Keep (frontend)
    if 'ui-aps' in path_str or path_str.endswith('.js') or path_str.endswith('.html'):
        return "INFRASTRUCTURE"

    # CLAUDE_REPLACE - Claude does this better natively
    claude_replaceable = [
        'docx_renderer',      # Claude generates perfect DOCX/LaTeX
        'pdf_renderer',       # Claude generates perfect PDF via LaTeX
        'epub_renderer',      # Claude generates EPUB content
        'text_formatter',     # Claude formats text perfectly
        'style_',             # Claude handles styling
        'template_renderer',  # Claude knows templates
        'merger',             # Claude merges content seamlessly
        'polisher',           # Claude polishes text natively
        'quality_enhancer',   # Claude enhances quality
        'formula_',           # Claude understands LaTeX natively
    ]

    for term in claude_replaceable:
        if term in name:
            return "CLAUDE_REPLACE"

    # TRANSFORM - Useful but needs restructuring
    transform_candidates = [
        'chunker',            # Keep but make semantic
        'batch_processor',    # Transform to orchestrator
        'translator',         # Transform to Claude-native
        'adn',                # Keep ADN but simplify extraction
        'editorial',          # Transform to prompt-based
        'layout',             # Transform to Claude-native
        'consistency',        # Claude handles this
        'extractor',          # Simplify extraction
        'agent',              # Transform agents
    ]

    for term in transform_candidates:
        if term in name:
            return "TRANSFORM"

    # KEEP_AS_IS - Traditional code still needed
    keep_as_is = [
        'cache',              # Caching is infrastructure
        'job_queue',          # Job management
        'ocr',                # OCR is external service
        'contracts',          # Data structures useful
        'schema',             # Schemas useful
        'checkpoint',         # Checkpointing useful
        'memory',             # Memory management
    ]

    for term in keep_as_is:
        if term in name:
            return "KEEP_AS_IS"

    # Default
    return "TRANSFORM"


def scan_directory(directory: Path, extensions: set = {'.py', '.js', '.ts', '.jsx', '.html', '.css'}) -> list:
    """Scan directory for source files"""
    files = []

    skip_dirs = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'dist', 'build', '.pytest_cache'}

    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                files.append(Path(root) / filename)

    return files


def generate_inventory():
    """Generate complete inventory"""
    print("="*70)
    print("       X-RAY CODEBASE INVENTORY")
    print("="*70)

    # Scan files
    files = scan_directory(PROJECT_ROOT)
    print(f"\nFound {len(files)} source files")

    # Analyze each file
    inventory = []
    category_stats = defaultdict(lambda: {"count": 0, "lines": 0, "files": []})

    for file_path in files:
        rel_path = file_path.relative_to(PROJECT_ROOT)

        # Count lines
        lines = count_lines(file_path)

        # Analyze structure (Python only)
        if file_path.suffix == '.py':
            analysis = analyze_python_file(file_path)
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            purpose = get_file_purpose(file_path, content)
        else:
            analysis = {"classes": [], "functions": [], "imports": []}
            purpose = "Frontend/Config"

        # Classify
        category = classify_component(file_path, analysis)

        entry = {
            "path": str(rel_path),
            "lines": lines,
            "analysis": analysis,
            "purpose": purpose,
            "category": category,
        }

        inventory.append(entry)
        category_stats[category]["count"] += 1
        category_stats[category]["lines"] += lines["code"]
        category_stats[category]["files"].append(str(rel_path))

    # Sort by category
    inventory.sort(key=lambda x: (x["category"], -x["lines"]["code"]))

    return inventory, dict(category_stats)


def print_inventory_report(inventory: list, stats: dict):
    """Print formatted inventory report"""

    print("\n" + "="*70)
    print("                    CATEGORY SUMMARY")
    print("="*70)

    total_files = 0
    total_lines = 0

    for category in ["INFRASTRUCTURE", "KEEP_AS_IS", "TRANSFORM", "CLAUDE_REPLACE", "REMOVE"]:
        if category in stats:
            s = stats[category]
            print(f"\n{category}:")
            print(f"  Files: {s['count']}")
            print(f"  Lines: {s['lines']:,}")
            total_files += s['count']
            total_lines += s['lines']

    print(f"\n{'─'*70}")
    print(f"TOTAL: {total_files} files, {total_lines:,} lines")

    # Detailed by category
    for category in ["CLAUDE_REPLACE", "TRANSFORM", "KEEP_AS_IS", "INFRASTRUCTURE"]:
        print(f"\n\n{'='*70}")
        print(f"                    {category}")
        print("="*70)

        category_files = [f for f in inventory if f["category"] == category]

        for f in category_files[:30]:  # Limit output
            print(f"\n📄 {f['path']}")
            print(f"   Lines: {f['lines']['code']} code, {f['lines']['comments']} comments")
            print(f"   Purpose: {f['purpose']}")
            if f['analysis']['classes']:
                print(f"   Classes: {', '.join(f['analysis']['classes'][:5])}")
            if f['analysis']['functions']:
                print(f"   Functions: {', '.join(f['analysis']['functions'][:5])}")


def save_inventory(inventory: list, stats: dict, output_file: str):
    """Save inventory to JSON"""
    data = {
        "summary": {k: {"count": v["count"], "lines": v["lines"]} for k, v in stats.items()},
        "files": inventory,
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n📁 Inventory saved to: {output_file}")


def generate_restructure_recommendations(inventory: list, stats: dict):
    """Generate restructuring recommendations"""

    print("\n\n" + "="*70)
    print("            RESTRUCTURING RECOMMENDATIONS")
    print("="*70)

    claude_replace = [f for f in inventory if f["category"] == "CLAUDE_REPLACE"]
    transform = [f for f in inventory if f["category"] == "TRANSFORM"]
    keep = [f for f in inventory if f["category"] == "KEEP_AS_IS"]
    infra = [f for f in inventory if f["category"] == "INFRASTRUCTURE"]

    print("\n🔴 CLAUDE_REPLACE - Let Claude handle natively:")
    print("   These components do things Claude already does better.")
    total_replace = sum(f["lines"]["code"] for f in claude_replace)
    print(f"   Total lines to replace: {total_replace:,}")
    print("\n   Action: Remove code, use Claude prompts instead")
    for f in claude_replace[:15]:
        print(f"   - {f['path']} ({f['lines']['code']} lines)")

    print("\n\n🟡 TRANSFORM - Restructure to orchestration:")
    print("   These components should become context managers.")
    total_transform = sum(f["lines"]["code"] for f in transform)
    print(f"   Total lines to transform: {total_transform:,}")
    print("\n   Action: Simplify to orchestration logic")
    for f in transform[:15]:
        print(f"   - {f['path']} ({f['lines']['code']} lines)")

    print("\n\n🟢 KEEP_AS_IS - Infrastructure that works:")
    total_keep = sum(f["lines"]["code"] for f in keep)
    print(f"   Total lines to keep: {total_keep:,}")
    for f in keep[:10]:
        print(f"   - {f['path']} ({f['lines']['code']} lines)")

    print("\n\n🔵 INFRASTRUCTURE - Supporting code:")
    total_infra = sum(f["lines"]["code"] for f in infra)
    print(f"   Total infrastructure lines: {total_infra:,}")

    # Estimated new architecture
    print("\n\n" + "="*70)
    print("            ESTIMATED NEW ARCHITECTURE")
    print("="*70)

    keep_lines = total_keep
    infra_lines = total_infra

    # Estimate new code sizes
    new_orchestrator = 500
    new_chunker = 150
    new_dna = 100
    new_converter = 50
    new_prompts = 200
    total_new = new_orchestrator + new_chunker + new_dna + new_converter + new_prompts

    print(f"""
    CURRENT:
    ├── Keep as-is:     {keep_lines:,} lines
    ├── Infrastructure: {infra_lines:,} lines
    ├── Transform:      {total_transform:,} lines → ~{total_new:,} lines
    └── Replace:        {total_replace:,} lines → prompts only

    NEW CODE BREAKDOWN:
    ├── Context Orchestrator:  ~{new_orchestrator} lines
    ├── Semantic Chunker:      ~{new_chunker} lines
    ├── Document DNA:          ~{new_dna} lines
    ├── Output Converter:      ~{new_converter} lines
    └── Prompts/Instructions:  ~{new_prompts} lines

    ESTIMATED NEW TOTAL:
    ├── Keep + Infra:   {keep_lines + infra_lines:,} lines
    └── New code:       ~{total_new:,} lines
    ─────────────────────────────────────
    TOTAL:              ~{keep_lines + infra_lines + total_new:,} lines

    REDUCTION:
    Current processable: {total_transform + total_replace:,} lines
    New replacement:     {total_new:,} lines
    Savings:             {total_transform + total_replace - total_new:,} lines
                        ({(1 - total_new/(total_transform + total_replace))*100:.0f}% reduction in core logic)
    """)

    return {
        "total_current": sum(f["lines"]["code"] for f in inventory),
        "keep": keep_lines,
        "infrastructure": infra_lines,
        "transform": total_transform,
        "replace": total_replace,
        "new_estimate": total_new,
    }


if __name__ == "__main__":
    inventory, stats = generate_inventory()
    print_inventory_report(inventory, stats)
    save_inventory(inventory, stats, "/tmp/codebase_inventory.json")
    results = generate_restructure_recommendations(inventory, stats)

    # Final summary
    print("\n" + "="*70)
    print("                    XRAY-R01 COMPLETE")
    print("="*70)
