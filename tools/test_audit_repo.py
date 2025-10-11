#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the repository audit tool
"""
import sys
import os
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

import audit_repo


def test_get_repo_root():
    """Test that get_repo_root returns a valid path."""
    root = audit_repo.get_repo_root()
    assert root.exists()
    assert (root / "README.md").exists()


def test_check_files():
    """Test that check_files returns expected structure."""
    results = audit_repo.check_files()
    assert len(results) > 0
    
    # Check that results contain tuples
    for file_path, exists in results:
        assert isinstance(file_path, str)
        assert isinstance(exists, bool)


def test_expected_files_structure():
    """Test that EXPECTED_FILES has the right structure."""
    assert "controller_app" in audit_repo.EXPECTED_FILES
    assert "fl_scripts" in audit_repo.EXPECTED_FILES
    assert "root" in audit_repo.EXPECTED_FILES
    
    # Check some key files are listed
    assert "app.py" in audit_repo.EXPECTED_FILES["controller_app"]
    assert "controller/main.py" in audit_repo.EXPECTED_FILES["fl_scripts"]


def test_get_file_template():
    """Test that file templates are available."""
    # Test a few key templates
    vmidi_template = audit_repo.get_file_template("controller_app/midi/vmidi.py")
    assert "VirtualMIDI" in vmidi_template
    assert "def __init__" in vmidi_template
    
    ci_template = audit_repo.get_file_template(".github/workflows/ci.yml")
    assert "name: CI" in ci_template
    assert "audit" in ci_template


def test_all_files_present():
    """Test that all expected files are present after running with --fix."""
    results = audit_repo.check_files()
    missing_files = [path for path, exists in results if not exists]
    
    if missing_files:
        print(f"Missing files: {missing_files}")
    
    # After running audit_repo.py --fix, all files should be present
    assert len(missing_files) == 0, f"Some files are still missing: {missing_files}"


if __name__ == "__main__":
    # Run tests
    print("Testing audit_repo.py...")
    test_get_repo_root()
    print("✅ test_get_repo_root passed")
    
    test_check_files()
    print("✅ test_check_files passed")
    
    test_expected_files_structure()
    print("✅ test_expected_files_structure passed")
    
    test_get_file_template()
    print("✅ test_get_file_template passed")
    
    test_all_files_present()
    print("✅ test_all_files_present passed")
    
    print("\n✅ All tests passed!")
