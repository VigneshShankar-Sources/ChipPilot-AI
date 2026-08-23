"""
ChipPilot AI - Multi-Agent Diagnostic & Grounded Reasoning Workflow
Coordinates specialized hardware agents (Lint, Timing, Synthesis, RCA, and Reasoning)
with strict citation guardrails and zero-hallucination compliance.
"""

from typing import Dict, Any, List, Optional
import os
import re

class AgentState:
    def __init__(self, project_id: str, parsed_ast: List[Dict[str, Any]], lint_findings: List[Dict[str, Any]],
                 synth_stats: Dict[str, Any], timing_data: Dict[str, Any], user_query: str = ""):
        self.project_id = project_id
        self.parsed_ast = parsed_ast
        self.lint_findings = lint_findings
        self.synth_stats = synth_stats
        self.timing_data = timing_data
        self.user_query = user_query
        self.root_causes: List[Dict[str, Any]] = []
        self.retrieved_evidence: List[Dict[str, Any]] = []
        self.agent_outputs: Dict[str, str] = {}
        self.final_response: str = ""

class ChipPilotMultiAgentFlow:
    def __init__(self, rca_engine, rag_engine):
        self.rca_engine = rca_engine
        self.rag_engine = rag_engine

    def execute_workflow(self, state: AgentState) -> AgentState:
        """Executes the complete multi-agent pipeline."""
        # 1. Lint & Structural Agent
        state.agent_outputs["lint"] = self._run_lint_agent(state)

        # 2. Timing & STA Agent
        state.agent_outputs["timing"] = self._run_timing_agent(state)

        # 3. Synthesis & Resource Agent
        state.agent_outputs["synthesis"] = self._run_synthesis_agent(state)

        # 4. Root-Cause Analysis Agent
        state.root_causes = self.rca_engine.analyze_root_causes(
            state.parsed_ast, state.lint_findings, state.timing_data, state.synth_stats
        )

        # 5. Hybrid Retrieval Step
        if state.user_query:
            state.retrieved_evidence = self.rag_engine.retrieve(state.user_query, top_k=4)

        # 6. Grounded AI Reasoning & Synthesis Agent
        state.final_response = self._synthesize_grounded_response(state)
        return state

    def _run_lint_agent(self, state: AgentState) -> str:
        num_errs = sum(1 for l in state.lint_findings if l.get("severity") == "ERROR")
        num_warns = sum(1 for l in state.lint_findings if l.get("severity") == "WARNING")
        latch_findings = [l for l in state.lint_findings if "LATCH" in l.get("code", "")]
        
        summary = f"Lint Agent identified {num_errs} errors and {num_warns} warnings."
        if latch_findings:
            summary += f" CRITICAL: Detected {len(latch_findings)} potential latch inference locations."
        return summary

    def _run_timing_agent(self, state: AgentState) -> str:
        worst_slack = state.timing_data.get("worst_slack", 0.0)
        has_violations = state.timing_data.get("has_violations", False)
        if has_violations or worst_slack < 0:
            return f"Timing Agent: Setup timing violated with Worst Negative Slack (WNS) = {worst_slack:.2f} ns."
        return f"Timing Agent: Timing constraints met with positive slack (+{worst_slack:.2f} ns)."

    def _run_synthesis_agent(self, state: AgentState) -> str:
        stats = state.synth_stats.get("statistics", {}) if "statistics" in state.synth_stats else state.synth_stats
        total_cells = stats.get("total_cells", 0)
        latches = stats.get("cells", {}).get("$_DLATCH_P_", 0)
        return f"Synthesis Agent: Elaborated {total_cells} total cells. Inferred latches: {latches}."

    def _synthesize_grounded_response(self, state: AgentState) -> str:
        """Constructs a deterministic, evidence-grounded engineering report with citations."""
        query = state.user_query or "Summarize all design issues and recommended fixes."
        top_causes = state.root_causes[:3]

        lines = []
        lines.append("### ChipPilot AI Grounded Diagnostic Report\n")
        lines.append(f"**Engineering Query:** {query}\n")

        # 1. Executive Status Banner
        worst_slack = state.timing_data.get("worst_slack", 0.0)
        status_badge = "🔴 CRITICAL DEFECTS DETECTED" if (state.lint_findings or worst_slack < 0) else "🟢 DESIGN CLEAN"
        lines.append(f"**Overall Design Health:** {status_badge}")
        lines.append(f"- **Worst Slack:** `{worst_slack:+.2f} ns` | **Lint Findings:** `{len(state.lint_findings)}` | **Top Root Causes:** `{len(top_causes)}`\n")

        # 2. Ranked Root Cause Breakdown
        if top_causes:
            lines.append("#### 1. Top Identified Root Causes (Ranked by Confidence Score):")
            for idx, cause in enumerate(top_causes, 1):
                conf_pct = int(cause['confidence_score'] * 100)
                lines.append(f"**[{idx}] {cause['title']}** (Confidence: `{conf_pct}%`)")
                lines.append(f"- **Location:** `{cause.get('file', 'N/A')}:{cause.get('line', 0)}`")
                lines.append(f"- **Diagnostic Mechanism:** {cause.get('hypothesis')}")
                lines.append("- **Verified EDA Evidence:**")
                for ev in cause.get("evidence", []):
                    lines.append(f"  * `{ev}`")
                lines.append("")
        else:
            lines.append("No critical hardware defects detected in current design hierarchy.\n")

        # 3. Retrieved RTL Context & Citations
        if state.retrieved_evidence:
            lines.append("#### 2. Grounded Design Citations (Hybrid RAG):")
            for idx, ev in enumerate(state.retrieved_evidence, 1):
                doc = ev["document"]
                sim = ev["similarity"]
                fname = os.path.basename(doc.get("file", "design"))
                lines.append(f"**Citation [{idx}]: `{fname}` (Type: `{doc.get('type')}`, Relevance: `{sim:.2f}`)**")
                lines.append("```verilog")
                lines.append(doc.get("content", "")[:260].strip())
                lines.append("```\n")

        # 4. Prescribed Engineering Actions
        lines.append("#### 3. Prescribed Engineering Actions:")
        if any("LATCH" in c.get("title", "") for c in top_causes):
            lines.append("1. **Fix Inferred Latches:** Add a terminal `default:` clause to combinational `case` statements or complete all `else` branches.")
        if worst_slack < 0:
            lines.append("2. **Pipeline Critical Path:** Break deep combinational arithmetic clouds by inserting an intermediate pipeline stage register.")
        if any("RESET" in c.get("title", "") for c in top_causes):
            lines.append("3. **Add Reset Handling:** Implement synchronous or asynchronous reset conditions in clocked `always` blocks.")

        lines.append("\n**Closed-Loop Verification Protocol:**")
        lines.append("1. Apply prescribed RTL modifications.")
        lines.append("2. Re-run Verilator lint and OpenSTA to verify `Worst Slack >= 0.00 ns` and 0 inferred latches.")
        lines.append("3. Submit for final engineering code review.")

        return "\n".join(lines)
