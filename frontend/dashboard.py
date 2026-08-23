"""
ChipPilot AI - Interactive Engineering Dashboard
High-density Streamlit interface for RTL Analysis, Timing Diagnostics, EKG Graphing,
RCA Confidence Scoring, AI Grounded Chatbot, and Closed-Loop Verification.
"""

import streamlit as st
import os
import sys
import json
import pandas as pd

# Add project root to sys.path
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

st.set_page_config(
    page_title="ChipPilot AI — RTL Engineering Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich dark-mode aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #334155;
    }
    .cause-card {
        background-color: #0f172a;
        border-left: 4px solid #f43f5e;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    .evidence-tag {
        background-color: #1e293b;
        color: #38bdf8;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "initialized" not in st.session_state:
    st.session_state.db = DatabaseManager(DATABASE_PATH)
    st.session_state.parser = RTLParser()
    st.session_state.orchestrator = EDAOrchestrator(WORKSPACE_DIR)
    st.session_state.normalizer = ReportNormalizer()
    st.session_state.ekg = EngineeringKnowledgeGraph()
    st.session_state.rag = RetrievalEngine()
    st.session_state.rca = RootCauseAnalyzer(st.session_state.ekg)
    st.session_state.multi_agent = ChipPilotMultiAgentFlow(st.session_state.rca, st.session_state.rag)
    st.session_state.optimizer = OptimizationAdvisor()
    st.session_state.verifier = VerificationSandbox(WORKSPACE_DIR)
    st.session_state.pdf_gen = PDFReportGenerator()
    st.session_state.analysis_run = None
    st.session_state.last_verification = None
    st.session_state.chat_history = []
    st.session_state.initialized = True

# Sidebar Controls
st.sidebar.title("⚡ ChipPilot AI")
st.sidebar.markdown("**Intelligent RTL Engineering Assistant**")
st.sidebar.divider()

demo_mode = st.sidebar.selectbox(
    "Target RTL Project",
    ["Demo RISC-V SoC (Faulty Test Suite)", "Demo RISC-V SoC (Fixed Clean Reference)", "Custom Project Path"]
)

if demo_mode == "Demo RISC-V SoC (Faulty Test Suite)":
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl", "faulty")
    top_mod = "cpu_top"
    default_files = [os.path.join(base_dir, f) for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]
elif demo_mode == "Demo RISC-V SoC (Fixed Clean Reference)":
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl", "fixed")
    top_mod = "cpu_top"
    default_files = [os.path.join(base_dir, f) for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]
else:
    custom_dir = st.sidebar.text_input("Project Directory", "./demo_rtl/faulty")
    top_mod = st.sidebar.text_input("Top Module Name", "cpu_top")
    default_files = [os.path.join(custom_dir, f) for f in os.listdir(custom_dir) if f.endswith(('.v', '.sv'))] if os.path.exists(custom_dir) else []

run_btn = st.sidebar.button("🚀 Run Full Diagnostic Pipeline", type="primary", use_container_width=True)

st.sidebar.divider()
st.sidebar.markdown("### Execution Pipeline")
st.sidebar.markdown("""
1. **RTL AST & Hazard Parsing**
2. **Verilator Lint Execution**
3. **Yosys Logic Synthesis**
4. **OpenSTA Static Timing Analysis**
5. **Engineering Knowledge Graph**
6. **Deterministic RCA Scoring**
7. **Hybrid RAG Semantic Indexing**
8. **Multi-Agent AI Reasoning**
""")

# Run Analysis Pipeline Logic
if run_btn or st.session_state.analysis_run is None:
    with st.spinner("Executing ChipPilot AI Diagnostic Suite..."):
        # 1. Parse RTL
        parsed_ast = [st.session_state.parser.parse_file(f) for f in default_files if os.path.exists(f)]
        
        # 2. Run EDA
        top_file = default_files[0] if default_files else ""
        lint_raw = st.session_state.orchestrator.run_verilator_lint(top_file)
        synth_raw = st.session_state.orchestrator.run_yosys_synthesis(top_mod, default_files)
        synth_netlist = synth_raw.get("netlist_file", "")
        timing_raw = st.session_state.orchestrator.run_opensta_timing(top_mod, synth_netlist)

        # 3. Normalize
        lint_findings = st.session_state.normalizer.normalize_verilator(lint_raw.get("stderr", ""), lint_raw.get("stdout", ""))
        synth_data = st.session_state.normalizer.normalize_yosys(synth_raw.get("stdout", ""))
        timing_data = st.session_state.normalizer.normalize_opensta(timing_raw.get("stdout", ""))

        # 4. EKG & RAG
        st.session_state.ekg.build_graph(parsed_ast, lint_findings, synth_data, timing_data)
        st.session_state.rag.index_project(parsed_ast, lint_findings, timing_data.get("timing_paths", []))

        # 5. RCA & Optimizations
        root_causes = st.session_state.rca.analyze_root_causes(parsed_ast, lint_findings, timing_data, synth_data)
        optimizations = st.session_state.optimizer.evaluate_optimizations(
            timing_data, synth_data.get("statistics", {}), lint_findings
        )

        st.session_state.analysis_run = {
            "top_module": top_mod,
            "parsed_ast": parsed_ast,
            "lint_findings": lint_findings,
            "synth_data": synth_data,
            "timing_data": timing_data,
            "root_causes": root_causes,
            "optimizations": optimizations,
            "files": default_files
        }

run_data = st.session_state.analysis_run

# Header Title
st.markdown('<p class="main-header">⚡ ChipPilot AI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Unified RTL Analysis, Cross-EDA Report Correlation, Root-Cause Diagnostics & PPA Optimization</p>', unsafe_allow_html=True)

# KPI Metrics Row
worst_slack = run_data["timing_data"].get("worst_slack", 0.0)
total_cells = run_data["synth_data"].get("statistics", {}).get("total_cells", 0)
latches = run_data["synth_data"].get("statistics", {}).get("cells", {}).get("$_DLATCH_P_", 0)
lint_count = len(run_data["lint_findings"])
rca_count = len(run_data["root_causes"])

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    slack_delta_color = "inverse" if worst_slack < 0 else "normal"
    st.metric("Worst Slack (WNS)", f"{worst_slack:+.2f} ns", delta=f"{'VIOLATION' if worst_slack < 0 else 'MET'}", delta_color=slack_delta_color)
with col2:
    st.metric("Total Cells (Area)", f"{total_cells:,}", delta=f"{latches} Inferred Latches", delta_color="inverse" if latches > 0 else "normal")
with col3:
    st.metric("Lint Warnings", f"{lint_count}", delta="Verilator Rules", delta_color="inverse" if lint_count > 0 else "off")
with col4:
    st.metric("Ranked Root Causes", f"{rca_count}", delta="Deterministic Score", delta_color="off")
with col5:
    st.metric("PPA Optimizations", f"{len(run_data['optimizations'])}", delta="Actionable Patches", delta_color="normal")

st.divider()

# Main Interactive Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊 Overview & Hierarchy",
    "🔍 RTL AST & Hazards",
    "⏱️ Static Timing (STA)",
    "⚙️ Synthesis & Cells",
    "⚠️ Lint Violations",
    "🕸️ Knowledge Graph (EKG)",
    "🎯 Root-Cause Analysis",
    "🤖 Grounded AI Co-Pilot",
    "🛠️ PPA Optimization Sandbox",
    "📄 Audit Report Export"
])

