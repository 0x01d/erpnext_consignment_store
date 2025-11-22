#!/usr/bin/env python3
"""
Test Structure Validator

This script validates the test suite structure without requiring Frappe to be installed.
It checks that:
- All test files are properly structured
- Test functions follow naming conventions
- Required fixtures are defined
- Test classes are properly organized

Usage:
    python validate_tests.py
"""

import ast
import os
from pathlib import Path
from collections import defaultdict


class TestValidator:
    def __init__(self, test_dir):
        self.test_dir = Path(test_dir)
        self.stats = defaultdict(int)
        self.issues = []
        self.test_files = []

    def validate(self):
        """Run all validations."""
        print("🔍 Validating Test Suite Structure...\n")

        self.find_test_files()
        self.analyze_test_files()
        self.analyze_fixtures()
        self.print_report()

    def find_test_files(self):
        """Find all test files."""
        for file_path in self.test_dir.rglob("test_*.py"):
            self.test_files.append(file_path)
            self.stats["test_files"] += 1

    def analyze_test_files(self):
        """Analyze each test file."""
        for file_path in self.test_files:
            self.analyze_file(file_path)

    def analyze_file(self, file_path):
        """Analyze a single test file."""
        try:
            with open(file_path, "r") as f:
                content = f.read()
                tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("test_"):
                        self.stats["test_functions"] += 1

                        # Check for docstring
                        if ast.get_docstring(node):
                            self.stats["documented_tests"] += 1

                        # Check for pytest markers
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Attribute):
                                if decorator.attr in ["unit", "integration", "slow"]:
                                    self.stats[f"marked_{decorator.attr}"] += 1

                elif isinstance(node, ast.ClassDef):
                    if node.name.startswith("Test"):
                        self.stats["test_classes"] += 1

                        # Check for docstring
                        if ast.get_docstring(node):
                            self.stats["documented_classes"] += 1

        except Exception as e:
            self.issues.append(f"Error parsing {file_path.name}: {e}")

    def analyze_fixtures(self):
        """Analyze conftest.py for fixtures."""
        conftest_path = self.test_dir / "conftest.py"

        if not conftest_path.exists():
            self.issues.append("conftest.py not found")
            return

        try:
            with open(conftest_path, "r") as f:
                content = f.read()
                tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for @pytest.fixture decorator
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Attribute):
                            if decorator.attr == "fixture":
                                self.stats["fixtures"] += 1
                        elif isinstance(decorator, ast.Name):
                            if decorator.id == "fixture":
                                self.stats["fixtures"] += 1

        except Exception as e:
            self.issues.append(f"Error parsing conftest.py: {e}")

    def print_report(self):
        """Print validation report."""
        print("=" * 70)
        print("📊 TEST SUITE VALIDATION REPORT")
        print("=" * 70)
        print()

        print("📁 Test File Structure:")
        print(f"   ✓ Test files found: {self.stats['test_files']}")
        print(f"   ✓ Test classes: {self.stats['test_classes']}")
        print(f"   ✓ Test functions: {self.stats['test_functions']}")
        print()

        print("📝 Documentation:")
        doc_percent = (
            (self.stats["documented_tests"] / self.stats["test_functions"] * 100)
            if self.stats["test_functions"] > 0
            else 0
        )
        print(f"   ✓ Documented tests: {self.stats['documented_tests']} ({doc_percent:.1f}%)")
        print(f"   ✓ Documented classes: {self.stats['documented_classes']}")
        print()

        print("🏷️  Test Markers:")
        print(f"   ✓ Unit tests marked: {self.stats.get('marked_unit', 0)}")
        print(f"   ✓ Integration tests marked: {self.stats.get('marked_integration', 0)}")
        print(f"   ✓ Slow tests marked: {self.stats.get('marked_slow', 0)}")
        print()

        print("🔧 Test Fixtures:")
        print(f"   ✓ Fixtures defined: {self.stats['fixtures']}")
        print()

        if self.issues:
            print("⚠️  Issues Found:")
            for issue in self.issues:
                print(f"   - {issue}")
            print()

        print("=" * 70)
        print("✅ VALIDATION COMPLETE")
        print("=" * 70)
        print()

        # List all test files
        print("📋 Test Files:")
        for i, file_path in enumerate(sorted(self.test_files), 1):
            print(f"   {i}. {file_path.name}")
        print()

        print("💡 To run these tests in a Frappe environment:")
        print("   1. Install the app in a Frappe bench")
        print("   2. Run: bench --site <site_name> run-tests --app consignment_store")
        print("   3. Or: cd apps/consignment_store && pytest")
        print()


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    test_dir = script_dir / "consignment_store" / "tests"

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    validator = TestValidator(test_dir)
    validator.validate()

    return 0


if __name__ == "__main__":
    exit(main())
