import sqlite3

import app as app_module
from conftest import register_and_login


# ---------- 基础 ----------

def test_index_ok(client):
    """首页能正常打开"""
    r = client.get("/")
    assert r.status_code == 200


def test_404_page(client):
    """访问不存在的地址返回 404 页面"""
    r = client.get("/no-such-page")
    assert r.status_code == 404
    assert "页面不存在" in r.get_data(as_text=True)


# ---------- 注册 ----------

def test_register_success(client):
    r = client.post("/register", data={
        "username": "alice",
        "password": "secret123",
        "password2": "secret123",
    })
    assert r.status_code == 302          # 注册成功 → 重定向到登录页
    assert "/login" in r.headers["Location"]


def test_register_duplicate(client):
    data = {"username": "bob", "password": "secret123", "password2": "secret123"}
    client.post("/register", data=data)
    r = client.post("/register", data=data)
    assert "已被注册" in r.get_data(as_text=True)


def test_register_short_password(client):
    r = client.post("/register", data={
        "username": "carl", "password": "123", "password2": "123",
    })
    assert "至少 6 位" in r.get_data(as_text=True)


def test_register_password_mismatch(client):
    r = client.post("/register", data={
        "username": "dora", "password": "secret123", "password2": "secret456",
    })
    assert "不一致" in r.get_data(as_text=True)


# ---------- 登录 ----------

def test_login_wrong_password(client):
    client.post("/register", data={
        "username": "dave", "password": "secret123", "password2": "secret123",
    })
    r = client.post("/login", data={"username": "dave", "password": "wrong"})
    assert "用户名或密码错误" in r.get_data(as_text=True)


def test_login_success(client):
    register_and_login(client, "erin")
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert sess.get("username") == "erin"


# ---------- 发布留言 ----------

def test_post_requires_login(client):
    """未登录发留言应被重定向到登录页"""
    r = client.post("/post", data={"content": "偷偷发一条"})
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_post_message(client):
    register_and_login(client, "frank")
    r = client.post("/post", data={"content": "我的第一条留言"}, follow_redirects=True)
    text = r.get_data(as_text=True)
    assert "我的第一条留言" in text
    assert "frank" in text


# ---------- 删除权限 ----------

def _only_message_id():
    conn = sqlite3.connect(app_module.DB)
    row = conn.execute("SELECT id FROM messages LIMIT 1").fetchone()
    conn.close()
    return row[0]


def test_delete_own_message(client):
    register_and_login(client, "gina")
    client.post("/post", data={"content": "gina 的留言"})

    mid = _only_message_id()
    r = client.post(f"/delete/{mid}")
    assert r.status_code == 302

    conn = sqlite3.connect(app_module.DB)
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    assert count == 0


def test_cannot_delete_others_message(client):
    """核心权限测试：不能删别人的留言"""
    register_and_login(client, "henry")
    client.post("/post", data={"content": "henry 的留言"})
    mid = _only_message_id()

    client.get("/logout")
    register_and_login(client, "ivy")

    r = client.post(f"/delete/{mid}")
    assert r.status_code == 403

    # 再确认留言还在
    conn = sqlite3.connect(app_module.DB)
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    assert count == 1


# ---------- 搜索 ----------

def test_search_filters(client):
    register_and_login(client, "judy")
    client.post("/post", data={"content": "flask 学习笔记"})
    client.post("/post", data={"content": "linux 命令练习"})

    r = client.get("/?q=flask")
    text = r.get_data(as_text=True)

    # 命中的留言要出现（关键词会被 <mark> 包裹，所以只断言未受影响的片段）
    assert "学习笔记" in text
    # 未命中的留言不能出现
    assert "命令练习" not in text
    # 命中数量正确
    assert "找到 1 条" in text


def test_search_highlight(client):
    register_and_login(client, "kate")
    client.post("/post", data={"content": "hello flask world"})

    r = client.get("/?q=flask")
    body = r.get_data(as_text=True)

    assert "<mark>flask</mark>" in body
    assert "hello <mark>flask</mark> world" in body     # 高亮位置正确


# ---------- 安全 ----------

def test_xss_is_escaped(client):
    """最关键的安全测试：HTML 标签必须被转义"""
    register_and_login(client, "leo")
    client.post("/post", data={"content": "<script>alert(1)</script>"})

    r = client.get("/")
    body = r.get_data(as_text=True)

    assert "<script>alert(1)</script>" not in body     # 不能被当 HTML 执行
    assert "&lt;script&gt;" in body                     # 必须显示成转义后的文本


def test_password_is_hashed(client):
    """密码必须存哈希，不能存明文"""
    client.post("/register", data={
        "username": "mia", "password": "secret123", "password2": "secret123",
    })
    conn = sqlite3.connect(app_module.DB)
    h = conn.execute("SELECT password_hash FROM users WHERE username='mia'").fetchone()[0]
    conn.close()

    assert "secret123" not in h
    assert h.startswith(("scrypt:", "pbkdf2:"))