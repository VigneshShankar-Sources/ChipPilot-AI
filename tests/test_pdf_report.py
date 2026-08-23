"""
Unit Tests - PDF Report Generator
Verifies generation of Engineering Audit and Comparative Verification Sign-Off PDF reports.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports.pdf_generator import PDFReportGenerator

def test_generate_audit_report_pdf():
    generator = PDFReportGenerator()
    sample_run_data = {
        "top_module": "cpu_top",
        "timing_data": {
            "worst_slack": -0.84,
            "timing_paths": [
                {
                    "startpoint": "regfile_inst/registers_reg[1][0]/C",
                    "endpoint": "alu_inst/result_reg[31]/D",
                    "slack": -0.84,
                    "data_arrival_time": 10.84,
                    "data_required_time": 10.00,
                    "is_violation": True
                }
            ]
        },
        "synth_data": {
            "statistics": {
                "total_cells": 1250,
                "cells": {"$_AND_": 300, "$_OR_": 200, "$_DLATCH_P_": 1}
            }
        },
        "lint_findings": [
            {
                "tool": "Verilator",
                "severity": "WARNING",
                "code": "LATCH",
                "file": "alu.v",
                "line": 15,
                "message": "Inferred latch for variable result",
                "evidence": "%Warning-LATCH: alu.v:15: Inferred latch"
            }
        ],
        "root_causes": [
            {
                "title": "Combinational Inferred Latch in ALU",
                "confidence_score": 0.95,
                "severity": "CRITICAL",
                "file": "alu.v",
                "line": 15,
                "hypothesis": "Incomplete case branches without default assignment cause transparent latch inference.",
                "evidence": ["Verilator: %Warning-LATCH at alu.v:15", "Yosys synthesized 1 $_DLATCH_P_ cell"]
            }
        ],
        "optimizations": [
            {
                "category": "LATCH_ELIMINATION",
                "target_path": "demo_rtl/faulty/alu.v",
                "action": "ADD_DEFAULT_ASSIGNMENT",
                "description": "Add default case to eliminate latch inference.",
                "expected_gain": "Eliminates transparent latch $_DLATCH_P_",
                "verification": "Re-run Verilator lint and Yosys synthesis"
            }
        ],
        "parsed_ast": [
            {
                "filename": "alu.v",
                "modules": [
                    {
                        "name": "alu",
                        "antipatterns": [
                            {
                                "type": "INCOMPLETE_CASE",
                                "severity": "WARNING",
                                "line": 15,
                                "description": "Case statement missing default branch."
                            }
                        ]
                    }
                ]
            }
        ]
    }

    pdf_bytes = generator.generate_audit_report(sample_run_data)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")

def test_generate_verification_report_pdf():
    generator = PDFReportGenerator()
    sample_v_res = {
        "is_verified": True,
        "baseline": {
            "worst_slack": -0.84,
            "inferred_latches": 1,
            "lint_violations": 3,
            "total_cells": 1250
        },
        "fixed": {
            "worst_slack": 0.42,
            "inferred_latches": 0,
            "lint_violations": 0,
            "total_cells": 1210
        },
        "delta": {
            "slack_improvement_ns": 1.26,
            "latches_eliminated": 1,
            "lint_issues_resolved": 3,
            "cell_count_change": -40
        }
    }

    pdf_bytes = generator.generate_verification_report(sample_v_res, top_module="cpu_top")
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
