#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Chunking Edge Cases - Phase 1.7 C2

Tests STEM-aware chunking with various edge cases:
1. Very long formulas (> max_chars)
2. Adjacent formulas with no text between
3. Formula at exact chunk boundary
4. Mixed short and long protected regions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.chunker import SmartChunker


def test_very_long_formula():
    """Test chunking when formula exceeds max_chars"""
    print("\n" + "="*70)
    print("TEST 1: Very Long Formula (>3000 chars)")
    print("="*70)

    # Create a formula longer than max_chars
    long_formula = "$$" + "x^{" * 800 + "2" + "}" * 800 + "$$"  # ~3200 chars
    text_before = "This is some text before the formula. " * 20  # ~760 chars
    text_after = "This is some text after the formula. " * 20  # ~760 chars

    test_text = text_before + "\n\n" + long_formula + "\n\n" + text_after

    print(f"Text before: {len(text_before)} chars")
    print(f"Formula: {len(long_formula)} chars")
    print(f"Text after: {len(text_after)} chars")
    print(f"Total: {len(test_text)} chars")

    # Chunk with STEM mode
    chunker = SmartChunker(max_chars=3000, context_window=500, stem_mode=True)
    chunks = chunker.create_chunks(test_text)

    print(f"\n✅ Created {len(chunks)} chunks")

    # Verify formula integrity
    full_merged = "\n\n".join([c.text for c in chunks])
    formula_count_orig = test_text.count("$$")
    formula_count_merged = full_merged.count("$$")

    if formula_count_orig == formula_count_merged:
        print(f"✅ Formula integrity preserved ({formula_count_orig//2} formulas)")
    else:
        print(f"❌ Formula integrity BROKEN: {formula_count_orig//2} → {formula_count_merged//2}")
        return False

    # Show chunk sizes
    for i, chunk in enumerate(chunks):
        has_formula = "$$" in chunk.text
        print(f"   Chunk {i+1}: {len(chunk.text)} chars {'[HAS FORMULA]' if has_formula else ''}")
        if len(chunk.text) > 3500:
            print(f"      ⚠️  WARNING: Chunk exceeds max_chars by {len(chunk.text) - 3000} chars")

    return True


def test_adjacent_formulas():
    """Test chunking with adjacent formulas (no text between)"""
    print("\n" + "="*70)
    print("TEST 2: Adjacent Formulas")
    print("="*70)

    formulas = [
        "$$E = mc^2$$",
        "$$F = ma$$",
        "$$a^2 + b^2 = c^2$$",
        "$$\\lambda = \\frac{h}{p}$$",
        "$$\\hat{H}\\psi = E\\psi$$"
    ]

    # Text with adjacent formulas
    test_text = "Introduction paragraph. " * 30 + "\n\n"  # ~720 chars
    test_text += "\n\n".join(formulas)  # Formulas with no prose between
    test_text += "\n\n" + "Conclusion paragraph. " * 30  # ~660 chars

    print(f"Total text: {len(test_text)} chars")
    print(f"Formula blocks: {len(formulas)}")

    chunker = SmartChunker(max_chars=3000, context_window=500, stem_mode=True)
    chunks = chunker.create_chunks(test_text)

    print(f"\n✅ Created {len(chunks)} chunks")

    # Verify all formulas present
    formula_count_orig = test_text.count("$$")
    full_merged = "\n\n".join([c.text for c in chunks])
    formula_count_merged = full_merged.count("$$")

    if formula_count_orig == formula_count_merged:
        print(f"✅ All formulas preserved ({formula_count_orig//2} formulas)")
    else:
        print(f"❌ Formulas LOST: {formula_count_orig//2} → {formula_count_merged//2}")
        return False

    for i, chunk in enumerate(chunks):
        formula_count = chunk.text.count("$$") // 2
        print(f"   Chunk {i+1}: {len(chunk.text)} chars, {formula_count} formulas")

    return True


