"""
ChipPilot AI - Deterministic Root Cause Analysis (RCA) Engine
Correlates findings across Verilator lint, Yosys synthesis, OpenSTA timing, and AST structures
using a deterministic, interpretable scoring model.
"""

import os
from typing import List, Dict, Any
from knowledge_graph.graph_engine import EngineeringKnowledgeGraph

class RootCauseAnalyzer:
    def __init__(self, ekg: EngineeringKnowledgeGraph, weights: Dict[str, float] = None):
        self.ekg = ekg
        self.weights = weights or {
            "evidence_strength": 0.25,
            "cross_tool_correlation": 0.30,
            "rtl_relevance": 0.20,
            "timing_relevance": 0.15,
            "pattern_relevance": 0.10
        }

    def analyze_root_causes(self, parsed_rtl: List[Dict[str, Any]], lint_findings: List[Dict[str, Any]],
                            timing_data: Dict[str, Any], synth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ranks candidate root causes with mathematical confidence scores and evidence chains."""
        candidate_causes = []
        worst_slack = timing_data.get("worst_slack", 0.0)
        has_timing_violation = worst_slack < 0.0
        synth_stats = synth_data.get("statistics", {})

        # 1. Evaluate Lint Antipatterns (e.g. Latch, Width, Comb Delay)
        for lint in lint_findings:
            e_strength = 1.0 if lint["severity"] == "ERROR" else 0.6
            c_xtool = 0.0
            r_rtl = 0.5
            t_timing = 0.0
            p_pattern = 0.3

            evidence = [
                f"[Verilator:{os.path.basename(lint['file'])}:{lint['line']}] {lint['severity']} [{lint['code']}]: {lint['message']}"
            ]

            # Cross-tool correlation check
            if lint["code"] in ["LATCH", "POTENTIAL_LATCH_INFERRED", "INCOMPLETE_CASE_STATEMENT"]:
                p_pattern = 0.95
                if synth_stats.get("cells", {}).get("$_DLATCH_P_", 0) > 0:
                    c_xtool += 0.5
                    evidence.append(f"[Yosys:Synthesis] Inferred {synth_stats['cells']['$_DLATCH_P_']} latch cells ($_DLATCH_P_).")
                if has_timing_violation:
                    c_xtool += 0.5
                    t_timing = min(1.0, abs(worst_slack) / 10.0)
                    evidence.append(f"[OpenSTA:Timing] Negative setup slack observed (WNS = {worst_slack:.2f} ns). Latch transparent phase stretches data arrival.")

            elif lint["code"] in ["WIDTH", "BITWIDTH_MISMATCH"]:
                p_pattern = 0.80
                evidence.append("Bit-width mismatch can cause unintended arithmetic sign extension or high-order bit truncation.")

            score = (
                self.weights["evidence_strength"] * e_strength +
                self.weights["cross_tool_correlation"] * c_xtool +
                self.weights["rtl_relevance"] * r_rtl +
                self.weights["timing_relevance"] * t_timing +
                self.weights["pattern_relevance"] * p_pattern
            )

            candidate_causes.append({
                "title": f"Hardware Defect: {lint['code']} in {os.path.basename(lint['file'])}:{lint['line']}",
                "confidence_score": round(min(0.99, max(0.10, score)), 3),
                "severity": lint["severity"],
                "file": lint["file"],
                "line": lint["line"],
                "evidence": evidence,
                "hypothesis": f"The construct at line {lint['line']} introduces structural logic flaws or inferred latches, degrading functional safety and path slack."
            })

        # 2. Evaluate AST Structural Antipatterns
        for file_entry in parsed_rtl:
            for mod in file_entry.get("modules", []):
                for ap in mod.get("antipatterns", []):
                    # Check if already covered by lint findings
                    if any(c.get("line") == ap.get("line") and os.path.basename(c.get("file", "")) == os.path.basename(ap.get("file", "")) for c in candidate_causes):
                        continue

                    e_strength = 0.8 if ap["severity"] == "ERROR" else 0.5
                    c_xtool = 0.3 if has_timing_violation else 0.1
                    r_rtl = 0.9
                    t_timing = min(1.0, abs(worst_slack) / 10.0) if has_timing_violation else 0.0
                    p_pattern = 0.85

                    evidence = [
                        f"[AST Scanner:{os.path.basename(ap['file'])}:{ap['line']}] {ap['type']}: {ap['description']}"
                    ]
                    if has_timing_violation and "LATCH" in ap["type"]:
                        evidence.append(f"[OpenSTA:Timing] Design timing violated (Worst Slack = {worst_slack:.2f} ns).")

                    score = (
                        self.weights["evidence_strength"] * e_strength +
                        self.weights["cross_tool_correlation"] * c_xtool +
                        self.weights["rtl_relevance"] * r_rtl +
                        self.weights["timing_relevance"] * t_timing +
                        self.weights["pattern_relevance"] * p_pattern
                    )

                    candidate_causes.append({
                        "title": f"Structural Hazard: {ap['type']} in {mod['name']}",
                        "confidence_score": round(min(0.99, max(0.10, score)), 3),
                        "severity": ap["severity"],
                        "file": ap["file"],
                        "line": ap["line"],
                        "evidence": evidence,
                        "hypothesis": ap["description"]
                    })

        # 3. Evaluate Setup Timing Path Violations
        if has_timing_violation:
            for path in timing_data.get("timing_paths", []):
                if path.get("is_violation", False):
                    evidence = [
                        f"[OpenSTA:Timing] Path: {path['startpoint']} -> {path['endpoint']}",
                        f"[OpenSTA:Timing] Data Arrival: {path.get('data_arrival_time', 0.0):.4f} ns, Data Required: {path.get('data_required_time', 0.0):.4f} ns",
                        f"[OpenSTA:Timing] Setup Slack: {path['slack']:.4f} ns (VIOLATION)"
                    ]
                    candidate_causes.append({
                        "title": f"Critical Setup Timing Violation ({path['startpoint']} -> {path['endpoint']})",
                        "confidence_score": 0.92,
                        "severity": "ERROR",
                        "file": path["startpoint"].split(".")[0] if "." in path["startpoint"] else "top",
                        "line": 1,
                        "evidence": evidence,
                        "hypothesis": "Excessive combinational logic depth between registers exceeds the clock period constraint."
                    })

        # Sort candidate causes descending by confidence score
        candidate_causes.sort(key=lambda x: x["confidence_score"], reverse=True)
        return candidate_causes
