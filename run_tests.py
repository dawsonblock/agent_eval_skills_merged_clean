#!/usr/bin/env python3
"""
Test runner for agent-skills-curated with correct PYTHONPATH setup.
Usage: python run_tests.py
"""
import os
import sys
import subprocess

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
CURATED = os.path.join(REPO_ROOT, "agent-skills-curated")
PYTHONPATH = os.environ.get("PYTHONPATH", "")
if CURATED not in PYTHONPATH.split(":"):
    os.environ["PYTHONPATH"] = f"{CURATED}:{PYTHONPATH}" if PYTHONPATH else CURATED

sys.exit(subprocess.call([sys.executable, "-m", "pytest", "agent-skills-curated/tests"]))
