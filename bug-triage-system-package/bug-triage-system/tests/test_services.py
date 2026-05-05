import sqlite3
import unittest

from services.assignment import choose_assignee
from services.classification import classify_bug


class ClassificationTests(unittest.TestCase):
    def test_security_bug_should_match_security_category(self):
        category, hits = classify_bug(
            "登录接口存在安全漏洞",
            "通过修改 token 可绕过鉴权访问他人数据。",
        )
        self.assertEqual(category, "安全")
        self.assertIn("token", hits)

    def test_unknown_bug_should_fallback_to_other(self):
        category, hits = classify_bug("文案问题", "帮助中心的描述措辞需要更自然一些。")
        self.assertEqual(category, "其他")
        self.assertEqual(hits, [])


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                expertise TEXT NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 5,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE bugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                status TEXT NOT NULL,
                assignee_id INTEGER
            );
            """
        )
        self.conn.executemany(
            """
            INSERT INTO team_members (name, email, expertise, capacity, active)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Alice", "alice@example.com", "前端界面,集成", 5, 1),
                ("Bob", "bob@example.com", "前端界面,后端服务", 5, 1),
                ("Carol", "carol@example.com", "数据库", 4, 1),
            ],
        )
        self.conn.executemany(
            """
            INSERT INTO bugs (title, status, assignee_id)
            VALUES (?, ?, ?)
            """,
            [
                ("bug-1", "处理中", 2),
                ("bug-2", "待处理", 2),
                ("bug-3", "处理中", 3),
            ],
        )

    def tearDown(self):
        self.conn.close()

    def test_choose_lighter_expert_first(self):
        assignee, reason = choose_assignee(self.conn, "前端界面")
        self.assertEqual(assignee["name"], "Alice")
        self.assertIn("专长", reason)


if __name__ == "__main__":
    unittest.main()
