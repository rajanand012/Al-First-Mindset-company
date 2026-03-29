"""SQLite database for storing assessments."""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "assessments.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            website_url TEXT NOT NULL,
            industry_segment TEXT,
            company_size TEXT,
            overall_score REAL NOT NULL,
            max_score REAL NOT NULL,
            percentage REAL NOT NULL,
            grade TEXT NOT NULL,
            grade_label TEXT,
            category_scores TEXT NOT NULL,  -- JSON
            recommendations TEXT,           -- JSON
            executive_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_assessments_company
            ON assessments(company_name, website_url);
    """)
    conn.commit()
    conn.close()


def save_assessment(data):
    """Save a completed assessment. Returns the new row id."""
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO assessments
           (company_name, website_url, industry_segment, company_size,
            overall_score, max_score, percentage, grade, grade_label,
            category_scores, recommendations, executive_summary)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["company_name"],
            data["website_url"],
            data.get("industry_segment", ""),
            data.get("company_size", ""),
            data["overall_score"],
            data["max_score"],
            data["percentage"],
            data["grade"],
            data.get("grade_label", ""),
            json.dumps(data["category_scores"]),
            json.dumps(data.get("recommendations", [])),
            data.get("executive_summary", ""),
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_assessment(assessment_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_dict(row)


def get_company_history(company_name):
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM assessments
           WHERE company_name = ? ORDER BY created_at DESC""",
        (company_name,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_all_assessments():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM assessments ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row):
    d = dict(row)
    d["category_scores"] = json.loads(d["category_scores"])
    recs = d.get("recommendations")
    d["recommendations"] = json.loads(recs) if recs else []
    return d
