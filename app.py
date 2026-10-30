import sqlite3
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, abort)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "c9f1e8a7b2d4f6a3e5c8b1d7f9a2e4c6"

DB = "messages.db"
PER_PAGE = 5


# ---------- 数据库 ----------

def init_db():
    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            name       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 兼容旧数据库：老表没有 user_id 列就补上
    cols = [row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()]
    if "user_id" not in cols:
        conn.execute("ALTER TABLE messages ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- 工具 ----------

def current_user_id():
    return session.get("user_id")


# ---------- 页面 ----------
def like_pattern(keyword):
    """转义 LIKE 的特殊字符，防止用户输入 % 或 _ 造成意外匹配"""
    keyword = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{keyword}%"

@app.route("/")
def index():
    # 页码
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    # 搜索关键词
    q = request.args.get("q", "").strip()

    # 动态拼 WHERE 条件
    where = ""
    params = []
    if q:
        where = "WHERE content LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\'"
        pattern = like_pattern(q)
        params = [pattern, pattern]

    conn = get_db()

    # 总条数（带搜索条件）
    total = conn.execute(
        f"SELECT COUNT(*) FROM messages {where}", params
    ).fetchone()[0]

    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    if page > total_pages:
        page = total_pages

    offset = (page - 1) * PER_PAGE
    messages = conn.execute(
        f"SELECT * FROM messages {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [PER_PAGE, offset]
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        messages=messages,
        page=page,
        total_pages=total_pages,
        total=total,
        q=q,
    )


@app.route("/post", methods=["POST"])
def post():
    uid = current_user_id()
    if not uid:
        return redirect(url_for("login"))

    content = request.form.get("content", "").strip()

    if content:
        conn = get_db()
        conn.execute(
            "INSERT INTO messages (user_id, name, content, created_at) VALUES (?, ?, ?, ?)",
            (uid, session.get("username"), content,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

    return redirect(url_for("index"))


@app.route("/delete/<int:msg_id>", methods=["POST"])
def delete(msg_id):
    uid = current_user_id()
    if not uid:
        abort(403)

    conn = get_db()
    msg = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()

    if not msg:
        conn.close()
        abort(404)

    # 只能删自己的；user_id 为 NULL 的是旧数据，允许登录用户清理
    if msg["user_id"] is not None and msg["user_id"] != uid:
        conn.close()
        abort(403)

    conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

    page = request.args.get("page", 1)
    q = request.args.get("q", "").strip()
    return redirect(url_for("index", page=page, q=q or None))


# ---------- 用户 ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not username or not password:
            error = "用户名和密码不能为空"
        elif not (2 <= len(username) <= 20):
            error = "用户名长度需在 2~20 个字符之间"
        elif len(password) < 6:
            error = "密码至少 6 位"
        elif password != password2:
            error = "两次输入的密码不一致"
        else:
            conn = get_db()
            exists = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()

            if exists:
                error = "该用户名已被注册"
                conn.close()
            else:
                conn.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password),
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                conn.close()
                return redirect(url_for("login"))

    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))

        error = "用户名或密码错误"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# 模块被导入时（gunicorn / python app.py 都会）立即建表与迁移
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)