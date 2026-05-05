from __future__ import annotations

from typing import List, Tuple


CATEGORY_ORDER = [
    "安全",
    "性能",
    "数据库",
    "后端服务",
    "前端界面",
    "集成",
    "其他",
]

CATEGORY_KEYWORDS = {
    "前端界面": [
        "ui",
        "button",
        "layout",
        "style",
        "css",
        "font",
        "screen",
        "responsive",
        "页面",
        "按钮",
        "样式",
        "前端",
        "显示",
        "弹窗",
    ],
    "后端服务": [
        "api",
        "server",
        "backend",
        "exception",
        "traceback",
        "nullpointer",
        "service",
        "controller",
        "接口",
        "后端",
        "服务",
        "报错",
        "500",
        "空指针",
    ],
    "数据库": [
        "sql",
        "database",
        "db",
        "query",
        "migration",
        "deadlock",
        "table",
        "index",
        "数据库",
        "数据表",
        "索引",
        "慢查询",
        "事务",
    ],
    "性能": [
        "slow",
        "timeout",
        "latency",
        "memory",
        "cpu",
        "freeze",
        "卡顿",
        "超时",
        "响应慢",
        "性能",
        "耗时",
        "内存",
        "cpu占用",
    ],
    "安全": [
        "auth",
        "token",
        "permission",
        "xss",
        "csrf",
        "sql injection",
        "credential",
        "漏洞",
        "权限",
        "安全",
        "越权",
        "注入",
        "鉴权",
        "登录绕过",
    ],
    "集成": [
        "webhook",
        "sync",
        "integration",
        "callback",
        "third-party",
        "payment",
        "sms",
        "email",
        "支付",
        "短信",
        "邮件",
        "同步",
        "回调",
        "第三方",
        "对接",
    ],
}


def classify_bug(title: str, description: str) -> Tuple[str, List[str]]:
    text = f"{title or ''} {description or ''}".lower().strip()
    if not text:
        return "其他", []

    ranked_matches = []
    for category in CATEGORY_ORDER:
        if category == "其他":
            continue
        hits = [keyword for keyword in CATEGORY_KEYWORDS[category] if keyword.lower() in text]
        if hits:
            ranked_matches.append((category, len(hits), hits))

    if not ranked_matches:
        return "其他", []

    ranked_matches.sort(
        key=lambda item: (-item[1], CATEGORY_ORDER.index(item[0]))
    )
    best_category, _, hits = ranked_matches[0]
    return best_category, hits