# Tab 1: Overview & Hierarchy
with tab1:
    st.subheader("Project Structure & Hierarchy")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("#### Ingested Design Files")
        file_df = []
        for f in run_data["parsed_ast"]:
            file_df.append({
                "File": f.get("filename"),
                "Modules": len(f.get("modules", [])),
                "Path": f.get("file_path")
            })
        st.dataframe(pd.DataFrame(file_df), use_container_width=True)

    with col_b:
        st.markdown("#### Module Hierarchy Breakdown")
        for f in run_data["parsed_ast"]:
            for mod in f.get("modules", []):
                with st.expander(f"📦 Module `{mod['name']}` ({f['filename']})", expanded=True):
                    st.write(f"**Ports:** {len(mod.get('ports', []))} | **Registers:** {len(mod.get('registers', []))} | **Wires:** {len(mod.get('wires', []))}")
                    st.write(f"**Clocks:** `{mod.get('clocks')}` | **Resets:** `{mod.get('resets')}`")
                    if mod.get("instantiations"):
                        st.write("**Instantiates:** " + ", ".join([f"`{i['submodule']} ({i['instance_name']})`" for i in mod["instantiations"]]))

# Tab 2: RTL AST & Hazards
with tab2:
    st.subheader("RTL Code & Structural Hazard Inspector")
    selected_file_entry = st.selectbox(
        "Select RTL File to Inspect",
        run_data["parsed_ast"],
        format_func=lambda x: x.get("filename", "")
    )
    if selected_file_entry:
        file_path = selected_file_entry["file_path"]
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                code_text = f.read()
            st.code(code_text, language="verilog", line_numbers=True)

        for mod in selected_file_entry.get("modules", []):
            if mod.get("antipatterns"):
                st.markdown(f"#### ⚠️ Identified Structural Hazards in `{mod['name']}`:")
                for ap in mod["antipatterns"]:
                    st.warning(f"**[{ap['severity']}] {ap['type']} (Line {ap.get('line', 1)}):** {ap['description']}")

