from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from services.assignment import choose_assignee
from services.classification import classify_bug


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bug_triage.db"

BUG_STATUSES = ["待处理", "处理中", "待验证", "已关闭"]
BUG_SEVERITIES = ["低", "中", "高", "紧急"]
BUG_CATEGORIES = ["前端界面", "后端服务", "数据库", "性能", "安全", "集成", "其他"]

DEFAULT_TEAM_MEMBERS = [
    {
        "name": "李明",
        "email": "liming@example.com",
        "expertise": "后端服务,数据库,性能",
        "capacity": 6,
    },
    {
        "name": "王雪",
        "email": "wangxue@example.com",
        "expertise": "前端界面,集成",
        "capacity": 5,
    },
    {
        "name": "周航",
        "email": "zhouhang@example.com",
        "expertise": "安全,后端服务",
        "capacity": 4,
    },
    {
        "name": "陈晨",
        "email": "chenchen@example.com",
        "expertise": "数据库,性能",
        "capacity": 5,
    },
]

DEFAULT_BUGS = [
    {
        "title": "支付回调偶发超时",
        "description": "第三方支付 webhook 返回慢，导致订单状态同步延迟。",
        "reporter": "产品经理",
        "severity": "高",
        "status": "处理中",
    },
    {
        "title": "登录接口存在越权风险",
        "description": "用户可通过修改 token 访问他人数据，需要补充鉴权校验。",
        "reporter": "安全测试",
        "severity": "紧急",
        "status": "待处理",
    },
    {
        "title": "移动端按钮样式错位",
        "description": "iPhone 小屏幕下提交按钮被遮挡，页面布局异常。",
        "reporter": "UI 测试",
        "severity": "中",
        "status": "待验证",
    },
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            expertise TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 5,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reporter TEXT NOT NULL,
            severity TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            assignee_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (assignee_id) REFERENCES team_members(id)
        );

        CREATE TABLE IF NOT EXISTS bug_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (bug_id) REFERENCES bugs(id)
        );
        """
    )
    seed_if_needed(conn)
    conn.commit()
    conn.close()


def seed_if_needed(conn: sqlite3.Connection) -> None:
    team_count = conn.execute("SELECT COUNT(*) AS count FROM team_members").fetchone()["count"]
    if team_count == 0:
        timestamp = now_str()
        conn.executemany(
            """
            INSERT INTO team_members (name, email, expertise, capacity, active, created_at, updated_at)
            VALUES (:name, :email, :expertise, :capacity, 1, :created_at, :updated_at)
            """,
            [
                {
                    **member,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
                for member in DEFAULT_TEAM_MEMBERS
            ],
        )

    bug_count = conn.execute("SELECT COUNT(*) AS count FROM bugs").fetchone()["count"]
    if bug_count == 0:
        for bug in DEFAULT_BUGS:
            create_bug(bug, conn=conn)


def record_history(conn: sqlite3.Connection, bug_id: int, action: str, details: str) -> None:
    conn.execute(
        """
        INSERT INTO bug_history (bug_id, action, details, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (bug_id, action, details, now_str()),
    )


