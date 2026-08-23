"""
ChipPilot AI - Database Manager
Handles SQLite persistent storage for projects, runs, findings, timing paths, RCA, and audit logs.
"""

import sqlite3
import os
import json
from typing import Dict, List, Any, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    top_module TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    content_hash TEXT
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    worst_slack REAL,
    total_cells INTEGER,
    lint_errors INTEGER,
    lint_warnings INTEGER,
    summary_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eda_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES analysis_runs(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    finding_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    rule_code TEXT,
    file_path TEXT,
    line_number INTEGER,
    message TEXT NOT NULL,
    raw_evidence TEXT
);

CREATE TABLE IF NOT EXISTS timing_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES analysis_runs(id) ON DELETE CASCADE,
    startpoint TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    slack REAL NOT NULL,
    arrival_time REAL,
    required_time REAL,
    is_violation BOOLEAN,
    raw_dump TEXT
);

CREATE TABLE IF NOT EXISTS root_causes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES analysis_runs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    severity TEXT NOT NULL,
    file_path TEXT,
    line_number INTEGER,
    hypothesis TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS optimization_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES analysis_runs(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    target_path TEXT,
    action TEXT NOT NULL,
    description TEXT NOT NULL,
    expected_gain TEXT,
    verification_step TEXT
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT REFERENCES analysis_runs(id) ON DELETE CASCADE,
    user_query TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_findings_run ON eda_findings(run_id);
CREATE INDEX IF NOT EXISTS idx_timing_run ON timing_paths(run_id);
CREATE INDEX IF NOT EXISTS idx_rca_run ON root_causes(run_id);
"""

class DatabaseManager:
    def __init__(self, db_path: str = "database/chippilot.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript(SCHEMA_SQL)

    def save_project(self, project_id: str, name: str, top_module: str, files: List[str]):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO projects (id, name, top_module) VALUES (?, ?, ?)",
                (project_id, name, top_module)
            )
            conn.execute("DELETE FROM project_files WHERE project_id = ?", (project_id,))
            for f in files:
                conn.execute(
                    "INSERT INTO project_files (project_id, file_path, file_type) VALUES (?, ?, ?)",
                    (project_id, f, "verilog" if f.endswith(('.v', '.sv')) else "other")
                )

    def save_analysis_run(self, run_id: str, project_id: str, worst_slack: float, total_cells: int,
                          lint_errors: int, lint_warnings: int, findings: List[Dict[str, Any]],
                          timing_paths: List[Dict[str, Any]], root_causes: List[Dict[str, Any]],
                          optimizations: List[Dict[str, Any]], summary_json: Optional[Dict[str, Any]] = None):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO analysis_runs 
                   (id, project_id, status, worst_slack, total_cells, lint_errors, lint_warnings, summary_json) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, project_id, "COMPLETED", worst_slack, total_cells, lint_errors, lint_warnings,
                 json.dumps(summary_json or {}))
            )

            # Insert Findings
            for f in findings:
                conn.execute(
                    """INSERT INTO eda_findings 
                       (run_id, tool, finding_type, severity, rule_code, file_path, line_number, message, raw_evidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, f.get("tool", "Unknown"), f.get("type", "LINT"), f.get("severity", "INFO"),
                     f.get("code", "GENERIC"), f.get("file", ""), f.get("line", 0), f.get("message", ""),
                     f.get("evidence", ""))
                )

            # Insert Timing Paths
            for p in timing_paths:
                conn.execute(
                    """INSERT INTO timing_paths 
                       (run_id, startpoint, endpoint, slack, arrival_time, required_time, is_violation, raw_dump)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, p.get("startpoint", ""), p.get("endpoint", ""), p.get("slack", 0.0),
                     p.get("data_arrival_time", 0.0), p.get("data_required_time", 0.0),
                     p.get("is_violation", False), p.get("raw_path_dump", ""))
                )

            # Insert Root Causes
            for rc in root_causes:
                conn.execute(
                    """INSERT INTO root_causes 
                       (run_id, title, confidence_score, severity, file_path, line_number, hypothesis, evidence_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, rc.get("title", ""), rc.get("confidence_score", 0.0), rc.get("severity", "INFO"),
                     rc.get("file", ""), rc.get("line", 0), rc.get("hypothesis", ""),
                     json.dumps(rc.get("evidence", [])))
                )

            # Insert Optimizations
            for opt in optimizations:
                conn.execute(
                    """INSERT INTO optimization_recommendations 
                       (run_id, category, target_path, action, description, expected_gain, verification_step)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, opt.get("category", ""), opt.get("target_path", ""), opt.get("action", ""),
                     opt.get("description", ""), opt.get("expected_gain", ""), opt.get("verification", ""))
                )

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            run_row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
            if not run_row:
                return None

            findings = [dict(r) for r in conn.execute("SELECT * FROM eda_findings WHERE run_id = ?", (run_id,)).fetchall()]
            timing_paths = [dict(r) for r in conn.execute("SELECT * FROM timing_paths WHERE run_id = ?", (run_id,)).fetchall()]
            root_causes = [dict(r) for r in conn.execute("SELECT * FROM root_causes WHERE run_id = ?", (run_id,)).fetchall()]
            optimizations = [dict(r) for r in conn.execute("SELECT * FROM optimization_recommendations WHERE run_id = ?", (run_id,)).fetchall()]

            res = dict(run_row)
            res["findings"] = findings
            res["timing_paths"] = timing_paths
            res["root_causes"] = root_causes
            res["optimizations"] = optimizations
            return res

    def save_chat(self, run_id: str, query: str, response: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO chat_history (run_id, user_query, assistant_response) VALUES (?, ?, ?)",
                (run_id, query, response)
            )

    def get_chat_history(self, run_id: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM chat_history WHERE run_id = ? ORDER BY id ASC", (run_id,)).fetchall()]
