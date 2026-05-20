import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "challenge.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as conn:
        # Keep roll number unique so a returning student continues the same profile.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE,
                class_section TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                task_title TEXT NOT NULL,
                word_limit INTEGER NOT NULL,
                student_prompt TEXT NOT NULL,
                word_count INTEGER NOT NULL,
                score REAL NOT NULL,
                feedback TEXT,
                improved_prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                UNIQUE(student_id, round_number)
            )
            """
        )
        conn.commit()


def get_or_create_student(name: str, roll_number: str, class_section: str = "") -> Dict[str, Any]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM students WHERE roll_number = ?",
            (roll_number.strip(),),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE students
                SET name = ?, class_section = ?
                WHERE id = ?
                """,
                (name.strip(), class_section.strip(), existing["id"]),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM students WHERE id = ?",
                (existing["id"],),
            ).fetchone()
            return dict(updated)

        cursor = conn.execute(
            """
            INSERT INTO students (name, roll_number, class_section)
            VALUES (?, ?, ?)
            """,
            (name.strip(), roll_number.strip(), class_section.strip()),
        )
        conn.commit()
        student_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row)


def get_student_by_id(student_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None


def save_submission(
    student_id: int,
    round_number: int,
    task_title: str,
    word_limit: int,
    student_prompt: str,
    word_count: int,
    score: float,
    feedback: str,
    improved_prompt: str,
) -> None:
    with get_connection() as conn:
        # Replace the same student's round if they retry, while preserving the original timestamp.
        conn.execute(
            """
            INSERT OR REPLACE INTO submissions (
                id,
                student_id,
                round_number,
                task_title,
                word_limit,
                student_prompt,
                word_count,
                score,
                feedback,
                improved_prompt,
                created_at
            )
            VALUES (
                (SELECT id FROM submissions WHERE student_id = ? AND round_number = ?),
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                COALESCE(
                    (SELECT created_at FROM submissions WHERE student_id = ? AND round_number = ?),
                    CURRENT_TIMESTAMP
                )
            )
            """,
            (
                student_id,
                round_number,
                student_id,
                round_number,
                task_title,
                word_limit,
                student_prompt,
                word_count,
                score,
                feedback,
                improved_prompt,
                student_id,
                round_number,
            ),
        )
        conn.commit()


def get_student_submissions(student_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM submissions
            WHERE student_id = ?
            ORDER BY round_number ASC
            """,
            (student_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_submission(student_id: int, round_number: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM submissions
            WHERE student_id = ? AND round_number = ?
            """,
            (student_id, round_number),
        ).fetchone()
        return dict(row) if row else None


def get_leaderboard() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                s.name,
                s.roll_number,
                COALESCE(ROUND(SUM(sub.score), 2), 0) AS total_score,
                COALESCE(ROUND(AVG(sub.score), 2), 0) AS average_score,
                COUNT(sub.id) AS rounds_attempted
            FROM students s
            LEFT JOIN submissions sub ON s.id = sub.student_id
            GROUP BY s.id, s.name, s.roll_number
            ORDER BY total_score DESC, average_score DESC, s.name ASC
            """
        ).fetchall()

        leaderboard = []
        for index, row in enumerate(rows, start=1):
            item = dict(row)
            item["rank"] = index
            leaderboard.append(item)
        return leaderboard


def get_all_submissions() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                sub.id,
                stu.name,
                stu.roll_number,
                stu.class_section,
                sub.round_number,
                sub.task_title,
                sub.word_limit,
                sub.word_count,
                sub.score,
                sub.student_prompt,
                sub.feedback,
                sub.improved_prompt,
                sub.created_at
            FROM submissions sub
            INNER JOIN students stu ON stu.id = sub.student_id
            ORDER BY sub.created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def clear_all_data() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM submissions")
        conn.execute("DELETE FROM students")
        conn.commit()
