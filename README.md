# 每日作战打卡看板

> 大客户牵引部团队打卡工具 · v1.0

纯前端 Web 应用（HTML/CSS/JS）+ Python 后端，零外部依赖。

---

## 快速上手

**场景一：本地开发调试（前后端分离）**

```bash
# 终端 1：后端纯 API
python backend/dev.py --api-only --port 8080

# 终端 2：前端 HTTP 服务器
cd frontend && python -m http.server 3000

# 浏览器打开 http://localhost:3000
```

**场景二：完整部署（Docker Compose）**

```bash
docker compose up -d
# 后端 API：http://localhost:8080
# 前端页面：由外网 nginx 托管 frontend/
```

详见 [`DEPLOY.md`](./DEPLOY.md)。

---

## 项目结构

```
├── docker-compose.yml         Docker 编排（单服务）
├── .env                       已预填配置（密码 365 + 端口 8080）
├── .env.example               环境变量模板（参考用）
│
├── frontend/                  前端包（外网 nginx / 本地调试都用这个）
│   ├── index.html / styles.css / app.js / config.js
│   └── ★ config.js 中 serverUrl 指向后端地址
│
├── backend/                   后端包
│   ├── api.py                 纯 API（生产用）
│   ├── dev.py                 本地开发（含静态文件服务）
│   ├── main.py                入口
│   └── deploy/Dockerfile
│
├── deploy/                    运维辅助
│   └── start.sh / stop.sh / logs.sh
│
├── data/                      数据目录（SQLite）
├── ops-guide.html             运维部署指引
├── CHANGELOG.md               迭代记录
└── DEPLOY.md                  部署文档
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | 纯 HTML/CSS/JS（零框架） |
| 后端 | Python 标准库 http.server |
| 存储 | SQLite（WAL 模式） |
| 部署 | Docker Compose |

---

## 依赖

- **运行**：Python 3.9+（标准库，无需 pip install）
- **部署**：Docker Engine 24.0+、Docker Compose v2.20+
- **浏览器**：Chrome / Edge / Safari / Firefox
