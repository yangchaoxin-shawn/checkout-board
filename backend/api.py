"""
作战打卡看板 — 纯 API 服务端
================================
Python 标准库实现（http.server 路由分发）。
存储: SQLite（并发安全、事务支持）
Excel: xml.etree + zipfile（标准库，无 openpyxl 依赖）
"""
import http.server
import json
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zipfile import ZIP_DEFLATED, ZipFile

# ── 配置 ──
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "checkin.db"
PASSWORD_INIT = os.environ.get("CHECKIN_PASSWORD", "365")
SECRET = os.environ.get("CHECKIN_SECRET", "checkin-secret-2026")

# ── 密码存储（SQLite 优先，支持运行时修改）──
def _init_password():
    """首次启动时将环境变量密码写入 SQLite，供 get_gate_password() 使用"""
    if not db_get("_password"):
        db_set("_password", PASSWORD_INIT)
        print(f"[init] 门禁密码已写入存储（{PASSWORD_INIT[:2]}***）")

def get_gate_password() -> str:
    """获取当前门禁密码，优先从 SQLite 读取"""
    stored = db_get("_password")
    if stored and isinstance(stored, str):
        return stored
    return PASSWORD_INIT

def set_gate_password(new_pw: str) -> bool:
    """更新门禁密码（运行时生效，无需重启）"""
    return db_set("_password", new_pw)

# ── SQLite 存储层 ──
def get_db():
    conn = sqlite3.connect(str(DB_PATH), isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT DEFAULT (datetime('now')))"
    )
    return conn

def db_get(key: str):
    with get_db() as conn:
        row = conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else None

def db_set(key: str, value) -> bool:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO kv (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, json.dumps(value, ensure_ascii=False)),
        )
    return True

def db_delete(key: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM kv WHERE key=?", (key,))
    return True

def db_list(prefix: str = "") -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key FROM kv WHERE key LIKE ? ORDER BY key",
            (prefix + "%",),
        ).fetchall()
    return [r["key"] for r in rows]

def db_count() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) as n FROM kv").fetchone()["n"]

# ── 迁移旧数据 ──
def migrate_json_to_sqlite():
    for f in sorted(DATA_DIR.glob("*.json")):
        key = f.stem
        if key == "checkin":
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            db_set(key, data)
            f.unlink()
            print(f"[migrate] {key}.json → SQLite")
        except Exception as e:
            print(f"[migrate] skip {key}: {e}")

def sanitize_key(key: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff\-:=]", "_", key) or "unnamed"

# ── Token 鉴权 ──
import hashlib
import time

def generate_token() -> str:
    ts = str(int(time.time()))
    h = hashlib.sha256(f"{SECRET}:{ts}".encode()).hexdigest()[:16]
    return f"{ts}.{h}"

def verify_token(token: str) -> bool:
    try:
        ts_str, h = token.split(".")
        if int(time.time()) - int(ts_str) > 86400:
            return False
        expected = hashlib.sha256(f"{SECRET}:{ts_str}".encode()).hexdigest()[:16]
        return h == expected
    except Exception:
        return False

# ── Excel 生成 ──
EXCEL_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
EXCEL_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
EXCEL_SHARED = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings"
ET.register_namespace("", EXCEL_NS)

def _excel_col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

def _xml_escape(s):
    if s is None: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&apos;")

def _cell_str(col, row, value, header=False):
    a1 = f"{_excel_col(col)}{row}"
    style = ' s="1"' if header else ''
    return f'<c r="{a1}"{style} t="inlineStr"><is><t xml:space="preserve">{_xml_escape(value)}</t></is></c>'

def _cell_num(col, row, value):
    a1 = f"{_excel_col(col)}{row}"
    return f'<c r="{a1}"><v>{_xml_escape(value)}</v></c>'

def generate_excel(cfg, roster_rows, checkin_rows, summary_rows):
    styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
  </fills>
  <borders count="1">
    <border><left/><right/><top/><bottom/><diagonal/></border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>'''

    content_types_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''

    rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    wb_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet4.xml"/>
  <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

    workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <bookViews>
    <workbookView xWindow="0" yWindow="0" windowWidth="0" windowHeight="0" activeTab="0"/>
  </bookViews>
  <sheets>
    <sheet name="打卡明细" sheetId="1" r:id="rId1"/>
    <sheet name="每日汇总" sheetId="2" r:id="rId2"/>
    <sheet name="团队配置" sheetId="3" r:id="rId3"/>
    <sheet name="成员花名册" sheetId="4" r:id="rId4"/>
  </sheets>
</workbook>'''

    def _build_sheet_xml(sheet_name, headers, data_rows, row_builder):
        last_col = _excel_col(len(headers))
        last_row = len(data_rows) + 1
        cells = ''.join(_cell_str(ci, 1, h, header=True) for ci, h in enumerate(headers, 1))
        rows_xml = f'<row r="1">{cells}</row>'
        for ri, row_data in enumerate(data_rows, 2):
            cells = row_builder(ri, row_data)
            rows_xml += f'<row r="{ri}">{cells}</row>'
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetViews>
    <sheetView showGridLines="1" tabSelected="0" workbookViewId="0">
      <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>
    </sheetView>
  </sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>
    {''.join(f'<col min="{i}" max="{i}" width="15" customWidth="0"/>' for i in range(1, len(headers)+1))}
  </cols>
  <sheetData>
    {rows_xml}
  </sheetData>
  <autoFilter ref="A1:{last_col}{last_row}"/>
