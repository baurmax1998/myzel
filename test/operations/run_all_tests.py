#!/usr/bin/env python3
"""Run all operation tests"""
import sys
import subprocess
from pathlib import Path

def run_test(test_file):
    """Run a single test file and return success status"""
    print(f"\n{'='*70}")
    print(f"Running: {test_file.name}")
    print(f"{'='*70}\n")

    result = subprocess.run([sys.executable, str(test_file)], cwd=test_file.parent)
    return result.returncode == 0

def main():
    """Run all operation tests"""
    test_dir = Path(__file__).parent
    test_files = sorted(test_dir.glob("test_*.py"))

    if not test_files:
        print("No test files found!")
        return 1

    print(f"\n{'='*70}")
    print("MYZEL OPERATION TESTS")
    print(f"{'='*70}")
    print(f"Found {len(test_files)} test files\n")

    results = {}
    for test_file in test_files:
        success = run_test(test_file)
        results[test_file.name] = success

    # Print summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")

    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {test_name:40s} {status}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\n{'='*70}")
    print(f"Total: {passed}/{total} tests passed")
    print(f"{'='*70}\n")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