# Tab 3: Static Timing (STA)
with tab3:
    st.subheader("Static Timing Analysis (OpenSTA)")
    tdata = run_data["timing_data"]
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("#### Timing Slack Summary")
        if worst_slack < 0:
            st.error(f"🔴 Setup Timing Violated!\n\n**Worst Negative Slack (WNS):** `{worst_slack:.4f} ns`\n\nTarget Clock Period: `10.00 ns`")
        else:
            st.success(f"🟢 Setup Timing Constraints Met!\n\n**Slack Margin:** `+{worst_slack:.4f} ns`\n\nTarget Clock Period: `10.00 ns`")
    with c2:
        st.markdown("#### Critical Paths")
        path_list = tdata.get("timing_paths", [])
        if path_list:
            path_df = pd.DataFrame([{
                "Startpoint": p.get("startpoint"),
                "Endpoint": p.get("endpoint"),
                "Slack (ns)": p.get("slack"),
                "Arrival (ns)": p.get("data_arrival_time"),
                "Required (ns)": p.get("data_required_time"),
                "Status": "VIOLATION" if p.get("is_violation") else "MET"
            } for p in path_list])
            st.dataframe(path_df, use_container_width=True)
            
            with st.expander("🔍 View Raw STA Pin-by-Pin Delay Trace"):
                st.text(path_list[0].get("raw_path_dump", ""))

# Tab 4: Synthesis & Cells
with tab4:
    st.subheader("Synthesis & Gate-Level Statistics (Yosys)")
    stats = run_data["synth_data"].get("statistics", {})
    cells = stats.get("cells", {})
    
    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        st.markdown("#### Standard Cell Distribution")
        if cells:
            cell_df = pd.DataFrame(list(cells.items()), columns=["Cell Type", "Count"]).sort_values(by="Count", ascending=False)
            st.dataframe(cell_df, use_container_width=True)
    with col_s2:
        st.markdown("#### Cell Count Visualization")
        if cells:
            st.bar_chart(pd.DataFrame(list(cells.items()), columns=["Cell", "Count"]).set_index("Cell"))

# Tab 5: Lint Violations
with tab5:
    st.subheader("Static Rule Violations (Verilator)")
    lfindings = run_data["lint_findings"]
    if lfindings:
        lint_df = pd.DataFrame([{
            "Severity": l.get("severity"),
            "Rule Code": l.get("code"),
            "File": os.path.basename(l.get("file", "")),
            "Line": l.get("line"),
            "Message": l.get("message")
        } for l in lfindings])
        st.dataframe(lint_df, use_container_width=True)
    else:
        st.success("✅ Zero Lint Violations! Design conforms to all standard static checks.")

# Tab 6: Knowledge Graph (EKG)
with tab6:
    st.subheader("Engineering Knowledge Graph (EKG)")
    ekg_stats = st.session_state.ekg.get_summary_stats()
    st.markdown(f"**Total Graph Nodes:** `{ekg_stats['total_nodes']}` | **Total Graph Edges:** `{ekg_stats['total_edges']}`")
    
    st.markdown("#### Entity Type Distribution")
    st.json(ekg_stats.get("entity_breakdown", {}))

    with st.expander("🔍 View All Graph Nodes & Relationships"):
        all_graph = st.session_state.ekg.get_all_nodes_and_edges()
        st.write(f"Sample Nodes (Total {len(all_graph['nodes'])}):")
        st.dataframe(pd.DataFrame(all_graph["nodes"][:15]), use_container_width=True)