</worksheet>'''

    def s1_builder(ri, row):
        ts = row.get("ts", 0)
        time_str = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d %H:%M") if ts else ""
        values = [row.get("date",""), time_str, row.get("name",""), row.get("type",""),
                  row.get("status",""), row.get("result",""), row.get("next","")]
        return ''.join(_cell_str(ci, ri, v) for ci, v in enumerate(values, 1))

    def s2_builder(ri, row):
        out = _cell_str(1, ri, row.get("日期",""))
        out += _cell_num(2, ri, row.get("打卡总次数", 0))
        out += _cell_num(3, ri, row.get("参与人数", 0))
        out += _cell_num(4, ri, row.get("牵引客户", 0))
        out += _cell_num(5, ri, row.get("吸引伙伴", 0))
        return out

    def s3_builder(ri, row):
        return _cell_str(1, ri, row.get("配置项","")) + _cell_str(2, ri, str(row.get("当前值","")))

    def s4_builder(ri, row):
        return _cell_str(1, ri, row.get("姓名","")) + _cell_str(2, ri, row.get("类型",""))

    s1_xml = _build_sheet_xml("打卡明细", ["日期","打卡时间","姓名","动作类型","资源状态","今日进展","下一步"], checkin_rows, s1_builder)
    s2_xml = _build_sheet_xml("每日汇总", ["日期","打卡总次数","参与人数","牵引客户","吸引伙伴"], summary_rows, s2_builder)
    s3_xml = _build_sheet_xml("团队配置", ["配置项","当前值"], cfg, s3_builder)
    s4_xml = _build_sheet_xml("成员花名册", ["姓名","类型"], roster_rows, s4_builder)

    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/styles.xml", styles_xml)
        zf.writestr("xl/worksheets/sheet1.xml", s1_xml)
        zf.writestr("xl/worksheets/sheet2.xml", s2_xml)
        zf.writestr("xl/worksheets/sheet3.xml", s3_xml)
        zf.writestr("xl/worksheets/sheet4.xml", s4_xml)
    buf.seek(0)
    return buf.read()

# ── HTTP 服务器 ──
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        xff = self.headers.get("X-Forwarded-For", "")
        client = xff.split(",")[0].strip() if xff else self.client_address[0]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {client} {format % args}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _route_api(self):
        """路由 API 路径。成功匹配返回 True，否则返回 False。"""
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            self._api_health(); return True
        if path == "/api/data" and self.command == "GET":
            self._api_get(qs); return True
        if path == "/api/list":
            self._api_list(qs); return True
        if path == "/api/export":
            self._api_export(qs); return True
        if path == "/api/export-excel":
            self._api_export_excel(qs); return True
        if path == "/api/auth" and self.command == "GET":
            self._api_auth(qs); return True
        if path == "/api/auth/check":
            self._api_check_token(); return True
        return False

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self._route_api():
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if raw:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("gbk")
            body = json.loads(text)
        else:
            body = {}
        parsed = urlparse(self.path)

        if parsed.path == "/api/data":
            return self._api_set(body)
        if parsed.path == "/api/auth":
            return self._api_login(body)
        if parsed.path == "/api/password":
            return self._api_change_password(body)
        if parsed.path == "/api/checkin":
            return self._api_checkin(body)

        self._json({"error": "not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path == "/api/data":
            return self._api_delete(qs)

        self._json({"error": "not found"}, 404)

    # ── 鉴权 ──
    def _check_auth(self) -> bool:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return verify_token(auth[7:])
        return False

    # ── API 实现 ──
    def _api_health(self):
        self._json({
            "status": "ok",
            "db": "sqlite",
            "data_rows": db_count(),
            "uptime": "running",
        })

    def _api_auth(self, qs):
        pw = qs.get("password", [""])[0]
        if pw == get_gate_password():
            self._json({"ok": True, "token": generate_token()})
        else:
            self._json({"ok": False, "error": "wrong password"}, 401)

    def _api_login(self, body):
        pw = body.get("password", "")
        if pw == get_gate_password():
            self._json({"ok": True, "token": generate_token()})
        else:
            self._json({"ok": False, "error": "wrong password"}, 401)

    def _api_check_token(self):
        """验证当前 Authorization header 中的 Token 是否有效"""
        ok = self._check_auth()
        self._json({"ok": ok})

    def _api_get(self, qs):
        key = qs.get("key", [""])[0]
        if not key:
            return self._json({"error": "missing key"}, 400)
        value = db_get(key)
        self._json({"key": key, "value": value})

    def _api_set(self, body):
        if not self._check_auth():
            return self._json({"ok": False, "error": "unauthorized"}, 401)
        key = body.get("key", "")
        value = body.get("value")
        if not key:
            return self._json({"ok": False, "error": "missing key"}, 400)

        # 打卡提交幂等性校验：同人 + 同日 + 同类型 + 同内容 → 拒绝
        if key.startswith("day:"):
            existing = db_get(key) or []
            existing_ids = {item.get("id") for item in existing}
            incoming = value if isinstance(value, list) else [value]
            new_items = [item for item in incoming if item.get("id") not in existing_ids]
            for new_item in new_items:
                for ex_item in existing:
                    if (ex_item.get("name") == new_item.get("name")
                            and ex_item.get("date") == new_item.get("date")
                            and ex_item.get("type") == new_item.get("type")
                            and ex_item.get("result") == new_item.get("result")):
                        return self._json({"ok": False, "error": "duplicate check-in", "dup": True}, 409)

        db_set(key, value)
        self._json({"ok": True})

    def _api_delete(self, qs):
        if not self._check_auth():
            return self._json({"ok": False, "error": "unauthorized"}, 401)
        key = qs.get("key", [""])[0]
        if not key:
            return self._json({"ok": False, "error": "missing key"}, 400)
        db_delete(key)
        self._json({"ok": True})

    def _api_list(self, qs):
        prefix = qs.get("prefix", [""])[0]
        keys = db_list(prefix)
        self._json({"keys": keys})

    def _api_export(self, qs):
        # 优先 Token 鉴权，其次密码查询参数（向后兼容）
        if not self._check_auth():
            pw = qs.get("password", [""])[0]
            if pw != get_gate_password():
                return self._json({"error": "unauthorized"}, 401)
        all_data = {}
        for key in db_list():
            all_data[key] = db_get(key)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="checkin_data_{ts}.json"')
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(all_data, ensure_ascii=False, indent=2).encode())

    def _api_export_excel(self, qs):
        # 优先 Token 鉴权，其次密码查询参数（向后兼容）
        if not self._check_auth():
            pw = qs.get("password", [""])[0]
            if pw != get_gate_password():
                return self._json({"error": "unauthorized"}, 401)

        cfg = db_get("config") or {}
        goal = _campaign_goal(cfg)
        config_rows = [
            {"配置项": "团队名称", "当前值": cfg.get("team", "作战")},
            {"配置项": "超级管理员", "当前值": cfg.get("superAdmin", "admin")},
            {"配置项": "年度目标截止日", "当前值": cfg.get("target", "2026-12-31")},
            {"配置项": "作战起始日", "当前值": cfg.get("start", "2026-07-13")},
            {"配置项": "年度目标(天)", "当前值": goal},
            {"配置项": "方法文档链接", "当前值": cfg.get("doc", "")},
        ]

        checkin_rows = []
        daily_map = {}
        for key in db_list("day:"):
            arr = db_get(key) or []
            for item in arr:
                checkin_rows.append(item)
                d = item.get("date", "")
                if d not in daily_map:
                    daily_map[d] = {"日期": d, "打卡总次数": 0, "参与人数": set(), "牵引客户": 0, "吸引伙伴": 0}
                daily_map[d]["打卡总次数"] += 1
                daily_map[d]["参与人数"].add(item.get("name", ""))
                if item.get("type") in ("牵引客户", "两者都有"):
                    daily_map[d]["牵引客户"] += 1
                if item.get("type") in ("吸引伙伴", "两者都有"):
                    daily_map[d]["吸引伙伴"] += 1
        checkin_rows.sort(key=lambda x: x.get("ts", 0), reverse=True)
        summary_rows = sorted(
            [{"日期": v["日期"], "打卡总次数": v["打卡总次数"], "参与人数": len(v["参与人数"]),
              "牵引客户": v["牵引客户"], "吸引伙伴": v["吸引伙伴"]} for v in daily_map.values()],
            key=lambda x: x["日期"]
        )

        roster_rows = []
        for key in db_list("roster:"):
            v = db_get(key) or {}
            name = v.get("name", key.replace("roster:", ""))
            roster_rows.append({"姓名": name, "类型": "超级管理员" if name == cfg.get("superAdmin") else "成员"})

        try:
            xlsx = generate_excel(config_rows, roster_rows, checkin_rows, summary_rows)
        except Exception as e:
            return self._json({"error": f"excel generation failed: {e}"}, 500)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="checkin_data_{ts}.xlsx"')
        self._cors()
        self.end_headers()
        self.wfile.write(xlsx)

    def _api_change_password(self, body):
        """超级管理员修改门禁密码（需要有效 Token 鉴权）"""
        if not self._check_auth():
            return self._json({"ok": False, "error": "unauthorized"}, 401)
        new_pw = body.get("password", "")
        if len(new_pw) < 2:
            return self._json({"ok": False, "error": "password too short"}, 400)
        set_gate_password(new_pw)
        # 修改后立即回收旧 Token，返回新 Token
        new_token = generate_token()
        print(f"[auth] 门禁密码已修改（{new_pw[:2]}***）")
        self._json({"ok": True, "token": new_token})

    def _api_checkin(self, body):
        """打卡提交 — 原子操作。接收单条 item，一个事务完成：幂等检查 + day 追加 + counts 更新"""
        if not self._check_auth():
            return self._json({"ok": False, "error": "unauthorized"}, 401)
        item = body.get("item", {})
        name = item.get("name", "")
        date = item.get("date", "")
        tp = item.get("type", "")
        result = item.get("result", "")
        if not name or not date or not tp or not result:
            return self._json({"ok": False, "error": "missing required fields (name, date, type, result)"}, 400)

        conn = get_db()
        try:
            # 开始事务
            conn.execute("BEGIN IMMEDIATE")

            # 1) 读 day: 数组
            row = conn.execute("SELECT value FROM kv WHERE key=?", (f"day:{date}",)).fetchone()
            day_arr = json.loads(row["value"]) if row else []

            # 2) 幂等性检查：同人+同日+同类型+同内容
            for ex in day_arr:
                if (ex.get("name") == name
                        and ex.get("date") == date
                        and ex.get("type") == tp
                        and ex.get("result") == result):
                    conn.execute("ROLLBACK")
                    return self._json({"ok": False, "error": "duplicate check-in", "dup": True}, 409)

            # 3) 追加到 day: 数组
            day_arr.append(item)
            conn.execute(
                "INSERT OR REPLACE INTO kv (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                (f"day:{date}", json.dumps(day_arr, ensure_ascii=False)),
            )

            # 4) 增量更新 counts（在同一个事务内，避免并发覆盖）
            row = conn.execute("SELECT value FROM kv WHERE key='counts'").fetchone()
            counts = json.loads(row["value"]) if row else {"customers": 0, "partners": 0}
            if tp in ("牵引客户", "两者都有"):
                counts["customers"] = counts.get("customers", 0) + 1
            if tp in ("吸引伙伴", "两者都有"):
                counts["partners"] = counts.get("partners", 0) + 1
            conn.execute(
                "INSERT OR REPLACE INTO kv (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                ("counts", json.dumps(counts, ensure_ascii=False)),
            )

            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            print(f"[checkin] transaction failed: {e}")
            return self._json({"ok": False, "error": str(e)}, 500)

        self._json({"ok": True, "item": item})


def _campaign_goal(cfg):
    from datetime import date
    try:
        ty = int((cfg.get("target") or "2026-12-31")[:4])
        start = date.fromisoformat(cfg.get("start") or "2026-07-13")
        end = date(ty, 12, 31)
        return max(1, (end - start).days + 1)
    except Exception:
        return 171


# ── 入口 ──
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="作战打卡看板 API 服务端（纯 API）")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--password", type=str, default=None)
    args = parser.parse_args()

    if args.password:
        PASSWORD_INIT = args.password

    json_files = list(DATA_DIR.glob("*.json"))
    if json_files:
        print(f"[init] 检测到 {len(json_files)} 个旧 JSON 文件，开始迁移到 SQLite...")
        migrate_json_to_sqlite()

    if not db_get("roster:admin"):
        db_set("roster:admin", {"name": "admin", "ts": int(datetime.now().timestamp() * 1000)})
        print("[init] 已创建默认管理员 admin")

    # 初始化门禁密码（若 SQLite 中尚无则从环境变量/默认值写入）
    _init_password()

    server = http.server.HTTPServer((args.host, args.port), Handler)
    display_host = "localhost" if args.host in ("0.0.0.0", "") else args.host
    print(f"[checkin] 纯 API 服务运行在 http://{display_host}:{args.port}")
    print(f"[checkin] API:  http://{display_host}:{args.port}/api/health")
    pw = get_gate_password()
    print(f"[checkin] 密码: {pw[:2]}***（可通过设置面板运行时修改）")
    print(f"[checkin] 存储: SQLite ({DB_PATH})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[checkin] 服务已停止")
        server.server_close()