def create_bug(data: Dict[str, str], conn: Optional[sqlite3.Connection] = None) -> int:
    own_connection = conn is None
    conn = conn or get_connection()

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    reporter = (data.get("reporter") or "").strip()
    severity = (data.get("severity") or "中").strip()
    status = (data.get("status") or "待处理").strip()
    category, hits = classify_bug(title, description)
    assignee, reason = choose_assignee(conn, category)
    assignee_id = assignee["id"] if assignee else None
    timestamp = now_str()

    cursor = conn.execute(
        """
        INSERT INTO bugs (title, description, reporter, severity, category, status, assignee_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            description,
            reporter,
            severity,
            category,
            status,
            assignee_id,
            timestamp,
            timestamp,
        ),
    )
    bug_id = cursor.lastrowid

    record_history(conn, bug_id, "创建", f"由 {reporter} 提交，严重级别为 {severity}。")
    if hits:
        record_history(conn, bug_id, "自动分类", f"系统根据关键字 {', '.join(hits)} 判定为 {category}。")
    else:
        record_history(conn, bug_id, "自动分类", f"系统未命中关键字，默认归类为 {category}。")
    if assignee:
        record_history(conn, bug_id, "自动分配", reason)

    if own_connection:
        conn.commit()
        conn.close()
    return bug_id


def get_bug(bug_id: int):
    conn = get_connection()
    bug = conn.execute(
        """
        SELECT b.*, t.name AS assignee_name
        FROM bugs b
        LEFT JOIN team_members t ON t.id = b.assignee_id
        WHERE b.id = ?
        """,
        (bug_id,),
    ).fetchone()
    conn.close()
    return bug


def get_bug_history(bug_id: int):
    conn = get_connection()
    history = conn.execute(
        """
        SELECT action, details, created_at
        FROM bug_history
        WHERE bug_id = ?
        ORDER BY id DESC
        """,
        (bug_id,),
    ).fetchall()
    conn.close()
    return history


def list_bugs(filters: Optional[Dict[str, str]] = None, limit: Optional[int] = None):
    filters = filters or {}
    conn = get_connection()

    sql = """
        SELECT b.*, t.name AS assignee_name
        FROM bugs b
        LEFT JOIN team_members t ON t.id = b.assignee_id
        WHERE 1 = 1
    """
    params = []

    if filters.get("status"):
        sql += " AND b.status = ?"
        params.append(filters["status"])
    if filters.get("category"):
        sql += " AND b.category = ?"
        params.append(filters["category"])
    if filters.get("severity"):
        sql += " AND b.severity = ?"
        params.append(filters["severity"])
    if filters.get("assignee_id"):
        sql += " AND b.assignee_id = ?"
        params.append(filters["assignee_id"])
    if filters.get("search"):
        keyword = f"%{filters['search'].strip()}%"
        sql += " AND (b.title LIKE ? OR b.description LIKE ? OR b.reporter LIKE ?)"
        params.extend([keyword, keyword, keyword])

    sql += """
        ORDER BY
            CASE b.severity
                WHEN '紧急' THEN 1
                WHEN '高' THEN 2
                WHEN '中' THEN 3
                ELSE 4
            END,
            CASE b.status
                WHEN '待处理' THEN 1
                WHEN '处理中' THEN 2
                WHEN '待验证' THEN 3
                ELSE 4
            END,
            b.updated_at DESC
    """

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    bugs = conn.execute(sql, params).fetchall()
    conn.close()
    return bugs


def update_bug(bug_id: int, data: Dict[str, str]) -> None:
    conn = get_connection()
    current = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    if current is None:
        conn.close()
        raise ValueError("Bug 不存在。")

    title = (data.get("title") or current["title"]).strip()
    description = (data.get("description") or current["description"]).strip()
    reporter = (data.get("reporter") or current["reporter"]).strip()
    severity = (data.get("severity") or current["severity"]).strip()
    category = (data.get("category") or current["category"]).strip()
    status = (data.get("status") or current["status"]).strip()
    assignee_id = data.get("assignee_id")
    assignee_id = int(assignee_id) if assignee_id not in (None, "", "None") else None
    timestamp = now_str()

    conn.execute(
        """
        UPDATE bugs
        SET title = ?, description = ?, reporter = ?, severity = ?, category = ?, status = ?, assignee_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (title, description, reporter, severity, category, status, assignee_id, timestamp, bug_id),
    )

    changes = []
    field_labels = {
        "title": "标题",
        "description": "描述",
        "reporter": "提交人",
        "severity": "严重级别",
        "category": "分类",
        "status": "状态",
        "assignee_id": "处理人",
    }
    next_values = {
        "title": title,
        "description": description,
        "reporter": reporter,
        "severity": severity,
        "category": category,
        "status": status,
        "assignee_id": assignee_id,
    }

    for field, label in field_labels.items():
        old_value = current[field]
        new_value = next_values[field]
        if old_value != new_value:
            if field == "assignee_id":
                old_name = get_member_name_by_id(conn, old_value) if old_value else "未分配"
                new_name = get_member_name_by_id(conn, new_value) if new_value else "未分配"
                changes.append(f"{label}: {old_name} -> {new_name}")
            else:
                changes.append(f"{label}: {old_value} -> {new_value}")

    if changes:
        record_history(conn, bug_id, "手动更新", "；".join(changes))

    conn.commit()
    conn.close()


