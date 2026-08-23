"""
ChipPilot AI - Closed-Loop Verification Sandbox
Performs automated before-and-after EDA execution to rigorously measure PPA improvement.
"""

from typing import Dict, Any, List
import os
from parser.rtl_parser import RTLParser
from eda.orchestrator import EDAOrchestrator
from eda.report_normalizer import ReportNormalizer

class VerificationSandbox:
    def __init__(self, workspace_dir: str = "./eda_workspace"):
        self.parser = RTLParser()
        self.orchestrator = EDAOrchestrator(workspace_dir)
        self.normalizer = ReportNormalizer()

    def run_comparative_verification(self, top_module: str, baseline_files: List[str],
                                     fixed_files: List[str]) -> Dict[str, Any]:
        """Runs the complete EDA suite on baseline vs fixed RTL and computes delta metrics."""
        # 1. Evaluate Baseline Design
        base_lint = self.orchestrator.run_verilator_lint(baseline_files[0])
        base_synth = self.orchestrator.run_yosys_synthesis(top_module, baseline_files)
        base_timing = self.orchestrator.run_opensta_timing(top_module, base_synth.get("netlist_file", ""))

        base_lint_findings = self.normalizer.normalize_verilator(base_lint.get("stderr", ""), base_lint.get("stdout", ""))
        base_synth_data = self.normalizer.normalize_yosys(base_synth.get("stdout", ""))
        base_timing_data = self.normalizer.normalize_opensta(base_timing.get("stdout", ""))

        # 2. Evaluate Fixed Design
        fix_lint = self.orchestrator.run_verilator_lint(fixed_files[0])
        fix_synth = self.orchestrator.run_yosys_synthesis(top_module, fixed_files)
        fix_timing = self.orchestrator.run_opensta_timing(top_module, fix_synth.get("netlist_file", ""))

        fix_lint_findings = self.normalizer.normalize_verilator(fix_lint.get("stderr", ""), fix_lint.get("stdout", ""))
        fix_synth_data = self.normalizer.normalize_yosys(fix_synth.get("stdout", ""))
        fix_timing_data = self.normalizer.normalize_opensta(fix_timing.get("stdout", ""))

        # 3. Compute Quantitative Deltas
        base_slack = base_timing_data.get("worst_slack", 0.0)
        fix_slack = fix_timing_data.get("worst_slack", 0.0)
        delta_slack = round(fix_slack - base_slack, 3)

        base_cells = base_synth_data.get("statistics", {}).get("total_cells", 0)
        fix_cells = fix_synth_data.get("statistics", {}).get("total_cells", 0)
        delta_cells = fix_cells - base_cells

        base_latches = base_synth_data.get("statistics", {}).get("cells", {}).get("$_DLATCH_P_", 0)
        fix_latches = fix_synth_data.get("statistics", {}).get("cells", {}).get("$_DLATCH_P_", 0)
        delta_latches = fix_latches - base_latches

        delta_lint = len(fix_lint_findings) - len(base_lint_findings)

        is_verified = (fix_slack >= 0.0) and (len(fix_lint_findings) == 0) and (fix_latches == 0)

        return {
            "is_verified": is_verified,
            "status": "PASSED" if is_verified else "FAILED",
            "baseline": {
                "worst_slack": base_slack,
                "total_cells": base_cells,
                "inferred_latches": base_latches,
                "lint_violations": len(base_lint_findings)
            },
            "fixed": {
                "worst_slack": fix_slack,
                "total_cells": fix_cells,
                "inferred_latches": fix_latches,
                "lint_violations": len(fix_lint_findings)
            },
            "delta": {
                "slack_improvement_ns": delta_slack,
                "cell_count_change": delta_cells,
                "latches_eliminated": abs(delta_latches) if delta_latches < 0 else 0,
                "lint_issues_resolved": abs(delta_lint) if delta_lint < 0 else 0
            }
        }
