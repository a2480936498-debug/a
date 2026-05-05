from __future__ import annotations

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from database import (
    BUG_CATEGORIES,
    BUG_SEVERITIES,
    BUG_STATUSES,
    add_team_member,
    auto_triage_bug,
    create_bug,
    get_bug,
    get_bug_history,
    get_dashboard_summary,
    get_team_members,
    init_db,
    list_bugs,
    update_bug,
    update_team_member,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = "bug-triage-system-demo-secret"

init_db()


@app.context_processor
def inject_globals():
    return {
        "bug_categories": BUG_CATEGORIES,
        "bug_statuses": BUG_STATUSES,
        "bug_severities": BUG_SEVERITIES,
    }


@app.route("/")
def dashboard():
    summary = get_dashboard_summary()
    recent_bugs = list_bugs(limit=8)
    return render_template("dashboard.html", summary=summary, recent_bugs=recent_bugs)


@app.route("/bugs")
def bug_list():
    filters = {
        "status": request.args.get("status", "").strip(),
        "category": request.args.get("category", "").strip(),
        "severity": request.args.get("severity", "").strip(),
        "assignee_id": request.args.get("assignee_id", "").strip(),
        "search": request.args.get("search", "").strip(),
    }
    bugs = list_bugs(filters)
    team_members = get_team_members()
    return render_template("bugs.html", bugs=bugs, filters=filters, team_members=team_members)


@app.route("/bugs/new", methods=["GET", "POST"])
def create_bug_view():
    if request.method == "POST":
        bug_id = create_bug(request.form.to_dict())
        flash(f"Bug #{bug_id} 已创建，并完成自动分类与分配。", "success")
        return redirect(url_for("edit_bug_view", bug_id=bug_id))
    return render_template("bug_form.html", bug=None, history=None, team_members=get_team_members())


@app.route("/bugs/<int:bug_id>/edit", methods=["GET", "POST"])
def edit_bug_view(bug_id: int):
    if request.method == "POST":
        update_bug(bug_id, request.form.to_dict())
        flash(f"Bug #{bug_id} 已更新。", "success")
        return redirect(url_for("edit_bug_view", bug_id=bug_id))

    bug = get_bug(bug_id)
    if bug is None:
        flash("未找到对应 Bug。", "error")
        return redirect(url_for("bug_list"))

    history = get_bug_history(bug_id)
    return render_template(
        "bug_form.html",
        bug=bug,
        history=history,
        team_members=get_team_members(),
    )


@app.post("/bugs/<int:bug_id>/auto-triage")
def auto_triage_view(bug_id: int):
    auto_triage_bug(bug_id)
    flash(f"Bug #{bug_id} 已重新自动分类并分配。", "success")
    return redirect(url_for("edit_bug_view", bug_id=bug_id))


@app.route("/team", methods=["GET", "POST"])
def team_view():
    if request.method == "POST":
        add_team_member(request.form.to_dict())
        flash("团队成员已添加。", "success")
        return redirect(url_for("team_view"))
    return render_template("team.html", team_members=get_team_members())


@app.post("/team/<int:member_id>/edit")
def edit_team_member_view(member_id: int):
    update_team_member(member_id, request.form.to_dict())
    flash("成员信息已更新。", "success")
    return redirect(url_for("team_view"))


@app.get("/api/bugs")
def bug_api():
    bugs = list_bugs(limit=50)
    payload = [
        {
            "id": bug["id"],
            "title": bug["title"],
            "category": bug["category"],
            "severity": bug["severity"],
            "status": bug["status"],
            "assignee": bug["assignee_name"],
            "updated_at": bug["updated_at"],
        }
        for bug in bugs
    ]
    return jsonify(payload)


if __name__ == "__main__":
    app.run(debug=True)

