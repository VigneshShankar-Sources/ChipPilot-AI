"""
Integration Tests - FastAPI Backend Endpoints
"""

import pytest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app

client = TestClient(app)

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "ChipPilot AI Backend API"

def test_api_analyze_and_ask():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl", "faulty")
    files = [os.path.join(base_dir, f) for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]

    payload = {
        "project_id": "test_demo_soc",
        "top_module": "cpu_top",
        "rtl_files": files
    }

    res = client.post("/api/v1/projects/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert data["status"] == "COMPLETED"

    run_id = data["run_id"]

    # Test PDF Report Download endpoint
    pdf_res = client.get(f"/api/v1/projects/{run_id}/report/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")

def test_api_verify_pdf():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl")
    faulty_files = [os.path.join(base_dir, "faulty", f) for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]
    fixed_files = [os.path.join(base_dir, "fixed", f) for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]

    verify_payload = {
        "top_module": "cpu_top",
        "baseline_files": faulty_files,
        "fixed_files": fixed_files
    }

    v_res = client.post("/api/v1/projects/verify/pdf", json=verify_payload)
    assert v_res.status_code == 200
    assert v_res.headers["content-type"] == "application/pdf"
    assert v_res.content.startswith(b"%PDF-")
