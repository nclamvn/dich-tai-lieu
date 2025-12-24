#!/usr/bin/env python3
import shutil
import subprocess
import os

print("=== Pandoc Detection Test ===")
print(f"PATH: {os.environ.get('PATH', 'NOT SET')}")
print()

# Test 1: shutil.which
pandoc_path = shutil.which("pandoc")
print(f"1. shutil.which('pandoc'): {pandoc_path}")
print(f"   Result: {'FOUND' if pandoc_path else 'NOT FOUND'}")
print()

# Test 2: Direct call
try:
    result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, timeout=5)
    print(f"2. subprocess.run(['pandoc', '--version']):")
    print(f"   Return code: {result.returncode}")
    print(f"   Output: {result.stdout.splitlines()[0] if result.stdout else 'No output'}")
except Exception as e:
    print(f"2. subprocess call failed: {e}")
print()

# Test 3: Check /opt/homebrew/bin/pandoc directly
try:
    result = subprocess.run(["/opt/homebrew/bin/pandoc", "--version"], capture_output=True, text=True, timeout=5)
    print(f"3. Direct call to /opt/homebrew/bin/pandoc:")
    print(f"   Return code: {result.returncode}")
    print(f"   Output: {result.stdout.splitlines()[0] if result.stdout else 'No output'}")
except Exception as e:
    print(f"3. Direct call failed: {e}")
