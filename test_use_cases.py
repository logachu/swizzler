#!/usr/bin/env python3
"""
test_use_cases.py - Test server responses for all use cases

This script:
1. Starts the server
2. Makes HTTP requests to all endpoints
3. Saves responses to output_actual
4. Compares with output_expected
5. Reports any differences
"""

import json
import subprocess
import time
import sys
import signal
from pathlib import Path
from typing import Dict, List, Tuple
import requests
from difflib import unified_diff


class UseCase:
    """Defines a use case with its test endpoints."""

    def __init__(self, name: str, endpoints: List[Dict[str, str]]):
        self.name = name
        self.base_path = Path(f"use_cases/{name}")
        self.output_actual = self.base_path / "output_actual"
        self.output_expected = self.base_path / "output_expected"
        self.endpoints = endpoints

    def ensure_directories(self):
        """Create output directories if they don't exist."""
        self.output_actual.mkdir(parents=True, exist_ok=True)
        self.output_expected.mkdir(parents=True, exist_ok=True)


# Define test cases for each use case
USE_CASES = [
    UseCase(
        name="price_estimation",
        endpoints=[
            {
                "section": "home",
                "epi": "EPI123456",
                "file": "section_home_EPI123456.json"
            },
            {
                "section": "home",
                "epi": "EPI789012",
                "file": "section_home_EPI789012.json"
            },
            {
                "section": "home",
                "epi": "EPI345678",
                "file": "section_home_EPI345678.json"
            },
            {
                "section": "procedures/APT001",
                "epi": "EPI123456",
                "file": "section_procedures_EPI123456_APT001.json"
            },
            {
                "section": "procedures/APT002",
                "epi": "EPI123456",
                "file": "section_procedures_EPI123456_APT002.json"
            },
            {
                "section": "procedures/APT001",
                "epi": "EPI789012",
                "file": "section_procedures_EPI789012_APT001.json"
            },
        ]
    ),
    UseCase(
        name="prescriptions",
        endpoints=[
            {
                "section": "active_medications",
                "epi": "EPI123456",
                "file": "section_active_medications_EPI123456.json"
            },
            {
                "section": "active_medications",
                "epi": "EPI789012",
                "file": "section_active_medications_EPI789012.json"
            },
            {
                "section": "active_medications",
                "epi": "EPI345678",
                "file": "section_active_medications_EPI345678.json"
            },
            {
                "section": "medication_history",
                "epi": "EPI123456",
                "file": "section_medication_history_EPI123456.json"
            },
            {
                "section": "medication_history",
                "epi": "EPI789012",
                "file": "section_medication_history_EPI789012.json"
            },
            {
                "section": "medication_history",
                "epi": "EPI345678",
                "file": "section_medication_history_EPI345678.json"
            },
        ]
    )
]


class ServerTester:
    """Manages server lifecycle and API testing."""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.server_process = None

    def start_server(self):
        """Start the FastAPI server."""
        print("Starting server...")

        # Get absolute path to project root
        project_root = Path(__file__).parent.absolute()

        # Start server using system Python
        self.server_process = subprocess.Popen(
            ["python3", f"{project_root}/server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for server to start
        max_retries = 30
        for _ in range(max_retries):
            try:
                response = requests.get(f"{self.server_url}/health", timeout=1)
                if response.status_code == 200:
                    print(f"✓ Server started successfully")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(0.5)

        print("✗ Server failed to start")
        return False

    def stop_server(self):
        """Stop the server process."""
        if self.server_process:
            print("\nStopping server...")
            self.server_process.send_signal(signal.SIGTERM)
            self.server_process.wait(timeout=5)
            print("✓ Server stopped")

    def fetch_response(self, section: str, epi: str) -> Dict:
        """Fetch a response from the server."""
        url = f"{self.server_url}/section/{section}"
        headers = {"X-EPI": epi}

        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def save_response(self, data: Dict, filepath: Path):
        """Save response to file with pretty formatting."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def compare_files(self, expected_file: Path, actual_file: Path) -> Tuple[bool, List[str]]:
        """Compare expected and actual output files."""
        if not expected_file.exists():
            return False, [f"Expected file not found: {expected_file}"]

        if not actual_file.exists():
            return False, [f"Actual file not found: {actual_file}"]

        with open(expected_file) as f:
            expected = json.load(f)

        with open(actual_file) as f:
            actual = json.load(f)

        # Compare as JSON (ignoring whitespace differences)
        if expected == actual:
            return True, []

        # Generate diff
        expected_str = json.dumps(expected, indent=4, sort_keys=True).splitlines()
        actual_str = json.dumps(actual, indent=4, sort_keys=True).splitlines()

        diff = list(unified_diff(
            expected_str,
            actual_str,
            fromfile=str(expected_file),
            tofile=str(actual_file),
            lineterm=''
        ))

        return False, diff

    def test_use_case(self, use_case: UseCase) -> Tuple[int, int]:
        """Test all endpoints for a use case. Returns (passed, failed) counts."""
        print(f"\n{'='*70}")
        print(f"Testing use case: {use_case.name}")
        print(f"{'='*70}")

        use_case.ensure_directories()

        passed = 0
        failed = 0

        for endpoint in use_case.endpoints:
            section = endpoint["section"]
            epi = endpoint["epi"]
            filename = endpoint["file"]

            print(f"\n  Testing: {section} (EPI: {epi})")

            # Fetch response
            response_data = self.fetch_response(section, epi)

            # Save to output_actual
            actual_file = use_case.output_actual / filename
            self.save_response(response_data, actual_file)
            print(f"    ✓ Saved actual response: {actual_file}")

            # Compare with expected
            expected_file = use_case.output_expected / filename
            matches, diff = self.compare_files(expected_file, actual_file)

            if matches:
                print(f"    ✓ Response matches expected")
                passed += 1
            else:
                print(f"    ✗ Response differs from expected")
                if diff:
                    print(f"    Diff (first 20 lines):")
                    for line in diff[:20]:
                        print(f"      {line}")
                    if len(diff) > 20:
                        print(f"      ... ({len(diff) - 20} more lines)")
                failed += 1

        return passed, failed


def main():
    """Main test runner."""
    print("="*70)
    print("Use Case Testing Suite")
    print("="*70)

    tester = ServerTester()

    try:
        # Start server
        if not tester.start_server():
            print("Failed to start server. Exiting.")
            return 1

        time.sleep(2)  # Give server time to fully initialize

        # Test all use cases
        total_passed = 0
        total_failed = 0

        for use_case in USE_CASES:
            passed, failed = tester.test_use_case(use_case)
            total_passed += passed
            total_failed += failed

        # Print summary
        print(f"\n{'='*70}")
        print("Test Summary")
        print(f"{'='*70}")
        print(f"Total tests: {total_passed + total_failed}")
        print(f"✓ Passed: {total_passed}")
        print(f"✗ Failed: {total_failed}")
        print(f"{'='*70}\n")

        return 0 if total_failed == 0 else 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        tester.stop_server()


if __name__ == "__main__":
    sys.exit(main())
