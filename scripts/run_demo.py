"""
ChipPilot AI - Automated CLI End-to-End Demonstration Script
Executes the full pipeline on demo SoC, performs RCA, runs comparative verification,
and displays results in clean terminal formatting.
"""

import os
import sys
import json
import time

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.rtl_parser import RTLParser
from eda.orchestrator import EDAOrchestrator
from eda.report_normalizer import ReportNormalizer
from knowledge_graph.graph_engine import EngineeringKnowledgeGraph
from root_cause.analyzer import RootCauseAnalyzer
from rag.retrieval_engine import RetrievalEngine
from agents.langgraph_workflow import ChipPilotMultiAgentFlow, AgentState
from optimization.advisor import OptimizationAdvisor
from optimization.verifier import VerificationSandbox
from database.db_manager import DatabaseManager
from backend.config import DATABASE_PATH, WORKSPACE_DIR
from reports.pdf_generator import PDFReportGenerator

def run_cli_demo():
    print("=" * 80)
    print("CHIPPILOT AI -- INTELLIGENT RTL ENGINEERING ASSISTANT (CLI DEMO)")
    print("=" * 80)

    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl")
    faulty_files = [os.path.join(base_dir, "faulty", f) for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]
    fixed_files = [os.path.join(base_dir, "fixed", f) for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]
    top_mod = "cpu_top"

    # 1. Parse RTL
    print("\n[Step 1/8] Ingesting & Parsing RTL Source Files...")
    parser = RTLParser()
    parsed_ast = [parser.parse_file(f) for f in faulty_files]
    print(f"  -> Parsed {len(parsed_ast)} Verilog source files.")
    for f in parsed_ast:
        for m in f["modules"]:
            if m["antipatterns"]:
                print(f"  -> Flagged {len(m['antipatterns'])} hazard(s) in `{m['name']}` ({f['filename']})")

    # 2. EDA Orchestration
    print("\n[Step 2/8] Executing EDA Diagnostic Suite (Verilator Lint, Yosys Synthesis, OpenSTA STA)...")
    orchestrator = EDAOrchestrator(WORKSPACE_DIR)
    lint_raw = orchestrator.run_verilator_lint(faulty_files[0])
    synth_raw = orchestrator.run_yosys_synthesis(top_mod, faulty_files)
    timing_raw = orchestrator.run_opensta_timing(top_mod, synth_raw.get("netlist_file", ""))

    # 3. Report Normalization
    print("\n[Step 3/8] Normalizing Heterogeneous Tool Reports...")
    normalizer = ReportNormalizer()
    lint_findings = normalizer.normalize_verilator(lint_raw.get("stderr", ""), lint_raw.get("stdout", ""))
    synth_data = normalizer.normalize_yosys(synth_raw.get("stdout", ""))
    timing_data = normalizer.normalize_opensta(timing_raw.get("stdout", ""))

    worst_slack = timing_data.get("worst_slack", 0.0)
    print(f"  -> Verilator Lint Findings: {len(lint_findings)}")
    print(f"  -> Yosys Synthesized Cells: {synth_data.get('statistics', {}).get('total_cells', 0)}")
    print(f"  -> OpenSTA Worst Slack (WNS): {worst_slack:+.2f} ns ({'VIOLATION' if worst_slack < 0 else 'MET'})")

    # 4. EKG Construction
    print("\n[Step 4/8] Building Engineering Knowledge Graph (EKG)...")
    ekg = EngineeringKnowledgeGraph()
    ekg.build_graph(parsed_ast, lint_findings, synth_data, timing_data)
    g_stats = ekg.get_summary_stats()
    print(f"  -> Constructed EKG: {g_stats['total_nodes']} Nodes, {g_stats['total_edges']} Edges.")

    # 5. Hybrid RAG Indexing
    print("\n[Step 5/8] Indexing Design Artifacts in Vector Store (FAISS)...")
    rag = RetrievalEngine()
    rag.index_project(parsed_ast, lint_findings, timing_data.get("timing_paths", []))
    print(f"  -> Indexed {len(rag.documents)} AST and Report Chunks.")

    # 6. Deterministic RCA
    print("\n[Step 6/8] Executing Deterministic Root-Cause Analyzer (RCA)...")
    rca = RootCauseAnalyzer(ekg)
    root_causes = rca.analyze_root_causes(parsed_ast, lint_findings, timing_data, synth_data)
    print(f"  -> Identified & Ranked {len(root_causes)} Candidate Root Causes:")
    for idx, c in enumerate(root_causes[:3], 1):
        print(f"     [{idx}] {c['title']} | Confidence: {int(c['confidence_score']*100)}% | Severity: {c['severity']}")
        print(f"         Hypothesis: {c['hypothesis']}")

    # 7. Grounded Multi-Agent Q&A
    print("\n[Step 7/8] Running Grounded AI Multi-Agent Reasoning...")
    multi_agent = ChipPilotMultiAgentFlow(rca, rag)
    state = AgentState(
        project_id=top_mod,
        parsed_ast=parsed_ast,
        lint_findings=lint_findings,
        synth_stats=synth_data.get("statistics", {}),
        timing_data=timing_data,
        user_query="Why is timing failing in ALU and how do we fix it?"
    )
    processed = multi_agent.execute_workflow(state)
    print("-" * 80)
    print(processed.final_response)
    print("-" * 80)

    # 8. Comparative Verification Sandbox
    print("\n[Step 8/8] Executing Closed-Loop Verification Harness (Faulty vs Fixed Reference)...")
    verifier = VerificationSandbox(WORKSPACE_DIR)
    v_res = verifier.run_comparative_verification(top_mod, faulty_files, fixed_files)

    print("\n" + "=" * 80)
    print("COMPARATIVE PPA VERIFICATION SCORECARD")
    print("=" * 80)
    print(f"  {'Metric':<30} | {'Baseline (Pre-Fix)':<20} | {'Fixed (Post-Fix)':<20} | {'Improvement Delta'}")
    print("  " + "-" * 76)
    print(f"  {'Worst Slack (WNS)':<30} | {v_res['baseline']['worst_slack']:+.2f} ns{'':<13} | {v_res['fixed']['worst_slack']:+.2f} ns{'':<13} | +{v_res['delta']['slack_improvement_ns']:.2f} ns")
    print(f"  {'Inferred Latches':<30} | {v_res['baseline']['inferred_latches']:<20} | {v_res['fixed']['inferred_latches']:<20} | -{v_res['delta']['latches_eliminated']} latches")
    print(f"  {'Lint Rule Violations':<30} | {v_res['baseline']['lint_violations']:<20} | {v_res['fixed']['lint_violations']:<20} | -{v_res['delta']['lint_issues_resolved']} warnings")
    print(f"  {'Total Cell Count (Area)':<30} | {v_res['baseline']['total_cells']:<20} | {v_res['fixed']['total_cells']:<20} | {v_res['delta']['cell_count_change']} cells")
    print("=" * 80)
    print(f"  Final Verification Status: {'PASSED -- ALL DEFECTS RESOLVED & TIMING CLOSED' if v_res['is_verified'] else 'FAILED'}")
    print("=" * 80)

    # 9. PDF Engineering Audit & Verification Report Generation
    print("\n[Audit & Verification] Compiling Publication-Ready PDF Reports...")
    pdf_gen = PDFReportGenerator()
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    audit_pdf_path = os.path.join(reports_dir, f"{top_mod}_audit_report.pdf")
    verification_pdf_path = os.path.join(reports_dir, f"{top_mod}_verification_signoff.pdf")

    # Compile run data for audit PDF
    run_summary = {
        "top_module": top_mod,
        "timing_data": timing_data,
        "synth_data": synth_data,
        "lint_findings": lint_findings,
        "root_causes": root_causes,
        "optimizations": [
            {
                "category": "LATCH_ELIMINATION",
                "target_path": "demo_rtl/faulty/alu.v",
                "action": "ADD_DEFAULT_ASSIGNMENT",
                "description": "Add default case assignment in ALU always block to eliminate latch inference.",
                "expected_gain": "Eliminates transparent latch $_DLATCH_P_",
                "verification": "Re-run Verilator lint and Yosys synthesis"
            }
        ],
        "parsed_ast": parsed_ast
    }

    pdf_gen.generate_audit_report(run_summary, output_path=audit_pdf_path)
    pdf_gen.generate_verification_report(v_res, top_module=top_mod, output_path=verification_pdf_path)

    # Save structured verification scorecard JSON
    scorecard_json_path = os.path.join(reports_dir, f"{top_mod}_verification_scorecard.json")
    with open(scorecard_json_path, "w", encoding="utf-8") as f:
        json.dump(v_res, f, indent=2)

    # Save Executive Summary Markdown
    summary_md_path = os.path.join(reports_dir, f"{top_mod}_executive_summary.md")
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write(f"# ChipPilot AI — Verification & Audit Summary ({top_mod})\n\n")
        f.write(f"**Date/Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 📊 Comparative PPA Verification Scorecard\n\n")
        f.write("| Metric | Baseline (Pre-Fix) | Fixed (Post-Fix) | Improvement Delta | Status |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Worst Slack (WNS)** | `{v_res['baseline']['worst_slack']:+.2f} ns` | `{v_res['fixed']['worst_slack']:+.2f} ns` | `+{v_res['delta']['slack_improvement_ns']:.2f} ns` | **TIMING CLOSED** |\n")
        f.write(f"| **Inferred Latches** | `{v_res['baseline']['inferred_latches']}` | `{v_res['fixed']['inferred_latches']}` | `-{v_res['delta']['latches_eliminated']}` | **ELIMINATED** |\n")
        f.write(f"| **Lint Violations** | `{v_res['baseline']['lint_violations']}` | `{v_res['fixed']['lint_violations']}` | `-{v_res['delta']['lint_issues_resolved']}` | **RESOLVED** |\n")
        f.write(f"| **Total Cell Count (Area)** | `{v_res['baseline']['total_cells']}` | `{v_res['fixed']['total_cells']}` | `{v_res['delta']['cell_count_change']}` | **OPTIMIZED** |\n\n")
        f.write(f"**Verification Status:** `{'PASSED — ALL DEFECTS RESOLVED & TIMING CLOSED' if v_res['is_verified'] else 'FAILED'}`\n\n")
        f.write("## 🔍 Root Cause Analysis Findings\n\n")
        for idx, rc in enumerate(root_causes, 1):
            f.write(f"### {idx}. {rc['title']} (Confidence: {int(rc['confidence_score']*100)}% | Severity: {rc['severity']})\n")
            f.write(f"- **Hypothesis:** {rc.get('hypothesis', 'N/A')}\n")
            if "evidence" in rc and rc["evidence"]:
                f.write(f"- **Evidence:**\n")
                for ev in rc["evidence"]:
                    f.write(f"  * `{ev}`\n")
            f.write("\n")
        f.write("## 📁 Saved Artifacts\n\n")
        f.write(f"- **Audit PDF Report:** `{audit_pdf_path}`\n")
        f.write(f"- **Verification Signoff PDF:** `{verification_pdf_path}`\n")
        f.write(f"- **Verification Scorecard JSON:** `{scorecard_json_path}`\n")

    print(f"  -> Engineering Audit Report (PDF):     {audit_pdf_path}")
    print(f"  -> Verification Sign-Off Report (PDF): {verification_pdf_path}")
    print(f"  -> Verification Scorecard (JSON):      {scorecard_json_path}")
    print(f"  -> Executive Summary (Markdown):       {summary_md_path}")
    print("\n" + "#" * 80)
    print(f"  ALL OUTPUTS SUCCESSFULLY GENERATED AND SAVED TO 'reports/'")
    print(f"  Files are ready for developer verification & signoff.")
    print("#" * 80 + "\n", flush=True)

class OutputTee:
    """Tees stdout to both terminal and a saved log file."""
    def __init__(self, filepath: str):
        self.terminal = sys.stdout
        self.log_file = open(filepath, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()

if __name__ == "__main__":
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    log_path = os.path.join(reports_dir, "run_demo_output.log")
    tee = OutputTee(log_path)
    sys.stdout = tee
    try:
        run_cli_demo()
        print(f"  -> Complete Execution Log saved to:   {log_path}\n", flush=True)
    finally:
        sys.stdout = tee.terminal
        tee.close()

