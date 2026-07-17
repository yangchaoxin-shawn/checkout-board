# Changelog

所有变更记录自**接手项目**起。版本号 V1-V5 是开发迭代阶段号，v1.0 是首个正式发布版。

## v1.0 (2026-07-14) — 正式发布

首个对外交付的稳定版本。包含 5 个迭代阶段 + Phase 4 代码清理。

### 交付后优化（Phase 4 · 2026-07-14）

- **前后端分离改造**：
  - main.py 加 `--api-only` 参数，后端可纯 API 运行
  - 创建 frontend/ + backend/ 独立目录，前端静态文件与后端 API 解耦
  - docker-compose.yml 改造为双服务（backend + frontend）
  - nginx.conf 更新为静态文件托管 + /api/ 反向代理
- **代码清理**：
  - `main.py`（596 行）拆为 `api.py`（527 行纯 API）+ `dev.py`（113 行本地开发）
  - `_serve_static` 仅保留在 `dev.py`，`api.py` 零静态文件
  - Dockerfile 改为 `COPY *.py ./`，不再含前端文件
- **安全与体验**：
  - 修复退出登录后超管按钮残留的权限 bug（3 处）
  - 所有输入框加 `autocomplete="new-password"` 等反填充属性

### 运维配置收口（2026-07-15）

- **去掉项目自带 nginx**：运维外网统一配置 nginx，项目不再包含 nginx.conf
- **docker-compose.yml**：精简为仅 backend 单服务，删 frontend 服务
- **端口可配置**：.env 新增 API_PORT 变量控制后端端口，无需改 compose
- **deploy/ 精简**：nginx.conf、旧版 Dockerfile、backend/deploy/nginx.conf 全部移除
- **文档同步**：DEPLOY.md / ops-guide.html / README.md 更新为单服务架构

### V5·打磨 — UX 与配置收口

- 7 天门禁记忆：localStorage 记住密码 7 天，免重复输入
- 部署配置独立文件 `config.js`：密码、后端类型、飞书地址集中管理
- 控制台 URL 修正：从 `0.0.0.0:8080` 改为可访问的 `localhost:8080`
- Dockerfile 补齐 config.js 复制（修复容器内 404）
- 一致性清理：版本号统一、删除冗余文件、补全 `.gitignore`

### V4·引擎 — 存储与导出重写

- 存储从 JSON 文件迁移到 **SQLite**（WAL 模式、事务、并发安全）
- Excel 导出从手写 Open XML 重构为 `xml.etree + zipfile`（零外部依赖，代码减半）
- 密码从硬编码 `PW='365'` 改为 `CHECKIN_PASSWORD` 环境变量
- Token 鉴权：SHA-256 签名，24 小时过期

### V3·权限 — 角色与管理后台

- 成员 + 超级管理员双角色系统
- 超级管理员面板：配置管理、成员增删、超管转让
- 登录校验花名册：未注册提示联系超管
- 访客模式：未登录显示「访客 / 登录」切换芯片
- 花名册与超管标识贯穿导出报表

### V2·拆分 — 工程化与多存储

- 1260 行单文件 HTML 拆分为 `index.html` + `styles.css` + `app.js` 三文件架构
- 纯 Python 标准库服务端子系统：HTTP 静态托管 + JSON 键值存储
- 5 种存储后端：server / feishu / supabase / claude / local
- 全量 API：读写删键值、列表查询、健康检查、Excel 导出
- E2E 自动化测试：11 大类 31 项，全部通过

### V1·起点 — 接手项目状态

- 单体 HTML 原型，约 1260 行
- 基础打卡 UI 与数据展示
- 暗色主题，vibe coding 产物

## v1.1 (2026-07-16) — 安全加固 + 数据链重构

### 安全加固

- **密码存储迁移至 SQLite**：密码由服务端 SQLite 存储，超管可在设置面板中运行时修改，无需改代码/重新部署
- **Token 鉴权强制**：`_check_auth()` 移除默认密码绕过，所有写操作强制 Bearer Token
- **门禁验证重构**：优先服务端验证，区分"密码错误"和"服务不可达"
- **全链路补 Token**：`SHARED.set`、`SHARED.del`、`syncFallbackData` 均补充 Authorization header
- **key 入口清洗**：`_api_set`/`_api_delete` 入口 `sanitize_key()` 过滤特殊字符
- **导出 Token 鉴权**：`/api/export-excel` 和 `/api/export` 支持 Token

### 数据链重构

- **新增 `POST /api/checkin`**：原子提交，SQLite 事务内完成幂等检查 + day 追加 + counts 更新
- **新增 `POST /api/checkin/delete`**：对称原子删除，事务内 day 移除 + counts 减
- **counts 由服务端原子维护**，前端不再 counts++
- **member: 不再独立落盘**，筛选器改为从 `day:` 动态过滤
- **/api/checkin 网络失败降级**到 localStorage 兜底

### 工程文档

- 新增 `PROJECT_WISDOM.md`（设计原则）、`ENGINEERING_CHECKLIST.md`（检查清单）、`VIBE_CODING_RETROSPECTIVE.md`（复盘）
- 引入 Git + Conventional Commits + 分支策略

## v1.2 (2026-07-17) — 超管身份强化 + UI 一致

### 安全加固

- **超管二次验证**：超管密码与门禁密码独立存储，`POST /api/auth/admin` 独立验证接口
- **打开设置/管理成员/修改密码前**，需先输入超管密码，验证状态存 sessionStorage，关闭页面自动失效
- **修改门禁密码后安全退出**：清空登录态（me=null）回到门禁页重新输入新密码
- **修改超管密码后清空验证标记**：sessionStorage 标记立即失效

### UX 修复

- 修复 `closeLogin()` 未调用 `updateSettingsBtn()` 导致的按钮残留
- 修复 `changePassword()` 后 UI 未立即刷新为访客态
- 新增 Escape 键关闭 Overlay 时正确走 `closeLogin()` 路径
- 新增全局 Escape 监听，支持多层 overlay 叠放时只关闭最顶层
- 门禁页 input 浏览器自动填充修复（readonly + onfocus 清空）
- 提示文案（sPwMsg/sAdminPwMsg）用户输入时自动清除

### UI 统一（方案 A）

- 超管验证弹窗：去掉内联 style，统一使用 `.field` 主题，modal 宽度 380→420px
- 成员过滤器下拉：浏览器原生 `<select>` 改为自定义 div 组件（圆角/阴影/hover 高亮/滑入动画）
- 修复 `adminPwErr` 被 `.err { display:none }` 吞掉的隐藏 bug

### Git

- 分支 `iter/v1.2`，共 11 个 commit

---

## 关键交付物

| 类型 | 文件 |
|------|------|
| 项目简介 | `README.md` |
| 部署手册 | `DEPLOY.md`（三种场景：Windows 开发 / WSL 测试 / Linux 生产） |
| 迭代记录 | `CHANGELOG.md`（本文件） |
| 部署编排 | `docker-compose.yml` |

## 技术指标

- 代码量：1695 行（前端） + 527 行（API 核心）+ 113 行（开发工具）
- 外部依赖：0（纯 Python 标准库 + 零前端框架）
- E2E 测试：31/31 PASS
- 跨平台：Linux 生产 / Windows WSL / macOS 本地
- 版本：v1.2（iter/v1.2 → main）