def auto_triage_bug(bug_id: int) -> None:
    conn = get_connection()
    bug = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    if bug is None:
        conn.close()
        raise ValueError("Bug 不存在。")

    new_category, hits = classify_bug(bug["title"], bug["description"])
    assignee, reason = choose_assignee(conn, new_category)
    new_assignee_id = assignee["id"] if assignee else None
    timestamp = now_str()

    conn.execute(
        """
        UPDATE bugs
        SET category = ?, assignee_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_category, new_assignee_id, timestamp, bug_id),
    )

    if bug["category"] != new_category:
        record_history(
            conn,
            bug_id,
            "重新分类",
            f"系统根据关键字 {', '.join(hits) if hits else '无'} 重新判定为 {new_category}。",
        )
    if bug["assignee_id"] != new_assignee_id and assignee:
        record_history(conn, bug_id, "重新分配", reason)

    conn.commit()
    conn.close()


def get_member_name_by_id(conn: sqlite3.Connection, member_id: Optional[int]) -> Optional[str]:
    if member_id is None:
        return None
    row = conn.execute("SELECT name FROM team_members WHERE id = ?", (member_id,)).fetchone()
    return row["name"] if row else None


def get_team_members():
    conn = get_connection()
    members = conn.execute(
        """
        SELECT
            t.*,
            COALESCE(SUM(CASE WHEN b.status IN ('待处理', '处理中', '待验证') THEN 1 ELSE 0 END), 0) AS open_bug_count,
            COUNT(b.id) AS total_bug_count
        FROM team_members t
        LEFT JOIN bugs b ON b.assignee_id = t.id
        GROUP BY t.id
        ORDER BY t.active DESC, t.name ASC
        """
    ).fetchall()
    conn.close()
    return members


def add_team_member(data: Dict[str, str]) -> None:
    conn = get_connection()
    timestamp = now_str()
    conn.execute(
        """
        INSERT INTO team_members (name, email, expertise, capacity, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (data.get("name") or "").strip(),
            (data.get("email") or "").strip(),
            (data.get("expertise") or "").strip(),
            int(data.get("capacity") or 5),
            1 if data.get("active") else 0,
            timestamp,
            timestamp,
        ),
    )
    conn.commit()
    conn.close()


def update_team_member(member_id: int, data: Dict[str, str]) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE team_members
        SET name = ?, email = ?, expertise = ?, capacity = ?, active = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            (data.get("name") or "").strip(),
            (data.get("email") or "").strip(),
            (data.get("expertise") or "").strip(),
            int(data.get("capacity") or 5),
            1 if data.get("active") else 0,
            now_str(),
            member_id,
        ),
    )
    conn.commit()
    conn.close()


def get_dashboard_summary():
    conn = get_connection()
    stats = {
        "total": conn.execute("SELECT COUNT(*) AS count FROM bugs").fetchone()["count"],
        "todo": conn.execute("SELECT COUNT(*) AS count FROM bugs WHERE status = '待处理'").fetchone()["count"],
        "doing": conn.execute("SELECT COUNT(*) AS count FROM bugs WHERE status = '处理中'").fetchone()["count"],
        "closed": conn.execute("SELECT COUNT(*) AS count FROM bugs WHERE status = '已关闭'").fetchone()["count"],
    }
    by_category = conn.execute(
        """
        SELECT category, COUNT(*) AS count
        FROM bugs
        GROUP BY category
        ORDER BY count DESC, category ASC
        """
    ).fetchall()
    by_severity = conn.execute(
        """
        SELECT severity, COUNT(*) AS count
        FROM bugs
        GROUP BY severity
        ORDER BY count DESC, severity ASC
        """
    ).fetchall()
    team_load = conn.execute(
        """
        SELECT
            t.name,
            t.capacity,
            COALESCE(SUM(CASE WHEN b.status IN ('待处理', '处理中', '待验证') THEN 1 ELSE 0 END), 0) AS open_bug_count
        FROM team_members t
        LEFT JOIN bugs b ON b.assignee_id = t.id
        WHERE t.active = 1
        GROUP BY t.id
        ORDER BY open_bug_count DESC, t.name ASC
        """
    ).fetchall()
    conn.close()
    return {
        "stats": stats,
        "by_category": by_category,
        "by_severity": by_severity,
        "team_load": team_load,
    }

