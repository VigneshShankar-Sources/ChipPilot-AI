"""
ChipPilot AI - Engineering Knowledge Graph (EKG) Engine
Models multi-domain RTL entities, EDA findings, and physical timing paths as an attributed multigraph.
"""

import networkx as nx
import os
from typing import Dict, List, Any, Optional

class EngineeringKnowledgeGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def build_graph(self, parsed_rtl: List[Dict[str, Any]], lint_findings: List[Dict[str, Any]],
                    synth_data: Dict[str, Any], timing_data: Dict[str, Any]):
        """Constructs graph entities and establishes multi-domain cross-tool relationships."""
        self.graph.clear()

        # 1. Ingest RTL Hierarchy
        for file_entry in parsed_rtl:
            file_path = file_entry.get("file_path", "")
            base_fname = os.path.basename(file_path)
            file_node = f"file:{base_fname}"
            self.graph.add_node(file_node, entity_type="File", path=file_path, name=base_fname)

            for mod in file_entry.get("modules", []):
                mod_node = f"module:{mod['name']}"
                self.graph.add_node(
                    mod_node,
                    entity_type="Module",
                    name=mod["name"],
                    file=file_path,
                    start_line=mod.get("start_line", 1),
                    end_line=mod.get("end_line", 1)
                )
                self.graph.add_edge(file_node, mod_node, relationship="CONTAINS")

                # Ports
                for port in mod.get("ports", []):
                    port_node = f"port:{mod['name']}.{port['name']}"
                    p_attrs = {k: v for k, v in port.items()}
                    self.graph.add_node(port_node, entity_type="Port", **p_attrs)
                    self.graph.add_edge(mod_node, port_node, relationship="HAS_PORT")

                # Registers
                for reg in mod.get("registers", []):
                    reg_node = f"reg:{mod['name']}.{reg['name']}"
                    r_attrs = {k: v for k, v in reg.items() if k != "type"}
                    self.graph.add_node(reg_node, entity_type="Register", signal_type="reg", **r_attrs)
                    self.graph.add_edge(mod_node, reg_node, relationship="CONTAINS_REG")

                # Clocks & Resets
                for clk in mod.get("clocks", []):
                    clk_node = f"clock:{mod['name']}.{clk}"
                    self.graph.add_node(clk_node, entity_type="Clock", name=clk)
                    self.graph.add_edge(mod_node, clk_node, relationship="DRIVEN_BY_CLOCK")

                for rst in mod.get("resets", []):
                    rst_node = f"reset:{mod['name']}.{rst}"
                    self.graph.add_node(rst_node, entity_type="Reset", name=rst)
                    self.graph.add_edge(mod_node, rst_node, relationship="RESET_BY")

                # Submodule Instantiations
                for inst in mod.get("instantiations", []):
                    inst_node = f"instance:{mod['name']}.{inst['instance_name']}"
                    self.graph.add_node(inst_node, entity_type="Instance", target_module=inst["submodule"], name=inst["instance_name"])
                    self.graph.add_edge(mod_node, inst_node, relationship="INSTANTIATES")

        # 2. Ingest Lint Violations
        for idx, lint in enumerate(lint_findings):
            lint_node = f"lint:{lint.get('code', 'GEN')}_{idx}"
            l_attrs = {k: v for k, v in lint.items() if k != "type"}
            self.graph.add_node(lint_node, entity_type="LintFinding", finding_type="LINT", **l_attrs)
            
            base_fname = os.path.basename(lint.get("file", ""))
            matched_file = f"file:{base_fname}"
            if self.graph.has_node(matched_file):
                self.graph.add_edge(matched_file, lint_node, relationship="HAS_VIOLATION")

        # 3. Ingest Synthesis Cell Distribution
        synth_stats = synth_data.get("statistics", {})
        for cell_type, count in synth_stats.get("cells", {}).items():
            cell_node = f"synth_cell:{cell_type}"
            self.graph.add_node(cell_node, entity_type="SynthesisCell", cell_type=cell_type, count=count)

        # 4. Ingest Timing Paths & Correlate
        for idx, path in enumerate(timing_data.get("timing_paths", [])):
            path_node = f"timing_path:{idx}"
            p_attrs = {k: v for k, v in path.items()}
            self.graph.add_node(path_node, entity_type="TimingPath", **p_attrs)
            
            if path.get("is_violation", False):
                # Search for matching registers or ports
                for node, data in list(self.graph.nodes(data=True)):
                    e_type = data.get("entity_type", "")
                    if e_type in ["Register", "Port"]:
                        var_name = data.get("name", "")
                        if var_name and var_name in path.get("startpoint", ""):
                            self.graph.add_edge(node, path_node, relationship="ORIGINATES_PATH")
                        if var_name and var_name in path.get("endpoint", ""):
                            self.graph.add_edge(path_node, node, relationship="TERMINATES_PATH")

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns node count breakdown by entity type."""
        type_counts = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("entity_type", "Unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "entity_breakdown": type_counts
        }

    def get_related_subgraph(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Extracts localized subgraph neighborhood around a target node."""
        if not self.graph.has_node(entity_id):
            return {"nodes": [], "edges": []}

        undirected = self.graph.to_undirected()
        sub_nodes = list(nx.single_source_shortest_path_length(undirected, entity_id, cutoff=depth).keys())
        subg = self.graph.subgraph(sub_nodes)

        nodes_out = [{"id": n, **subg.nodes[n]} for n in subg.nodes()]
        edges_out = []
        for u, v, k in subg.edges(keys=True):
            edge_data = subg.edges[u, v, k]
            edges_out.append({
                "source": u,
                "target": v,
                "relationship": edge_data.get("relationship", "RELATED_TO")
            })

        return {"nodes": nodes_out, "edges": edges_out}

    def get_all_nodes_and_edges(self) -> Dict[str, Any]:
        """Returns all graph elements formatted for interactive visualization."""
        nodes = [{"id": n, "label": n.split(":")[-1], **self.graph.nodes[n]} for n in self.graph.nodes()]
        edges = [{"source": u, "target": v, "label": self.graph.edges[u, v, k].get("relationship", "")}
                 for u, v, k in self.graph.edges(keys=True)]
        return {"nodes": nodes, "edges": edges}
