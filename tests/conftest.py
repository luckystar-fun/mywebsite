import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    每个测试函数都会拿到一个全新的、隔离的测试环境：
    - 独立的临时数据库（tmp_path），绝不会碰真实的 messages.db
    - TESTING 模式（异常会直接抛出，不会变成 500 页面）
    """
    monkeypatch.setattr(app_module, "DB", str(tmp_path / "test.db"))
    app_module.init_db()

    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as c:
        yield c


def register_and_login(client, username="alice", password="secret123"):
    """测试辅助：注册并登录"""
    client.post("/register", data={
        "username": username,
        "password": password,
        "password2": password,
    })
    return client.post("/login", data={
        "username": username,
        "password": password,
    })