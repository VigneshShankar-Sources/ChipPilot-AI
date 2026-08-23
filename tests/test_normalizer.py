"""
Unit Tests - EDA Report Normalizer Layer
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eda.report_normalizer import ReportNormalizer

def test_normalize_verilator_logs():
    normalizer = ReportNormalizer()
    sample_stderr = """
%Warning-LATCH: /path/to/alu.v:15:5: Inferred latch for signal 'result'
%Error-WIDTH: /path/to/cpu_top.v:45:10: Operator ASSIGN expects 16 bits but expression has 8 bits
"""
    findings = normalizer.normalize_verilator(sample_stderr, "")
    assert len(findings) == 2
    assert findings[0]["severity"] == "WARNING"
    assert findings[0]["code"] == "LATCH"
    assert findings[0]["line"] == 15
    assert findings[1]["severity"] == "ERROR"
    assert findings[1]["code"] == "WIDTH"

def test_normalize_opensta_logs():
    normalizer = ReportNormalizer()
    sample_sta = """
Startpoint: alu.a[31]
Endpoint: alu.result[31]
  data arrival time 11.8400
  data required time 9.8000
  slack (VIOLATED) -2.0400
worst slack max = -2.04
"""
    timing_data = normalizer.normalize_opensta(sample_sta)
    assert timing_data["worst_slack"] == -2.04
    assert timing_data["has_violations"] is True
    assert len(timing_data["timing_paths"]) == 1
    assert timing_data["timing_paths"][0]["slack"] == -2.04
