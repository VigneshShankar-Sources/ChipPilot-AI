"""
ChipPilot AI - Hybrid RAG & Semantic Retrieval Engine
AST-guided chunking, dense vector indexing via FAISS/SentenceTransformers, 
and metadata/graph-neighborhood constrained similarity retrieval.
"""

import numpy as np
import os
from typing import List, Dict, Any, Optional

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAVE_FAISS_ST = True
except ImportError:
    HAVE_FAISS_ST = False

class RetrievalEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.have_faiss = HAVE_FAISS_ST
        self.documents: List[Dict[str, Any]] = []
        self.doc_embeddings: Optional[np.ndarray] = None
        self.encoder = None
        self.index = None
        self.dimension = 384

        if self.have_faiss:
            try:
                self.encoder = SentenceTransformer(model_name)
                self.index = faiss.IndexFlatIP(self.dimension)
            except Exception:
                self.have_faiss = False

    def index_project(self, parsed_rtl: List[Dict[str, Any]], reports: List[Dict[str, Any]],
                      timing_paths: List[Dict[str, Any]] = None):
        """Indexes RTL AST blocks, EDA findings, and timing paths into the vector store."""
        self.documents.clear()
        doc_texts = []

        # 1. Chunk RTL Modules, Ports, and Always Blocks
        for file_entry in parsed_rtl:
            file_path = file_entry.get("file_path", "")
            base_fname = os.path.basename(file_path)

            for mod in file_entry.get("modules", []):
                # Header Chunk
                port_names = ", ".join([p["name"] for p in mod.get("ports", [])])
                header_text = f"Module: {mod['name']} in file {base_fname}\nPorts: {port_names}\nClocks: {mod.get('clocks')}\nResets: {mod.get('resets')}"
                doc_texts.append(header_text)
                self.documents.append({
                    "type": "RTL_MODULE_HEADER",
                    "module": mod["name"],
                    "file": file_path,
                    "line": mod.get("start_line", 1),
                    "content": header_text
                })

                # Always Blocks
                for idx, blk in enumerate(mod.get("always_blocks", [])):
                    blk_type = "Sequential Clocked" if blk.get("is_sequential") else "Combinational"
                    blk_text = f"Module {mod['name']} ({base_fname}:{blk.get('line', 1)}) - {blk_type} Always Block @({blk.get('sensitivity')}):\n{blk.get('code')}"
                    doc_texts.append(blk_text)
                    self.documents.append({
                        "type": "RTL_ALWAYS_BLOCK",
                        "module": mod["name"],
                        "file": file_path,
                        "line": blk.get("line", 1),
                        "content": blk_text
                    })

        # 2. Chunk EDA Findings (Lint & Synthesis)
        for rep in reports:
            tool = rep.get("tool", "EDA")
            code = rep.get("code", "GEN")
            rep_text = f"Tool Finding: [{tool}] {rep.get('severity')} ({code}) in {rep.get('file')}:{rep.get('line')}\nMessage: {rep.get('message')}\nEvidence: {rep.get('evidence')}"
            doc_texts.append(rep_text)
            self.documents.append({
                "type": "EDA_FINDING",
                "tool": tool,
                "file": rep.get("file", ""),
                "line": rep.get("line", 0),
                "content": rep_text
            })

        # 3. Chunk Timing Paths
        if timing_paths:
            for p in timing_paths:
                p_text = f"Timing Path: {p.get('startpoint')} -> {p.get('endpoint')}\nSetup Slack: {p.get('slack')} ns\nArrival: {p.get('data_arrival_time')} ns, Required: {p.get('data_required_time')} ns"
                doc_texts.append(p_text)
                self.documents.append({
                    "type": "TIMING_PATH",
                    "file": p.get("startpoint", ""),
                    "line": 1,
                    "content": p_text
                })

        # Generate Embeddings
        if doc_texts:
            if self.have_faiss and self.encoder and self.index:
                self.index.reset()
                embeddings = self.encoder.encode(doc_texts, convert_to_numpy=True, normalize_embeddings=True)
                self.index.add(embeddings.astype(np.float32))
            else:
                # Lightweight TF-IDF / word-overlap bag-of-words fallback
                self.doc_embeddings = [set(t.lower().split()) for t in doc_texts]

    def retrieve(self, query: str, top_k: int = 5, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves top-k semantically relevant chunks with similarity score."""
        if not self.documents:
            return []

        results = []
        if self.have_faiss and self.encoder and self.index and self.index.ntotal > 0:
            q_vec = self.encoder.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
            distances, indices = self.index.search(q_vec, min(top_k * 3, self.index.ntotal))

            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1 or idx >= len(self.documents):
                    continue
                doc = self.documents[idx]
                if filter_type and doc.get("type") != filter_type:
                    continue
                results.append({
                    "similarity": float(dist),
                    "document": doc
                })
                if len(results) >= top_k:
                    break
        else:
            # Fallback word-overlap similarity
            q_words = set(query.lower().split())
            scored = []
            for doc, words in zip(self.documents, self.doc_embeddings or []):
                if filter_type and doc.get("type") != filter_type:
                    continue
                overlap = len(q_words & words) / max(1, len(q_words | words))
                scored.append((overlap, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            for sim, doc in scored[:top_k]:
                results.append({"similarity": float(sim), "document": doc})

        return results
