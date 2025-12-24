#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stress Test Runner - AI Publisher Pro
======================================

Easy-to-use stress test runner with configurable levels.

Usage:
    python tests/stress/run_stress_tests.py              # Run all tests (medium level)
    python tests/stress/run_stress_tests.py --level low  # Quick smoke test
    python tests/stress/run_stress_tests.py --level high # Full stress test
    python tests/stress/run_stress_tests.py --api-only   # Only API tests
    python tests/stress/run_stress_tests.py --core-only  # Only core module tests
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure we're in the right directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))


def print_header():
    """Print test header"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AI PUBLISHER PRO - STRESS TEST SUITE                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Testing: Core modules, API endpoints, Japanese OCR, Translation pipeline   ║
║  Purpose: Ensure system stability under load                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


def check_dependencies():
    """Check and report missing dependencies"""
    missing = []

    try:
        import pytest
    except ImportError:
        missing.append("pytest")

    try:
        import httpx
    except ImportError:
        missing.append("httpx")

    try:
        import psutil
    except ImportError:
        missing.append("psutil")

    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False

    print("✅ All dependencies available")
    return True


def run_tests(level: str = "medium", api_only: bool = False, core_only: bool = False):
    """Run stress tests with specified configuration"""

    # Set environment variable for stress level
    os.environ['STRESS_LEVEL'] = level

    # Determine which tests to run
    test_files = []

    if api_only:
        test_files.append("tests/stress/test_api_stress.py")
    elif core_only:
        test_files.append("tests/stress/test_stress_suite.py")
    else:
        test_files = [
            "tests/stress/test_stress_suite.py",
            "tests/stress/test_api_stress.py",
        ]

    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--durations=10",  # Show 10 slowest tests
        "--no-cov",  # Skip coverage for stress tests
    ]

    # Add test files
    for tf in test_files:
        if os.path.exists(tf):
            cmd.append(tf)

    print(f"\n🚀 Running stress tests (level: {level})")
    print(f"   Command: {' '.join(cmd)}\n")

    # Run tests
    start_time = datetime.now()
    result = subprocess.run(cmd)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Report
    print(f"\n{'='*60}")
    print(f"⏱️  Total time: {elapsed:.1f}s")

    if result.returncode == 0:
        print("✅ All stress tests PASSED")
    else:
        print("❌ Some stress tests FAILED")

    return result.returncode


def run_quick_sanity_check():
    """Run a quick sanity check before full stress tests"""
    print("\n🔍 Running quick sanity check...")

    checks = [
        ("Core imports", "from core.smart_extraction import smart_extract"),
        ("OCR imports", "from core.ocr.paddle_client import get_ocr_client_for_language"),
        ("API imports", "import api.main"),
        ("Language imports", "from core.language import COMMON_PAIRS"),
    ]

    all_passed = True

    for name, check_code in checks:
        try:
            exec(check_code)
            print(f"   ✓ {name}")
        except Exception as e:
            print(f"   ✗ {name}: {e}")
            all_passed = False

    if all_passed:
        print("✅ Sanity check passed\n")
    else:
        print("⚠️  Some checks failed, tests may not run correctly\n")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Run AI Publisher Pro stress tests"
    )
    parser.add_argument(
        "--level",
        choices=["low", "medium", "high"],
        default="medium",
        help="Stress test level (default: medium)"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Run only API stress tests"
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Run only core module stress tests"
    )
    parser.add_argument(
        "--skip-sanity",
        action="store_true",
        help="Skip initial sanity check"
    )

    args = parser.parse_args()

    print_header()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Sanity check
    if not args.skip_sanity:
        if not run_quick_sanity_check():
            print("⚠️  Continuing despite sanity check warnings...")

    # Run tests
    exit_code = run_tests(
        level=args.level,
        api_only=args.api_only,
        core_only=args.core_only
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