def test_formula_at_boundary():
    """Test formula at exact chunk boundary"""
    print("\n" + "="*70)
    print("TEST 3: Formula at Chunk Boundary")
    print("="*70)

    # Create text where formula lands exactly at 3000-char boundary
    text_part1 = "A" * 2950  # Pad to near boundary
    formula = "$$x^2 + y^2 = z^2$$"  # ~20 chars
    text_part2 = "B" * 2950

    test_text = text_part1 + "\n\n" + formula + "\n\n" + text_part2

    print(f"Part 1: {len(text_part1)} chars")
    print(f"Formula position: ~{len(text_part1 + '\\n\\n')} chars")
    print(f"Formula: {len(formula)} chars")
    print(f"Total: {len(test_text)} chars")

    chunker = SmartChunker(max_chars=3000, context_window=500, stem_mode=True)
    chunks = chunker.create_chunks(test_text)

    print(f"\n✅ Created {len(chunks)} chunks")

    # Verify formula not split
    formula_found = False
    for i, chunk in enumerate(chunks):
        if formula in chunk.text:
            formula_found = True
            print(f"   ✅ Formula found intact in chunk {i+1}")
        if "$$x^2" in chunk.text and "z^2$$" not in chunk.text:
            print(f"   ❌ Formula SPLIT in chunk {i+1}")
            return False

    if not formula_found:
        print(f"   ❌ Formula NOT FOUND in any chunk")
        return False

    return True


def test_mixed_regions():
    """Test mix of short and long protected regions"""
    print("\n" + "="*70)
    print("TEST 4: Mixed Protected Regions")
    print("="*70)

    # Mix of short inline formulas, display formulas, and code blocks
    test_text = """
The energy-momentum relation in special relativity is given by $E^2 = (pc)^2 + (mc^2)^2$.

For a photon with zero rest mass ($m = 0$), this simplifies to:

$$E = pc$$

Where $E$ is energy, $p$ is momentum, and $c$ is the speed of light.

Here's a Python implementation:

```python
def energy_momentum(p, m, c=3e8):
    '''Calculate energy from momentum and mass'''
    return ((p*c)**2 + (m*c**2)**2)**0.5
```

For ultra-relativistic particles where $pc >> mc^2$, we can approximate:

$$E \\approx pc\\left(1 + \\frac{1}{2}\\left(\\frac{mc^2}{pc}\\right)^2\\right)$$

This shows that high-energy particles behave like photons.
    """.strip()

    # Pad to make multiple chunks
    test_text = ("Introduction. " * 100) + "\n\n" + test_text + "\n\n" + ("Conclusion. " * 100)

    print(f"Total text: {len(test_text)} chars")
    print(f"Inline formulas ($): {test_text.count('$') - test_text.count('$$')*2}")
    print(f"Display formulas ($$): {test_text.count('$$')//2}")
    print(f"Code blocks (```): {test_text.count('```')//2}")

    chunker = SmartChunker(max_chars=3000, context_window=500, stem_mode=True)
    chunks = chunker.create_chunks(test_text)

    print(f"\n✅ Created {len(chunks)} chunks")

    # Verify integrity
    full_merged = "\n\n".join([c.text for c in chunks])

    checks = [
        ("Inline $", test_text.count('$'), full_merged.count('$')),
        ("Display $$", test_text.count('$$'), full_merged.count('$$')),
        ("Code ```", test_text.count('```'), full_merged.count('```')),
    ]

    all_good = True
    for name, orig, merged in checks:
        if orig == merged:
            print(f"   ✅ {name}: {orig} preserved")
        else:
            print(f"   ❌ {name}: {orig} → {merged} (LOST: {orig - merged})")
            all_good = False

    return all_good


def run_all_tests():
    """Run all edge case tests"""
    print("="*70)
    print("PHASE 1.7 - CHUNKING EDGE CASE TESTS")
    print("="*70)

    tests = [
        ("Very Long Formula", test_very_long_formula),
        ("Adjacent Formulas", test_adjacent_formulas),
        ("Formula at Boundary", test_formula_at_boundary),
        ("Mixed Regions", test_mixed_regions),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\n{passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
