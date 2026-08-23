"""
ChipPilot AI - Master FastAPI Service
RESTful API for RTL Analysis, EDA Orchestration, EKG Graphing, RCA, and Closed-Loop Verification.
"""

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import os
import sys

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import DATABASE_PATH, WORKSPACE_DIR
from parser.rtl_parser import RTLParser
from eda.orchestrator import EDAOrchestrator
from eda.report_normalizer import ReportNormalizer
from knowledge_graph.graph_engine import EngineeringKnowledgeGraph
from rag.retrieval_engine import RetrievalEngine
from root_cause.analyzer import RootCauseAnalyzer
from agents.langgraph_workflow import ChipPilotMultiAgentFlow, AgentState
from optimization.advisor import OptimizationAdvisor
from optimization.verifier import VerificationSandbox
from database.db_manager import DatabaseManager
from reports.pdf_generator import PDFReportGenerator

app = FastAPI(
    title="ChipPilot AI Backend API",
    description="Intelligent AI-Powered RTL Engineering Assistant API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Singletons
db = DatabaseManager(DATABASE_PATH)
rtl_parser = RTLParser()
eda_orchestrator = EDAOrchestrator(WORKSPACE_DIR)
normalizer = ReportNormalizer()
ekg = EngineeringKnowledgeGraph()
rag_engine = RetrievalEngine()
rca_analyzer = RootCauseAnalyzer(ekg)
multi_agent = ChipPilotMultiAgentFlow(rca_analyzer, rag_engine)
optimizer = OptimizationAdvisor()
verifier = VerificationSandbox(WORKSPACE_DIR)
pdf_generator = PDFReportGenerator()

# Request Models
class AnalyzeRequest(BaseModel):
    project_id: str
    top_module: str
    rtl_files: List[str]
    sdc_file: Optional[str] = None

class AskRequest(BaseModel):
    run_id: str
    query: str

class VerifyRequest(BaseModel):
    top_module: str
    baseline_files: List[str]
    fixed_files: List[str]

@app.get("/")
def root():
    return {
        "service": "ChipPilot AI Backend API",
        "status": "ONLINE",
        "capabilities": [
            "RTL Parsing & Hazard Detection",
            "Verilator/Yosys/OpenSTA Orchestration & Emulation",
            "Engineering Knowledge Graph (EKG)",
            "Deterministic Multi-Factor Root-Cause Analysis",
            "Hybrid RAG Retrieval",
            "Multi-Agent Grounded Reasoning",
            "Closed-Loop PPA Verification Sandbox"
        ]
    }

@app.post("/api/v1/projects/analyze")
def run_analysis_pipeline(req: AnalyzeRequest):
    """Executes the full end-to-end RTL and EDA diagnostic cycle."""
    run_id = str(uuid.uuid4())
    
    # 1. Parse RTL Files
    parsed_ast = []
    for f in req.rtl_files:
        if os.path.exists(f):
            parsed_ast.append(rtl_parser.parse_file(f))

    if not parsed_ast:
        raise HTTPException(status_code=400, detail="No valid RTL files found to parse.")

    # 2. Run EDA Pipeline
    top_file = req.rtl_files[0]
    lint_raw = eda_orchestrator.run_verilator_lint(top_file)
    synth_raw = eda_orchestrator.run_yosys_synthesis(req.top_module, req.rtl_files)
    
    synth_netlist = synth_raw.get("netlist_file", "")
    sta_raw = eda_orchestrator.run_opensta_timing(req.top_module, synth_netlist, req.sdc_file)

    # 3. Normalize Reports
    lint_findings = normalizer.normalize_verilator(lint_raw.get("stderr", ""), lint_raw.get("stdout", ""))
    synth_data = normalizer.normalize_yosys(synth_raw.get("stdout", ""))
    timing_data = normalizer.normalize_opensta(sta_raw.get("stdout", ""))

    # 4. Build EKG & Index Vector RAG
    ekg.build_graph(parsed_ast, lint_findings, synth_data, timing_data)
    rag_engine.index_project(parsed_ast, lint_findings, timing_data.get("timing_paths", []))

    # 5. Deterministic RCA
    root_causes = rca_analyzer.analyze_root_causes(parsed_ast, lint_findings, timing_data, synth_data)

    # 6. Optimization Proposals
    optimizations = optimizer.evaluate_optimizations(
        timing_data, synth_data.get("statistics", {}), lint_findings
    )

    # 7. Persist to Database
    db.save_project(req.project_id, req.project_id, req.top_module, req.rtl_files)
    db.save_analysis_run(
        run_id=run_id,
        project_id=req.project_id,
        worst_slack=timing_data.get("worst_slack", 0.0),
        total_cells=synth_data.get("statistics", {}).get("total_cells", 0),
        lint_errors=sum(1 for l in lint_findings if l.get("severity") == "ERROR"),
        lint_warnings=sum(1 for l in lint_findings if l.get("severity") == "WARNING"),
        findings=lint_findings,
        timing_paths=timing_data.get("timing_paths", []),
        root_causes=root_causes,
        optimizations=optimizations
    )

    return {
        "run_id": run_id,
        "project_id": req.project_id,
        "top_module": req.top_module,
        "status": "COMPLETED",
        "worst_slack_ns": timing_data.get("worst_slack", 0.0),
        "total_cells": synth_data.get("statistics", {}).get("total_cells", 0),
        "lint_findings_count": len(lint_findings),
        "root_causes_count": len(root_causes),
        "optimizations_count": len(optimizations)
    }

@app.post("/api/v1/projects/ask")
def ask_assistant(req: AskRequest):
    """Executes multi-agent grounded reasoning over the knowledge graph and RAG context."""
    run_data = db.get_run(req.run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run ID not found in database.")

    agent_state = AgentState(
        project_id=run_data.get("project_id", "project"),
        parsed_ast=[],
        lint_findings=run_data.get("findings", []),
        synth_stats={"total_cells": run_data.get("total_cells", 0)},
        timing_data={"worst_slack": run_data.get("worst_slack", 0.0), "timing_paths": run_data.get("timing_paths", [])},
        user_query=req.query
    )

    processed_state = multi_agent.execute_workflow(agent_state)
    db.save_chat(req.run_id, req.query, processed_state.final_response)

    return {
        "run_id": req.run_id,
        "query": req.query,
        "response": processed_state.final_response,
        "top_root_causes": processed_state.root_causes[:3]
    }

@app.post("/api/v1/projects/verify")
def run_verification(req: VerifyRequest):
    """Runs closed-loop comparative verification between baseline and fixed RTL."""
    res = verifier.run_comparative_verification(req.top_module, req.baseline_files, req.fixed_files)
    return res

@app.get("/api/v1/projects/{run_id}/report")
def get_report(run_id: str):
    run_data = db.get_run(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run ID not found.")
    return run_data

@app.get("/api/v1/projects/{run_id}/report/pdf")
def get_report_pdf(run_id: str):
    """Generates and downloads the formal Engineering Audit Report in PDF format."""
    run_data = db.get_run(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run ID not found.")
    
    # Format run_data structure expected by PDF generator
    formatted_data = {
        "top_module": run_data.get("project_id", "cpu_top"),
        "timing_data": {
            "worst_slack": run_data.get("worst_slack", 0.0),
            "timing_paths": run_data.get("timing_paths", [])
        },
        "synth_data": {
            "statistics": {
                "total_cells": run_data.get("total_cells", 0),
                "cells": {}
            }
        },
        "lint_findings": run_data.get("findings", []),
        "root_causes": run_data.get("root_causes", []),
        "optimizations": run_data.get("optimizations", []),
        "parsed_ast": []
    }
    
    pdf_bytes = pdf_generator.generate_audit_report(formatted_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={run_id}_audit_report.pdf"}
    )

@app.post("/api/v1/projects/verify/pdf")
def get_verification_report_pdf(req: VerifyRequest):
    """Executes comparative verification and returns the sign-off scorecard in PDF format."""
    res = verifier.run_comparative_verification(req.top_module, req.baseline_files, req.fixed_files)
    pdf_bytes = pdf_generator.generate_verification_report(res, top_module=req.top_module)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={req.top_module}_verification_report.pdf"}
    )

@app.get("/api/v1/projects/{run_id}/ekg")
def get_ekg_graph(run_id: str):
    return ekg.get_all_nodes_and_edges()
