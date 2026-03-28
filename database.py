"""SQLite database for storing assessments and web cache."""

import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "assessments.db")
CACHE_TTL_DAYS = 7


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
            category_scores TEXT NOT NULL,  -- JSON
            recommendations TEXT NOT NULL,  -- JSON
            web_content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS web_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_assessments_company
            ON assessments(company_name, website_url);
        CREATE INDEX IF NOT EXISTS idx_web_cache_url
            ON web_cache(url);
    """)
    conn.commit()
    conn.close()


# --- Web Cache ---

def get_cached_content(url):
    """Return cached web content if within TTL, else None."""
    conn = get_db()
    row = conn.execute(
        "SELECT content, fetched_at FROM web_cache WHERE url = ?", (url,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    fetched_at = datetime.fromisoformat(row["fetched_at"])
    if datetime.now() - fetched_at > timedelta(days=CACHE_TTL_DAYS):
        return None

    return row["content"]


def set_cached_content(url, content):
    """Store or update cached web content."""
    conn = get_db()
    conn.execute(
        """INSERT INTO web_cache (url, content, fetched_at)
           VALUES (?, ?, ?)
           ON CONFLICT(url) DO UPDATE SET content=?, fetched_at=?""",
        (url, content, datetime.now().isoformat(),
         content, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


# --- Assessments ---

def save_assessment(data):
    """Save a completed assessment. Returns the new row id."""
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO assessments
           (company_name, website_url, industry_segment, company_size,
            overall_score, max_score, percentage, grade,
            category_scores, recommendations, web_content_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["company_name"],
            data["website_url"],
            data.get("industry_segment", ""),
            data.get("company_size", ""),
            data["overall_score"],
            data["max_score"],
            data["percentage"],
            data["grade"],
            json.dumps(data["category_scores"]),
            json.dumps(data["recommendations"]),
            data.get("web_content_hash", ""),
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_assessment(assessment_id):
    """Retrieve a single assessment by id."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_dict(row)


def get_company_history(company_name):
    """Get all past assessments for a company, newest first."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM assessments
           WHERE company_name = ? ORDER BY created_at DESC""",
        (company_name,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_all_assessments():
    """Get all assessments, newest first."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM assessments ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row):
    d = dict(row)
    d["category_scores"] = json.loads(d["category_scores"])
    d["recommendations"] = json.loads(d["recommendations"])
    return d
