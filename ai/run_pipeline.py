"""
ai/run_pipeline.py
==================
Entry point for CrimeLens AI data pipeline execution.
Executes the Phase 2 dataset validation, cleaning, feature engineering,
temporal sequences, and CNN hotspot tensor generation.
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.preprocessing.run_pipeline import run_pipeline

if __name__ == "__main__":
    run_pipeline()
