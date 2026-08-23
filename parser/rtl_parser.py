"""
ChipPilot AI - Advanced RTL & Structural AST Parser
Extracts module hierarchy, ports, registers, wires, clocks, resets, 
and detects structural design antipatterns with exact line-number tracking.
"""

import re
import os
from typing import Dict, List, Any, Optional

KEYWORDS = {
    "input", "output", "inout", "wire", "reg", "logic", "integer", "signed", "unsigned",
    "module", "endmodule", "always", "assign", "begin", "end", "case", "endcase",
    "if", "else", "posedge", "negedge"
}

class RTLParser:
    def __init__(self):
        self.module_pattern = re.compile(r'\bmodule\s+([a-zA-Z_][a-zA-Z0-9_$]*)\s*(?:#\s*\((.*?)\))?\s*\((.*?)\);', re.DOTALL)
        self.port_item_pattern = re.compile(r'\b(input|output|inout)\s+(?:wire|reg|logic)?\s*(?:signed|unsigned)?\s*(?:\[(\d+):(\d+)\])?\s*([a-zA-Z_][a-zA-Z0-9_$]*)', re.MULTILINE)
        self.reg_pattern = re.compile(r'\breg\s+(?:signed|unsigned)?\s*(?:\[(\d+):(\d+)\])?\s*([a-zA-Z_][a-zA-Z0-9_$]*)\s*(?:\[\d+:\d+\])?\s*;', re.MULTILINE)
        self.wire_pattern = re.compile(r'\bwire\s+(?:signed|unsigned)?\s*(?:\[(\d+):(\d+)\])?\s*([a-zA-Z_][a-zA-Z0-9_$]*)\s*;', re.MULTILINE)
        self.always_pattern = re.compile(r'always\s*@\s*\((.*?)\)\s*begin(?:\s*:\s*[a-zA-Z_][a-zA-Z0-9_]*)?(.*?)end\b', re.DOTALL)
        self.instantiation_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_$]*)\s+(?:#\s*\(.*?\)\s+)?([a-zA-Z_][a-zA-Z0-9_$]*)\s*\((.*?)\);', re.DOTALL)

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parses an RTL file and returns a rich AST dictionary."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"RTL file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()

        line_offsets = [0]
        for line in raw_content.splitlines(True):
            line_offsets.append(line_offsets[-1] + len(line))

        def get_line_num(char_pos: int) -> int:
            for idx, offset in enumerate(line_offsets):
                if offset > char_pos:
                    return max(1, idx)
            return len(line_offsets)

        clean_content = re.sub(r'//.*', lambda m: ' ' * len(m.group(0)), raw_content)
        clean_content = re.sub(r'/\*.*?\*/', lambda m: ' ' * len(m.group(0)), clean_content, flags=re.DOTALL)

        modules_data = []
        for match in self.module_pattern.finditer(clean_content):
            module_name = match.group(1)
            raw_params = match.group(2) or ""
            raw_ports = match.group(3) or ""
            module_body_start = match.end()
            start_line = get_line_num(match.start())
            
            endmodule_pos = clean_content.find("endmodule", module_body_start)
            module_body = clean_content[module_body_start:endmodule_pos] if endmodule_pos != -1 else clean_content[module_body_start:]
            end_line = get_line_num(endmodule_pos if endmodule_pos != -1 else len(clean_content))

            parsed_module = self._parse_module_body(
                module_name, raw_ports, module_body, file_path, start_line, end_line, get_line_num, module_body_start
            )
            modules_data.append(parsed_module)

        return {
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "modules": modules_data
        }

    def _parse_module_body(self, name: str, raw_ports: str, body: str, file_path: str,
                           start_line: int, end_line: int, get_line_num, body_offset: int) -> Dict[str, Any]:
        ports = self._extract_ports(raw_ports, body)
        registers = self._extract_signals(self.reg_pattern, body, "reg")
        wires = self._extract_signals(self.wire_pattern, body, "wire")
        clocks, resets = self._detect_clocks_and_resets(ports, body)
        always_blocks = self._extract_always_blocks(body, body_offset, get_line_num)
        instantiations = self._extract_instantiations(body, name)
        antipatterns = self._detect_structural_antipatterns(body, always_blocks, ports, registers, file_path)

        return {
            "name": name,
            "file": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "ports": ports,
            "registers": registers,
            "wires": wires,
            "clocks": clocks,
            "resets": resets,
            "always_blocks": always_blocks,
            "instantiations": instantiations,
            "antipatterns": antipatterns
        }

    def _extract_ports(self, raw_ports: str, body: str) -> List[Dict[str, Any]]:
        ports = []
        combined_declarations = raw_ports + "\n" + body
        for match in self.port_item_pattern.finditer(combined_declarations):
            direction = match.group(1)
            msb = int(match.group(2)) if match.group(2) is not None else 0
            lsb = int(match.group(3)) if match.group(3) is not None else 0
            width = abs(msb - lsb) + 1 if match.group(2) is not None else 1
            port_name = match.group(4).strip()
            
            if port_name and port_name not in KEYWORDS and not any(p['name'] == port_name for p in ports):
                ports.append({
                    "name": port_name,
                    "direction": direction,
                    "width": width,
                    "msb": msb,
                    "lsb": lsb
                })
        return ports

    def _extract_signals(self, pattern: re.Pattern, body: str, sig_type: str) -> List[Dict[str, Any]]:
        signals = []
        for match in pattern.finditer(body):
            msb = int(match.group(1)) if match.group(1) is not None else 0
            lsb = int(match.group(2)) if match.group(2) is not None else 0
            width = abs(msb - lsb) + 1 if match.group(1) is not None else 1
            sig_name = match.group(3).strip()
            if sig_name and sig_name not in KEYWORDS and not any(s['name'] == sig_name for s in signals):
                signals.append({
                    "name": sig_name,
                    "type": sig_type,
                    "width": width,
                    "msb": msb,
                    "lsb": lsb
                })
        return signals

    def _detect_clocks_and_resets(self, ports: List[Dict[str, Any]], body: str) -> (List[str], List[str]):
        clocks = []
        resets = []
        for port in ports:
            pname = port["name"].lower()
            if any(k in pname for k in ["clk", "clock"]):
                clocks.append(port["name"])
            if any(k in pname for k in ["rst", "reset"]):
                resets.append(port["name"])
        
        posedge_clks = re.findall(r'posedge\s+([a-zA-Z_][a-zA-Z0-9_$]*)', body)
        for c in posedge_clks:
            if c not in clocks and c not in KEYWORDS:
                clocks.append(c)
        return clocks, resets

    def _extract_always_blocks(self, body: str, body_offset: int, get_line_num) -> List[Dict[str, Any]]:
        blocks = []
        for match in self.always_pattern.finditer(body):
            sensitivity = match.group(1).strip()
            code = match.group(2).strip()
            line_no = get_line_num(body_offset + match.start())
            is_sequential = "posedge" in sensitivity or "negedge" in sensitivity
            blocks.append({
                "line": line_no,
                "sensitivity": sensitivity,
                "is_sequential": is_sequential,
                "code": code
            })
        return blocks

    def _extract_instantiations(self, body: str, current_module: str) -> List[Dict[str, Any]]:
        instantiations = []
        primitives = {"and", "nand", "or", "nor", "xor", "xnor", "buf", "not", "reg", "wire", "always", "initial"}
        for match in self.instantiation_pattern.finditer(body):
            mod_type = match.group(1)
            inst_name = match.group(2)
            ports_mapping = match.group(3)
            if mod_type not in primitives and mod_type not in KEYWORDS and mod_type != current_module:
                instantiations.append({
                    "submodule": mod_type,
                    "instance_name": inst_name,
                    "port_map_raw": ports_mapping.strip()
                })
        return instantiations

    def _detect_structural_antipatterns(self, body: str, always_blocks: List[Dict[str, Any]],
                                        ports: List[Dict[str, Any]], registers: List[Dict[str, Any]],
                                        file_path: str) -> List[Dict[str, Any]]:
        antipatterns = []
        
        # 1. Latch Inference
        for block in always_blocks:
            if not block["is_sequential"]:
                if "if" in block["code"] and "else" not in block["code"]:
                    antipatterns.append({
                        "type": "POTENTIAL_LATCH_INFERRED",
                        "severity": "WARNING",
                        "line": block["line"],
                        "file": file_path,
                        "description": "Combinational always block contains 'if' branch without terminal 'else'. May infer level-sensitive latch."
                    })
                if "case" in block["code"] and "default" not in block["code"]:
                    antipatterns.append({
                        "type": "INCOMPLETE_CASE_STATEMENT",
                        "severity": "WARNING",
                        "line": block["line"],
                        "file": file_path,
                        "description": "Combinational case statement lacks 'default' clause. High risk of unwanted latch inference."
                    })

        # 2. Blocking assignment in sequential logic
        for block in always_blocks:
            if block["is_sequential"]:
                if re.search(r'(?<![<!=])=(?!=)', block["code"]):
                    antipatterns.append({
                        "type": "BLOCKING_ASSIGNMENT_IN_SEQUENTIAL",
                        "severity": "ERROR",
                        "line": block["line"],
                        "file": file_path,
                        "description": "Blocking assignment (=) used in clocked always block. Risk of simulation-synthesis race conditions."
                    })

        # 3. Missing reset in sequential block
        for block in always_blocks:
            if block["is_sequential"]:
                if "rst" not in block["sensitivity"].lower() and "reset" not in block["sensitivity"].lower():
                    if "rst" not in block["code"].lower() and "reset" not in block["code"].lower():
                        antipatterns.append({
                            "type": "MISSING_ASYNC_RESET",
                            "severity": "WARNING",
                            "line": block["line"],
                            "file": file_path,
                            "description": "Sequential always block does not include reset logic. Registers will power-up in undefined state."
                        })

        # 4. Unused Registers / Nets
        for reg in registers:
            rname = reg["name"]
            if rname not in KEYWORDS:
                occurrences = len(re.findall(r'\b' + re.escape(rname) + r'\b', body))
                if occurrences <= 1:
                    antipatterns.append({
                        "type": "UNUSED_NET",
                        "severity": "INFO",
                        "line": 0,
                        "file": file_path,
                        "description": f"Declared register '{rname}' is never referenced in module logic."
                    })

        return antipatterns
