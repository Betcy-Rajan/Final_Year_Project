"""
Test runner script for Government Scheme Agent unit tests
"""
import sys
import subprocess

def run_tests():
    """Run pytest with appropriate options"""
    print("=" * 80)
    print("Running Government Scheme Agent Unit Tests")
    print("=" * 80)
    print()
    
    # Run pytest with verbose output
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "test_scheme_agent.py",
            "-v",  # Verbose
            "--tb=short",  # Short traceback format
            "--color=yes",  # Colored output
            "-x",  # Stop on first failure (optional, remove if you want to see all failures)
        ],
        cwd="."
    )
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)




