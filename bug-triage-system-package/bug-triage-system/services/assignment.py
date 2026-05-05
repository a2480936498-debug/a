from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple


OPEN_STATUSES = ("待处理", "处理中", "待验证")


def _member_value(member, key: str):
    try:
        return member[key]
    except (KeyError, TypeError):
        return member.get(key)


def parse_expertise(expertise: str) -> List[str]:
    if not expertise:
        return []
    return [item.strip() for item in expertise.split(",") if item.strip()]


def rank_candidates(
    members: Iterable,
    workloads: Dict[int, int],
    category: str,
) -> Tuple[Optional[object], List[object]]:
    members = list(members)
    if not members:
        return None, []

    preferred = [
        member
        for member in members
        if category in parse_expertise(_member_value(member, "expertise") or "")
    ]
    candidates = preferred or members

    def sort_key(member):
        member_id = int(_member_value(member, "id"))
        capacity = max(int(_member_value(member, "capacity") or 1), 1)
        open_count = int(workloads.get(member_id, 0))
        expertise = parse_expertise(_member_value(member, "expertise") or "")
        expertise_penalty = 0 if category in expertise else 1
        load_ratio = open_count / capacity
        return (expertise_penalty, load_ratio, open_count, -capacity, _member_value(member, "name"))

    ranked = sorted(candidates, key=sort_key)
    return ranked[0], ranked


def choose_assignee(conn, category: str):
    members = conn.execute(
        """
        SELECT id, name, email, expertise, capacity, active
        FROM team_members
        WHERE active = 1
        ORDER BY name
        """
    ).fetchall()
    if not members:
        return None, "当前没有启用的处理成员。"

    workload_rows = conn.execute(
        """
        SELECT assignee_id, COUNT(*) AS open_count
        FROM bugs
        WHERE status IN (?, ?, ?)
          AND assignee_id IS NOT NULL
        GROUP BY assignee_id
        """,
        OPEN_STATUSES,
    ).fetchall()
    workloads = {row["assignee_id"]: row["open_count"] for row in workload_rows}

    winner, _ = rank_candidates(members, workloads, category)
    if winner is None:
        return None, "当前没有可用于分配的成员。"

    winner_id = int(_member_value(winner, "id"))
    open_count = int(workloads.get(winner_id, 0))
    capacity = max(int(_member_value(winner, "capacity") or 1), 1)
    expertise = parse_expertise(_member_value(winner, "expertise") or "")
    name = _member_value(winner, "name")

    if category in expertise:
        reason = (
            f"{name} 具备 {category} 专长，当前开放 Bug {open_count} 个，"
            f"容量上限 {capacity} 个。"
        )
    else:
        reason = (
            f"{name} 为当前负载最轻成员，当前开放 Bug {open_count} 个，"
            f"容量上限 {capacity} 个。"
        )

    return winner, reason

