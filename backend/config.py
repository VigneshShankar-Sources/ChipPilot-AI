"""
ChipPilot AI - Backend Configuration
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "chippilot.db")
WORKSPACE_DIR = os.path.join(BASE_DIR, "eda_workspace")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
