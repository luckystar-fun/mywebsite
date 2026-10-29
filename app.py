import os
import sqlite3
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, abort)

app = Flask(__name__)

# session 加密用的密钥，必须固定且保密
app.secret_key = "c9f1e8a7b2d4f6a3e5c8b1d7f9a2e4c6"

# 管理员密码（学习用，正式项目应存哈希）
ADMIN_PASSWORD = "learn123"

DB = "messages.db"
PER_PAGE = 5


def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    if page > total_pages:
        page = total_pages

    offset = (page - 1) * PER_PAGE
    messages = conn.execute(
        "SELECT * FROM messages ORDER BY id DESC LIMIT ? OFFSET ?",
        (PER_PAGE, offset)
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        messages=messages,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route("/post", methods=["POST"])
def post():
    name = request.form.get("name", "").strip()
    content = request.form.get("content", "").strip()

    if name and content:
        conn = get_db()
        conn.execute(
            "INSERT INTO messages (name, content, created_at) VALUES (?, ?, ?)",
            (name, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """登录页：GET 显示表单，POST 校验密码"""
    error = None

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["logged_in"] = True          # 记进 session
            return redirect(url_for("index"))
        error = "密码错误，请重试"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """退出登录"""
    session.pop("logged_in", None)
    return redirect(url_for("index"))


@app.route("/delete/<int:msg_id>", methods=["POST"])
def delete(msg_id):
    """删除留言：必须已登录"""
    if not session.get("logged_in"):
        abort(403)                                # 未登录直接拒绝

    page = request.args.get("page", 1)

    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("index", page=page))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)