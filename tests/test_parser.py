"""
Unit Tests - RTL Parser & Structural Antipattern Detector
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.rtl_parser import RTLParser

def test_parse_faulty_alu():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl", "faulty")
    alu_file = os.path.join(base_dir, "alu.v")
    
    parser = RTLParser()
    result = parser.parse_file(alu_file)
    
    assert len(result["modules"]) == 1
    mod = result["modules"][0]
    assert mod["name"] == "alu"
    assert len(mod["ports"]) >= 4
    
    # Check that latch hazard is flagged
    antipatterns = mod["antipatterns"]
    assert any(ap["type"] == "INCOMPLETE_CASE_STATEMENT" or ap["type"] == "POTENTIAL_LATCH_INFERRED" for ap in antipatterns)

def test_parse_regfile_reset_detection():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl", "faulty")
    regfile_file = os.path.join(base_dir, "regfile.v")
    
    parser = RTLParser()
    result = parser.parse_file(regfile_file)
    
    mod = result["modules"][0]
    assert mod["name"] == "regfile"
    assert any(ap["type"] == "MISSING_ASYNC_RESET" for ap in mod["antipatterns"])
