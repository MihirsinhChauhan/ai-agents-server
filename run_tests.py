#!/usr/bin/env python3
"""
Test runner script for comprehensive testing of the DebtEase backend.
Provides easy-to-use commands for running different types of tests.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔍 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, cwd=".", capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✅ {description} passed!")
            return True
        else:
            print(f"❌ {description} failed with exit code {result.returncode}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with error: {e}")
        return False


def setup_test_database():
    """Set up test database."""
    print("🚀 Setting up test database...")

    # Run database migrations
    success = run_command([
        "python", "-c", """
import asyncio
from app.databases.migrations.migration_runner import run_migrations
import asyncpg

async def setup():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='debtease_test'
    )
    try:
        await run_migrations(conn)
        print('✅ Database migrations completed')
    finally:
        await conn.close()

asyncio.run(setup())
"""
    ], "Setting up test database")

    return success


def run_unit_tests():
    """Run unit tests."""
    return run_command([
        "pytest", "test/test_models_comprehensive.py",
        "-v",
        "--tb=short",
        "--no-cov"  # Disable coverage for unit tests (they're just model validation)
    ], "Running unit tests")


def run_integration_tests():
    """Run integration tests."""
    return run_command([
        "pytest", "test/",
        "-m", "integration",
        "-v",
        "--tb=short"
    ], "Running integration tests")


def run_api_tests():
    """Run API endpoint tests."""
    return run_command([
        "pytest", "test/",
        "-m", "api",
        "-v",
        "--tb=short"
    ], "Running API tests")


def run_ai_tests():
    """Run AI agent tests."""
    return run_command([
        "pytest", "test/",
        "-m", "ai",
        "-v",
        "--tb=short"
    ], "Running AI agent tests")


def run_e2e_tests():
    """Run end-to-end tests."""
    return run_command([
        "pytest", "test/",
        "-m", "e2e",
        "-v",
        "--tb=short"
    ], "Running end-to-end tests")


def run_performance_tests():
    """Run performance tests."""
    return run_command([
        "pytest", "test/",
        "-m", "performance",
        "-v",
        "--tb=short",
        "--durations=10"
    ], "Running performance tests")


def run_all_tests():
    """Run all tests with coverage."""
    return run_command([
        "pytest", "test/",
        "--cov=app",
        "--cov-report=html:htmlcov",
        "--cov-report=xml",
        "--cov-report=term-missing",
        "--cov-fail-under=80",
        "-v",
        "--tb=short"
    ], "Running all tests with coverage")


def run_linting():
    """Run code linting."""
    success = True

    # Run flake8
    success &= run_command([
        "flake8", "app", "test",
        "--max-line-length=88",
        "--max-complexity=10"
    ], "Running flake8 linting")

    # Run black check
    success &= run_command([
        "black", "--check", "--diff", "app", "test"
    ], "Checking code formatting with black")

    # Run isort check
    success &= run_command([
        "isort", "--check-only", "--diff", "app", "test"
    ], "Checking import sorting with isort")

    return success


def run_type_checking():
    """Run type checking."""
    return run_command([
        "mypy", "app",
        "--ignore-missing-imports",
        "--no-strict-optional"
    ], "Running type checking with mypy")


def run_security_scan():
    """Run security scanning."""
    return run_command([
        "bandit", "-r", "app",
        "-f", "txt"
    ], "Running security scan with bandit")


def main():
    parser = argparse.ArgumentParser(description="DebtEase Backend Test Runner")
    parser.add_argument(
        "command",
        choices=[
            "setup-db", "unit", "integration", "api", "ai", "e2e",
            "performance", "all", "lint", "type-check", "security",
            "full-suite"
        ],
        help="Test command to run"
    )
    parser.add_argument(
        "--no-setup",
        action="store_true",
        help="Skip database setup"
    )

    args = parser.parse_args()

    # Ensure we're in the server directory
    if not Path("app").exists():
        print("❌ Error: Must run from server directory")
        sys.exit(1)

    success = True

    if args.command == "full-suite":
        # Run complete test suite
        print("🚀 Running complete test suite...")

        # Setup
        if not args.no_setup:
            success &= setup_test_database()

        # Code quality
        success &= run_linting()
        success &= run_type_checking()
        success &= run_security_scan()

        # Tests
        success &= run_unit_tests()
        success &= run_integration_tests()
        success &= run_api_tests()
        success &= run_ai_tests()
        success &= run_e2e_tests()
        success &= run_performance_tests()

        # Final comprehensive test
        success &= run_all_tests()

    elif args.command == "setup-db":
        success = setup_test_database()

    elif args.command == "unit":
        success = run_unit_tests()

    elif args.command == "integration":
        success = run_integration_tests()

    elif args.command == "api":
        success = run_api_tests()

    elif args.command == "ai":
        success = run_ai_tests()

    elif args.command == "e2e":
        success = run_e2e_tests()

    elif args.command == "performance":
        success = run_performance_tests()

    elif args.command == "all":
        success = run_all_tests()

    elif args.command == "lint":
        success = run_linting()

    elif args.command == "type-check":
        success = run_type_checking()

    elif args.command == "security":
        success = run_security_scan()

    # Final status
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
