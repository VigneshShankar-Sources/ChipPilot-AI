"""
Unit Tests - RAG Semantic Retrieval & Multi-Agent Flow
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retrieval_engine import RetrievalEngine
from knowledge_graph.graph_engine import EngineeringKnowledgeGraph
from root_cause.analyzer import RootCauseAnalyzer
from agents.langgraph_workflow import ChipPilotMultiAgentFlow, AgentState

def test_rag_indexing_and_retrieval():
    rag = RetrievalEngine()
    mock_ast = [{
        "file_path": "alu.v",
        "modules": [{
            "name": "alu",
            "file": "alu.v",
            "ports": [{"name": "a"}, {"name": "b"}, {"name": "result"}],
            "always_blocks": [{
                "line": 10,
                "sensitivity": "*",
                "is_sequential": False,
                "code": "case (opcode) 4'b0: result = a + b; endcase"
            }]
        }]
    }]

    mock_lint = [{
        "tool": "Verilator",
        "severity": "WARNING",
        "code": "LATCH",
        "file": "alu.v",
        "line": 10,
        "message": "Inferred latch for result",
        "evidence": "%Warning-LATCH: alu.v:10: Inferred latch"
    }]

    rag.index_project(mock_ast, mock_lint)
    results = rag.retrieve("Why is latch inferred in ALU?", top_k=2)
    assert len(results) > 0
    assert "document" in results[0]
    assert results[0]["similarity"] > 0

def test_multi_agent_workflow():
    ekg = EngineeringKnowledgeGraph()
    rca = RootCauseAnalyzer(ekg)
    rag = RetrievalEngine()
    multi_agent = ChipPilotMultiAgentFlow(rca, rag)

    agent_state = AgentState(
        project_id="test_cpu",
        parsed_ast=[],
        lint_findings=[{"tool": "Verilator", "severity": "WARNING", "code": "LATCH", "file": "alu.v", "line": 10, "message": "Inferred latch", "evidence": "evidence line"}],
        synth_stats={"total_cells": 500},
        timing_data={"worst_slack": -1.5, "timing_paths": []},
        user_query="Explain timing slack"
    )

    processed = multi_agent.execute_workflow(agent_state)
    assert processed.final_response != ""
    assert "ChipPilot AI Grounded Diagnostic Report" in processed.final_response
