"""
ChipPilot AI - Report Normalizer Layer
Converts raw log streams from Verilator, Yosys, and OpenSTA into structured JSON findings.
"""

import re
from typing import Dict, List, Any

class ReportNormalizer:
    def normalize_verilator(self, raw_stderr: str, raw_stdout: str) -> List[Dict[str, Any]]:
        """Parses Verilator %Warning and %Error log lines."""
        findings = []
        combined = raw_stderr + "\n" + raw_stdout
        pattern = re.compile(r'%(Warning|Error)(?:-([A-Z0-9_]+))?:\s*([^:]+):(\d+):(?:\d+:)?\s*(.*)')
        
        for line in combined.splitlines():
            line_str = line.strip()
            match = pattern.match(line_str)
            if match:
                severity = match.group(1).upper()
                rule_code = match.group(2) or "GENERIC"
                file_path = match.group(3).strip()
                line_no = int(match.group(4))
                message = match.group(5).strip()
                
                findings.append({
                    "tool": "Verilator",
                    "type": "LINT",
                    "severity": severity,
                    "code": rule_code,
                    "file": file_path,
                    "line": line_no,
                    "message": message,
                    "evidence": line_str
                })
        return findings

    def normalize_yosys(self, raw_stdout: str) -> Dict[str, Any]:
        """Extracts synthesis cell counts, wire statistics, and warnings from Yosys."""
        findings = []
        stats = {"cells": {}, "total_cells": 0, "wires": 0}
        
        # Parse Warnings and Errors
        warn_pattern = re.compile(r'Warning:\s*(.*)')
        for match in warn_pattern.finditer(raw_stdout):
            findings.append({
                "tool": "Yosys",
                "type": "SYNTHESIS_WARNING",
                "severity": "WARNING",
                "code": "SYNTH_WARN",
                "file": "synthesis",
                "line": 0,
                "message": match.group(1).strip(),
                "evidence": match.group(0)
            })

        # Parse Statistics Section
        stat_section = re.search(r'Printing statistics\.(.*?)===', raw_stdout, re.DOTALL)
        if stat_section:
            stat_text = stat_section.group(1)
            for line in stat_text.splitlines():
                line = line.strip()
                cell_match = re.match(r'(\$_[A-Z0-9_]+|[a-zA-Z0-9_]+)\s+(\d+)', line)
                if cell_match and not line.startswith("Number of"):
                    stats["cells"][cell_match.group(1)] = int(cell_match.group(2))
                if "Number of cells:" in line:
                    num_m = re.search(r'\d+', line)
                    if num_m:
                        stats["total_cells"] = int(num_m.group())
                if "Number of wires:" in line:
                    num_w = re.search(r'\d+', line)
                    if num_w:
                        stats["wires"] = int(num_w.group())

        return {
            "findings": findings,
            "statistics": stats
        }

    def normalize_opensta(self, raw_stdout: str) -> Dict[str, Any]:
        """Parses OpenSTA timing reports, slack, critical paths, and endpoint delays."""
        timing_paths = []
        worst_slack = 0.0
        
        # Match worst slack lines: worst slack max = -1.84
        ws_match = re.search(r'worst slack (?:max|setup)\s*=\s*([-+]?\d+\.\d+)', raw_stdout, re.IGNORECASE)
        if ws_match:
            worst_slack = float(ws_match.group(1))

        # Extract timing path details
        path_blocks = raw_stdout.split("Startpoint:")
        for block in path_blocks[1:]:
            lines = block.splitlines()
            startpoint = lines[0].strip().split()[0] if lines else "Unknown"
            endpoint = "Unknown"
            slack = worst_slack
            data_arrival = 0.0
            data_required = 0.0
            
            for line in lines:
                if "Endpoint:" in line:
                    endpoint = line.split("Endpoint:")[1].strip().split()[0]
                if "slack (" in line.lower() or "slack :" in line.lower() or line.strip().startswith("slack"):
                    slack_match = re.search(r'([-+]?\d+\.\d+)', line)
                    if slack_match:
                        slack = float(slack_match.group(1))
                if "data arrival time" in line:
                    arr_match = re.search(r'([-+]?\d+\.\d+)', line)
                    if arr_match:
                        data_arrival = float(arr_match.group(1))
                if "data required time" in line:
                    req_match = re.search(r'([-+]?\d+\.\d+)', line)
                    if req_match:
                        data_required = float(req_match.group(1))

            timing_paths.append({
                "startpoint": startpoint,
                "endpoint": endpoint,
                "slack": slack,
                "data_arrival_time": data_arrival,
                "data_required_time": data_required,
                "is_violation": slack < 0.0,
                "raw_path_dump": ("Startpoint: " + block).strip()
            })

        return {
            "worst_slack": worst_slack,
            "timing_paths": timing_paths,
            "has_violations": worst_slack < 0.0
        }
