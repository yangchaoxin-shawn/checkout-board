# 每日作战打卡看板 — 部署文档

> 项目根目录下的 `DEPLOY.md`，你一眼就能看到它。
> 根据你的场景，跳到对应章节即可。

---

## 三种场景，对号入座

| 场景 | 在哪操作 | 做什么 | 跳到 |
|:----:|---------|--------|:----:|
| ⚡ **日常开发** | Windows 终端 (Git Bash / PowerShell) | 改前端/后端代码，快速看效果 | [场景一](#%E2%9A%A1-%E5%9C%BA%E6%99%AF%E4%B8%80windows-%E6%9C%AC%E5%9C%B0%E7%BB%88%E7%AB%AF%E8%B0%83%E8%AF%95) |
| 🧪 **环境测试** | WSL (Ubuntu Linux) | 用 Docker 完整模拟生产环境，验证部署流程 | [场景二](#%F0%9F%A7%AA-%E5%9C%BA%E6%99%AF%E4%BA%8Cwsl--linux-%E7%8E%AF%E5%A2%83%E6%B5%8B%E8%AF%95) |
| 🚀 **正式上线** | 生产 Linux 服务器 | 申请域名 + SSL，交付给运维人员部署 | [场景三](#%F0%9F%9A%80-%E5%9C%BA%E6%99%AF%E4%B8%89%E7%94%9F%E4%BA%A7-linux-%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2) |

> 📖 项目迭代历史请见 [`CHANGELOG.md`](./CHANGELOG.md)

---

## 🗂️ 项目结构

```
打卡小程序/
│
├── frontend/              ← 👈 前端包：放入你的 nginx 中托管
│   ├── index.html / styles.css / app.js / config.js
│   └── ★ config.js 中 serverUrl 指向后端地址
│
├── backend/               ← 👈 后端包：纯 API 服务（Docker 容器）
│   ├── api.py                 纯 API
│   ├── dev.py                 本地开发（含静态文件服务）
│   ├── main.py                入口
│   └── deploy/Dockerfile
│
├── deploy/                ← 辅助运维
│   ├── start.sh / stop.sh / logs.sh
├── docker-compose.yml     ← 单服务编排（端口由 .env 控制）
├── .env.example           → .env（配密码和端口）
├── ops-guide.html         运维部署指引
├── DEPLOY.md              部署文档（本文件）
├── user-guide.html        用户操作手册
└── ...
```

> **整体架构：** 你（运维）的外网 nginx 托管 `frontend/` 静态文件，`/api/*` 反向代理到后端容器。<br>
> **后端：** Docker 跑纯 API（`--api-only`），端口由 `.env` 中 `API_PORT` 控制，默认 8080。<br>
> **本地开发：** 前后端分离调试（后端纯 API + 前端 HTTP 服务器）。

---

## ⚡ 场景一：Windows 本地终端调试

**目标**：改完代码马上看效果，不经过 Docker，秒级启动。

```bash
# 终端 1：后端纯 API
python backend/dev.py --api-only --port 8080

# 终端 2：前端 HTTP 服务器
cd frontend && python -m http.server 3000

# 浏览器访问 http://localhost:3000
```

**要点：**
- 改前端代码刷新浏览器即可（热更新）
- 数据库文件自动创建在 `data/checkin.db`
- 自定义端口：`python backend/dev.py --api-only --port 9000`

---

## 🧪 场景二：WSL / Linux 环境测试

**目标**：在你的 Windows 电脑上，通过 WSL 启动 Linux 环境，用 Docker 完整模拟生产部署。

### 前提条件

```
WSL 已安装（建议 Ubuntu 22.04+）
Docker Desktop 已安装，并启用 WSL2 集成
  设置路径：Docker Desktop → Settings → Resources → WSL Integration
```

### 操作步骤

**① 进入 WSL 终端**

```bash
# 打开 Windows 终端或 PowerShell，输入：
wsl

# 进入项目目录（Windows 文件在 /mnt/c/ 下）
cd /mnt/c/Users/你的用户名/Desktop/打卡小程序/
```

**② 启动服务（和 Linux 服务器完全一样的命令）**

```bash
# 构建并启动
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f
```

**④ 在 Windows 浏览器中验证**

```
→ http://localhost:8080/api/health   （直连后端 API）
```

**⑤ 清理**

```bash
# 停止服务（数据保留）
docker compose down

# 完全清理（删数据）
docker compose down -v
```

### WSL 和 Windows 的关系

```
WSL 终端里执行：docker compose up -d
       ↓
Docker Desktop（WSL2 后端）启动 Linux 容器
       ↓
容器监听端口映射到 Windows localhost
       ↓
Windows 浏览器访问 http://localhost :API_PORT 即可
```

> **Tips：** 场景三中使用的外网 nginx 在此测试时不需要配置，仅验证后端 API 是否正常工作即可。

---

## 🚀 场景三：生产 Linux 服务器部署

**目标**：通过外网 nginx 正式上线。

**适用对象**：服务器运维人员。

> 生产部署方案：
> - 你的外网 nginx 托管 `frontend/` 下的静态文件
> - nginx 将 `/api/*` 反向代理到后端容器
> - 后端仅提供纯 API（`--api-only`），不处理前端
> - 部署前需在 `frontend/config.js` 中配置 `serverUrl: 'https://你的域名'`

### 前提

```
Linux 服务器（Ubuntu 20.04+ / CentOS 7+）
Docker Engine 24.0+
Docker Compose v2.20+
certbot（Let's Encrypt SSL 证书）
域名已解析到服务器公网 IP
```

### 第 1 步：部署项目代码

```bash
# 创建部署目录
sudo mkdir -p /opt/checkin
sudo chown $USER:$USER /opt/checkin

# 获取代码（Git 克隆 或 手动上传）
cd /opt/checkin
git clone <仓库地址> .
# 或上传项目文件到 /opt/checkin/
```

### 第 2 步：启动后端容器（可选：改密码）

```bash
# .env 已预填默认密码 365，直接启动
docker compose up -d

# 如需修改密码，编辑 .env 后重新启动即可
vim .env
docker compose up -d
```

### 第 3 步：配置域名和 SSL 证书（外网 nginx）

**① DNS 解析** — 将域名（如 `checkin.your-company.com`）解析到服务器公网 IP

**② 申请 SSL 证书**（外网 nginx 需要）

```bash
sudo certbot certonly --standalone \
  -d checkin.your-company.com \
  --email your-email@company.com \
  --agree-tos --no-eff-email
```

**③ 在你的外网 nginx 中配置反向代理**

将以下配置加入你的 nginx：

```
# 前端：托管 frontend/ 目录
root /path/to/frontend;
index index.html;

# API：反向代理到后端容器
location /api/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

### 第 4 步：启动（如果第 2 步没启动）

```bash
# 一键启动
./deploy/start.sh

# 或手动执行
docker compose up -d
```

**验证：**
```
# 后端 API
curl http://localhost:8080/api/health
# → {"status":"ok","db":"sqlite"...}

# 前端页面（通过外网 nginx）
浏览器访问 → https://你的域名
应看到门禁登录页面
```

### 第 5 步：日常维护

```bash
# 查看日志
./deploy/logs.sh             # 实时滚动容器日志

# 停止
./deploy/stop.sh

# 升级版本
git pull
docker compose up -d --build

# 备份数据
sqlite3 data/checkin.db ".backup /backup/checkin_$(date +%Y%m%d).db"
```

### 常见问题

**Q：端口被占用？**
→ 修改 `.env` 中的 `API_PORT=xxxx`，换个可用端口。

**Q：数据库在哪？**
→ 项目根目录 `data/checkin.db`，备份就是拷走这个文件。

**Q：迁移到新服务器？**
→ 拷贝整个 `data/` 目录 + 项目文件到新服务器，执行 `./deploy/start.sh`。

**Q：忘了密码？**
```bash
cat /opt/checkin/.env | grep CHECKIN_PASSWORD
```
修改密码后执行 `docker compose restart` 生效。

---

## 📁 项目文件速查

| 路径 | 谁关心 | 用途 |
|------|--------|------|
| `DEPLOY.md` | 所有人 | ← 就是你现在看的这个 |
| `CHANGELOG.md` | 所有人 | 迭代记录 |
| `README.md` | 所有人 | 项目简介 |
| `docker-compose.yml` | 运维 / WSL 测试 | Docker 编排（单服务 backend） |
| `.env` / `.env.example` | 运维 | 密码、端口配置（已预填默认值） |
| `data/` | 运维 | **数据目录**，SQLite 数据库文件所在，勿删 |
| `deploy/start.sh` | 运维 | 一键启动（含环境检查） |
| `deploy/stop.sh` | 运维 | 停止服务 |
| `deploy/logs.sh` | 运维 | 查看日志 |
| `frontend/` | 运维 / 开发者 | **前端包**（放入你的 nginx 中托管） |
| `frontend/config.js` | 运维 | ★ 生产部署需改 `serverUrl: 'https://你的域名'`（不加 /api） |
| `backend/` | 运维 / 开发者 | **后端包**（api.py / dev.py / main.py + deploy/Dockerfile） |
