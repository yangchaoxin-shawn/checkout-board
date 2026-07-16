"""
本地开发服务器 —— 继承 api.py 纯 API，增加静态文件服务
===================================================
使用方式：
  python dev.py                      # 带静态文件（本地调试）
  python dev.py --api-only           # 纯 API（模拟生产部署）
"""
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# 导入 api 模块（后面需要修改 api.PASSWORD，所以用 import api 而非 from api import PASSWORD）
import api
from api import Handler, ROOT, DATA_DIR, DB_PATH, db_get, db_set, migrate_json_to_sqlite, get_gate_password, _init_password, _init_admin_password, set_admin_password, check_admin_password

# 静态文件根目录：frontend/（线上 nginx 也服务这里，保持一致）
STATIC_ROOT = ROOT.parent / "frontend"


class DevHandler(Handler):
    """开发用 Handler —— 增加 _serve_static 方法"""

    def __init__(self, *args, **kwargs):
        # 先初始化父类（directory=ROOT），再覆盖为项目根目录
        super().__init__(*args, **kwargs)
        self.directory = str(STATIC_ROOT)

    def do_GET(self):
        if self._route_api():
            return
        # 非 API 路径 → 静态文件
        parsed = urlparse(self.path)
        path = parsed.path
        if not getattr(self, "api_only", False):
            return self._serve_static(path)
        self._json({"error": "api only, static serving disabled"}, 404)

    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        file_path = STATIC_ROOT / path.lstrip("/")
        try:
            file_path.resolve().relative_to(STATIC_ROOT.resolve())
        except ValueError:
            return self._json({"error": "forbidden"}, 403)
        if not file_path.exists() or not file_path.is_file():
            return self._json({"error": "not found"}, 404)
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }.get(file_path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self._cors()
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())


def main():
    import argparse
    import http.server

    parser = argparse.ArgumentParser(description="作战打卡看板开发服务器")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--password", type=str, default=None)
    parser.add_argument("--api-only", action="store_true", default=False,
                        help="纯 API 模式，不托管静态文件（前后端分离用）")
    args = parser.parse_args()

    if args.password:
        api.PASSWORD_INIT = args.password

    json_files = list(DATA_DIR.glob("*.json"))
    if json_files:
        print(f"[init] 检测到 {len(json_files)} 个旧 JSON 文件，开始迁移到 SQLite...")
        migrate_json_to_sqlite()

    if not db_get("roster:admin"):
        db_set("roster:admin", {"name": "admin", "ts": int(datetime.now().timestamp() * 1000)})
        print("[init] 已创建默认管理员 admin")

    # 初始化门禁密码和超管密码
    api._init_password()
    api._init_admin_password()

    DevHandler.api_only = args.api_only

    server = http.server.HTTPServer((args.host, args.port), DevHandler)
    display_host = "localhost" if args.host in ("0.0.0.0", "") else args.host
    mode = "纯 API（生产模式）" if args.api_only else "本地开发（含静态文件）"
    print(f"[checkin] 服务运行在 http://{display_host}:{args.port}  [{mode}]")
    print(f"[checkin] API:  http://{display_host}:{args.port}/api/health")
    pw = api.get_gate_password()
    print(f"[checkin] 密码: {pw[:2]}***（可通过设置面板运行时修改）")
    print(f"[checkin] 存储: SQLite ({DB_PATH})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[checkin] 服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