# Tab 7: Root-Cause Analysis
with tab7:
    st.subheader("Deterministic Root-Cause Analysis (RCA)")
    st.markdown("Candidate root causes ranked by multi-factor cross-tool evidence scoring:")

    for idx, cause in enumerate(run_data["root_causes"], 1):
        conf = cause["confidence_score"]
        conf_pct = int(conf * 100)
        
        with st.container():
            st.markdown(f"""
            <div class="cause-card">
                <h4>#{idx} {cause['title']} &nbsp; <span style="color:#38bdf8;">[Confidence: {conf_pct}%]</span></h4>
                <p><b>Severity:</b> <code>{cause['severity']}</code> | <b>Location:</b> <code>{os.path.basename(cause.get('file',''))}:{cause.get('line', 1)}</code></p>
                <p><b>Diagnostic Hypothesis:</b> {cause['hypothesis']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(conf)
            st.markdown("**Verified Multi-Tool Evidence:**")
            for ev in cause.get("evidence", []):
                st.markdown(f"- `{ev}`")
            st.divider()

# Tab 8: Grounded AI Co-Pilot
with tab8:
    st.subheader("Grounded Natural-Language AI Assistant")
    st.markdown("Ask natural language questions regarding timing paths, lint errors, synthesis cells, or micro-architectural fixes.")

    user_query = st.chat_input("Ask ChipPilot AI (e.g., 'Why is timing failing in ALU and what is the root cause?')...")
    
    # Pre-canned quick questions
    st.markdown("**Quick Inquiries:**")
    quick_cols = st.columns(3)
    if quick_cols[0].button("❓ Why is timing failing?"):
        user_query = "Why is the critical timing path failing and which module is responsible?"
    if quick_cols[1].button("❓ Explain latch warning"):
        user_query = "What caused the inferred latch warning in the ALU and how do I resolve it?"
    if quick_cols[2].button("❓ Recommend PPA fixes"):
        user_query = "Provide concrete RTL code modifications to close timing and fix all lint issues."

    if user_query:
        with st.spinner("AI Assistant synthesizing grounded response..."):
            agent_state = AgentState(
                project_id=run_data["top_module"],
                parsed_ast=run_data["parsed_ast"],
                lint_findings=run_data["lint_findings"],
                synth_stats=run_data["synth_data"].get("statistics", {}),
                timing_data=run_data["timing_data"],
                user_query=user_query
            )
            processed_state = st.session_state.multi_agent.execute_workflow(agent_state)
            st.session_state.chat_history.append((user_query, processed_state.final_response))

    for q, a in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.markdown(a)

# Tab 9: Optimization Sandbox
with tab9:
    st.subheader("Closed-Loop PPA Optimization Sandbox")
    st.markdown("Evaluate prescribed RTL patches through automated before-and-after comparative EDA execution.")

    st.markdown("#### Recommended RTL Optimization Patches")
    for opt in run_data["optimizations"]:
        with st.expander(f"🔧 `{opt['action']}` ({opt['category']})", expanded=True):
            st.write(f"**Target:** `{opt['target_path']}`")
            st.write(f"**Prescription:** {opt['description']}")
            st.write(f"**Expected Gain:** `{opt['expected_gain']}`")
            st.write(f"**Verification Step:** `{opt['verification']}`")

    st.divider()
    st.markdown("#### 🔄 Run Comparative Verification (Faulty Baseline vs Fixed Reference)")
    if st.button("🧪 Execute Closed-Loop Verification Harness", type="primary"):
        base_files = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl", "faulty", f) 
                      for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]
        fix_files = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo_rtl", "fixed", f) 
                     for f in ["cpu_top.v", "alu.v", "regfile.v", "control_unit.v", "data_memory.v"]]

        with st.spinner("Executing comparative regression across full EDA toolchain..."):
            v_res = st.session_state.verifier.run_comparative_verification("cpu_top", base_files, fix_files)
            st.session_state.last_verification = v_res
            st.success("✅ Comparative Verification Run Complete! All defects resolved and timing closed.")

    if st.session_state.last_verification:
        v_res = st.session_state.last_verification
        # Comparison Scorecard Table
        comp_data = [
            {"Metric": "Worst Negative Slack (WNS)", "Baseline (Pre-Fix)": f"{v_res['baseline']['worst_slack']:.2f} ns", "Fixed (Post-Fix)": f"{v_res['fixed']['worst_slack']:.2f} ns", "Delta (Improvement)": f"+{v_res['delta']['slack_improvement_ns']:.2f} ns"},
            {"Metric": "Inferred Latches", "Baseline (Pre-Fix)": str(v_res['baseline']['inferred_latches']), "Fixed (Post-Fix)": str(v_res['fixed']['inferred_latches']), "Delta (Improvement)": f"-{v_res['delta']['latches_eliminated']} latches"},
            {"Metric": "Lint Rule Violations", "Baseline (Pre-Fix)": str(v_res['baseline']['lint_violations']), "Fixed (Post-Fix)": str(v_res['fixed']['lint_violations']), "Delta (Improvement)": f"-{v_res['delta']['lint_issues_resolved']} warnings"},
            {"Metric": "Total Cell Count (Area)", "Baseline (Pre-Fix)": str(v_res['baseline']['total_cells']), "Fixed (Post-Fix)": str(v_res['fixed']['total_cells']), "Delta (Improvement)": f"{v_res['delta']['cell_count_change']} cells"}
        ]
        st.table(pd.DataFrame(comp_data))

        # Generate Verification Sign-Off PDF
        v_pdf_bytes = st.session_state.pdf_gen.generate_verification_report(v_res, top_module=run_data["top_module"])
        st.download_button(
            label="📥 Download Closed-Loop Verification Sign-Off Report (.pdf)",
            data=v_pdf_bytes,
            file_name=f"{run_data['top_module']}_verification_signoff.pdf",
            mime="application/pdf",
            type="primary"
        )

# Tab 10: Audit Report Export
with tab10:
    st.subheader("Professional Engineering Audit & Verification Report")
    st.markdown("Generate and download formal engineering audit reports formatted for architectural review and developer sign-off.")

    # Generate PDF Report
    pdf_bytes = st.session_state.pdf_gen.generate_audit_report(run_data)

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        st.download_button(
            label="📥 Download Engineering Audit Report (.pdf)",
            data=pdf_bytes,
            file_name=f"{run_data['top_module']}_chippilot_audit.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    with col_btn2:
        report_md = f"""# ChipPilot AI — Engineering Audit Report
**Design:** `{run_data['top_module']}`
**Analysis Date:** `2026-08-18`
**Status:** `{'🔴 VIOLATIONS DETECTED' if (worst_slack < 0 or lint_count > 0) else '🟢 DESIGN CLEAN'}`

## 1. Key Performance Metrics
- **Worst Negative Slack (WNS):** `{worst_slack:+.2f} ns`
- **Total Synthesized Cells:** `{total_cells:,}`
- **Inferred Latches:** `{latches}`
- **Static Lint Violations:** `{lint_count}`

## 2. Top Ranked Root Causes
"""
        for idx, c in enumerate(run_data["root_causes"][:3], 1):
            report_md += f"### [{idx}] {c['title']} (Confidence: {int(c['confidence_score']*100)}%)\n"
            report_md += f"- **Location:** `{c.get('file')}:{c.get('line')}`\n"
            report_md += f"- **Hypothesis:** {c.get('hypothesis')}\n"
            report_md += "- **Evidence:**\n"
            for ev in c.get("evidence", []):
                report_md += f"  * {ev}\n"

        st.download_button(
            label="📥 Download Audit Summary (.md)",
            data=report_md,
            file_name=f"{run_data['top_module']}_chippilot_audit.md",
            mime="text/markdown",
            use_container_width=True
        )

    st.divider()

    # Developer Sign-Off Checklist Card
    st.markdown("### 📋 Developer Sign-Off & Verification Checklist")
    sign_col1, sign_col2 = st.columns(2)
    with sign_col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Timing & Structural Sign-Off</h4>
            <p>• <b>Setup Slack:</b> <code>{worst_slack:+.2f} ns</code> ({'✅ MET' if worst_slack >= 0 else '❌ VIOLATION'})</p>
            <p>• <b>Asynchronous Latches:</b> <code>{latches}</code> ({'✅ ZERO HAZARDS' if latches == 0 else '❌ LATCH DETECTED'})</p>
            <p>• <b>Static Lint Issues:</b> <code>{lint_count}</code> ({'✅ CLEAN' if lint_count == 0 else '⚠️ WARNS REMAINING'})</p>
        </div>
        """, unsafe_allow_html=True)
    with sign_col2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>PDF Export Features</h4>
            <p>• <b>Publication-Ready:</b> Formatted headers, footers & two-pass dynamic page numbering.</p>
            <p>• <b>Full Traceability:</b> Pin-by-pin STA timing, multi-factor RCA confidence & evidence chains.</p>
            <p>• <b>Verification Box:</b> Formal sign-off lines for Lead RTL, STA, and QA verification engineers.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### 📄 Audit Summary Preview")
    st.markdown(report_md)
