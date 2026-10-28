# 留言板

一个用 Flask + SQLite 实现的简易留言板，用于学习 Python Web 开发与 Linux 部署。

## 功能

- 发布留言
- 分页浏览（每页 5 条）
- 删除留言（带二次确认）

## 技术栈

- Flask 3.x
- SQLite
- gunicorn + systemd
- Cloudflare Tunnel（内网穿透）

## 本地运行

\`\`\`bash
python3 -m venv venv
source venv/bin/activate
pip install flask gunicorn

python app.py
# 访问 http://localhost:5000
\`\`\`

## 部署

服务由 systemd 管理：

\`\`\`bash
sudo systemctl status mywebsite
sudo systemctl restart mywebsite
journalctl -u mywebsite -f
\`\`\`