"""
Unit Tests - Engineering Knowledge Graph & Deterministic RCA
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_graph.graph_engine import EngineeringKnowledgeGraph
from root_cause.analyzer import RootCauseAnalyzer

def test_ekg_and_rca_flow():
    ekg = EngineeringKnowledgeGraph()
    rca = RootCauseAnalyzer(ekg)

    mock_ast = [{
        "file_path": "demo_rtl/faulty/alu.v",
        "modules": [{
            "name": "alu",
            "file": "demo_rtl/faulty/alu.v",
            "ports": [{"name": "a", "direction": "input", "width": 32}],
            "registers": [{"name": "result", "type": "reg", "width": 32}],
            "wires": [],
            "clocks": [],
            "resets": [],
            "instantiations": [],
            "antipatterns": [{
                "type": "POTENTIAL_LATCH_INFERRED",
                "severity": "WARNING",
                "line": 15,
                "file": "demo_rtl/faulty/alu.v",
                "description": "Inferred latch"
            }]
        }]
    }]

    mock_lint = [{
        "tool": "Verilator",
        "severity": "WARNING",
        "code": "LATCH",
        "file": "demo_rtl/faulty/alu.v",
        "line": 15,
        "message": "Inferred latch for result",
        "evidence": "%Warning-LATCH: demo_rtl/faulty/alu.v:15: Inferred latch"
    }]

    mock_synth = {
        "statistics": {"total_cells": 1482, "cells": {"$_DLATCH_P_": 32, "$_AND_": 100}}
    }

    mock_timing = {
        "worst_slack": -1.84,
        "timing_paths": [{
            "startpoint": "alu.a[31]",
            "endpoint": "alu.result[31]",
            "slack": -1.84,
            "is_violation": True
        }]
    }

    ekg.build_graph(mock_ast, mock_lint, mock_synth, mock_timing)
    stats = ekg.get_summary_stats()
    assert stats["total_nodes"] > 0
    assert stats["total_edges"] > 0

    causes = rca.analyze_root_causes(mock_ast, mock_lint, mock_timing, mock_synth)
    assert len(causes) >= 1
    top = causes[0]
    assert top["confidence_score"] > 0.70
    assert len(top["evidence"]) >= 2
