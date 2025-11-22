#!/usr/bin/env python3
"""
Test Syntax and Structure Checker

Validates test files without requiring Frappe installation.
Checks:
- Python syntax correctness
- Test naming conventions
- Import statements
- Docstrings
- Test structure

Usage:
    python check_tests.py
"""

import ast
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class TestStats:
    """Statistics about test files."""

    total_files: int = 0
    total_classes: int = 0
    total_functions: int = 0
    documented_tests: int = 0
    documented_classes: int = 0
    syntax_errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.syntax_errors is None:
            self.syntax_errors = []
        if self.warnings is None:
            self.warnings = []


class TestChecker:
    """Check test files for correctness."""

    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.stats = TestStats()

    def check_all(self) -> bool:
        """Check all test files."""
        print("🔍 Checking Test Suite...\n")

        test_files = list(self.test_dir.glob("test_*.py"))

        if not test_files:
            print(f"❌ No test files found in {self.test_dir}")
            return False

        self.stats.total_files = len(test_files)

        for test_file in test_files:
            self.check_file(test_file)

        self.print_report()

        return len(self.stats.syntax_errors) == 0

    def check_file(self, file_path: Path):
        """Check a single test file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check syntax
            try:
                tree = ast.parse(content, filename=str(file_path))
                self.analyze_ast(tree, file_path)
            except SyntaxError as e:
                self.stats.syntax_errors.append(f"{file_path.name}: Syntax error at line {e.lineno}: {e.msg}")
                return

        except Exception as e:
            self.stats.syntax_errors.append(f"{file_path.name}: Error reading file: {e}")

    def analyze_ast(self, tree: ast.AST, file_path: Path):
        """Analyze AST for test structure."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("Test"):
                    self.stats.total_classes += 1
                    if ast.get_docstring(node):
                        self.stats.documented_classes += 1
                    else:
                        self.stats.warnings.append(f"{file_path.name}: Class {node.name} missing docstring")

            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    self.stats.total_functions += 1
                    if ast.get_docstring(node):
                        self.stats.documented_tests += 1
                    else:
                        self.stats.warnings.append(f"{file_path.name}: Test {node.name} missing docstring")

                    # Check for assertions
                    has_assertion = any(
                        isinstance(n, ast.Assert) for n in ast.walk(node)
                    )
                    if not has_assertion:
                        self.stats.warnings.append(f"{file_path.name}: Test {node.name} has no assertions")

    def print_report(self):
        """Print check report."""
        print("=" * 70)
        print("📊 TEST SUITE CHECK REPORT")
        print("=" * 70)
        print()

        # Summary
        print("📁 Files Checked:")
        print(f"   • Test files: {self.stats.total_files}")
        print(f"   • Test classes: {self.stats.total_classes}")
        print(f"   • Test functions: {self.stats.total_functions}")
        print()

        # Documentation
        doc_percent = (
            (self.stats.documented_tests / self.stats.total_functions * 100)
            if self.stats.total_functions > 0
            else 0
        )
        class_doc_percent = (
            (self.stats.documented_classes / self.stats.total_classes * 100)
            if self.stats.total_classes > 0
            else 0
        )

        print("📝 Documentation:")
        print(f"   • Documented tests: {self.stats.documented_tests}/{self.stats.total_functions} ({doc_percent:.1f}%)")
        print(f"   • Documented classes: {self.stats.documented_classes}/{self.stats.total_classes} ({class_doc_percent:.1f}%)")
        print()

        # Syntax errors
        if self.stats.syntax_errors:
            print("❌ Syntax Errors:")
            for error in self.stats.syntax_errors:
                print(f"   • {error}")
            print()
        else:
            print("✅ No syntax errors found")
            print()

        # Warnings
        if self.stats.warnings:
            print(f"⚠️  Warnings ({len(self.stats.warnings)}):")
            # Show first 10 warnings
            for warning in self.stats.warnings[:10]:
                print(f"   • {warning}")
            if len(self.stats.warnings) > 10:
                print(f"   ... and {len(self.stats.warnings) - 10} more")
            print()

        # Status
        print("=" * 70)
        if self.stats.syntax_errors:
            print("❌ CHECK FAILED")
            print()
            print("Fix syntax errors before running tests.")
        else:
            print("✅ CHECK PASSED")
            print()
            print("All test files have valid Python syntax.")
            print()
            print("To run tests in Frappe environment:")
            print("  1. cd ~/frappe-bench")
            print("  2. bench --site mysite.local run-tests --app consignment_store")
            print()
            print("See TESTING.md for detailed instructions.")
        print("=" * 70)
        print()


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    test_dir = script_dir / "consignment_store" / "tests"

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    checker = TestChecker(test_dir)
    success = checker.check_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
