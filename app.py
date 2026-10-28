import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DB = "messages.db"
PER_PAGE = 5          # 每页显示几条


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
    """首页：分页显示留言"""
    # 1. 取页码，容错处理
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    conn = get_db()

    # 2. 总条数和总页数
    total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    if page > total_pages:
        page = total_pages

    # 3. 只取当前页的数据
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
    """发布留言"""
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


@app.route("/delete/<int:msg_id>", methods=["POST"])
def delete(msg_id):
    """删除留言：注意用 POST，不是 GET"""
    page = request.args.get("page", 1)

    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("index", page=page))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)