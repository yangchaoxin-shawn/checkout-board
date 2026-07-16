/* 每日作战打卡看板 · 部署配置文件
   ============================================
   部署前只需修改此文件，app.js 不用动。
   - PW 为首次部署默认密码，上线后超管可在设置面板中运行时修改
   - 后端类型改 type（server/feishu/supabase/local）
   - 飞书代理地址改 proxyUrl
   - 自定义服务地址改 serverUrl
*/
window.CHECKIN_CONFIG = {
  // ── 门禁密码（首次部署默认值，上线后可在设置面板中修改）──
  PW: '365',

  // ── 后端存储 ──
  backend: {
    type: 'server',      // 'server' | 'feishu' | 'supabase' | 'local'
    proxyUrl: '',        // 飞书代理地址，例：https://xxx.workers.dev
    serverUrl: 'http://localhost:8080',  // 本地调试：后端地址；生产部署改为 https://你的域名（不加 /api）
    // supabase 用：
    url: '', key: ''
  }
};

/* ============ 以下由代码自动推导，一般不用改 ============ */
var PW = window.CHECKIN_CONFIG.PW;
const BOARD_CONFIG = window.CHECKIN_CONFIG;
const CLAUDE  = (typeof window.storage !== 'undefined' && !!window.storage);
const B       = BOARD_CONFIG.backend || {};
const FEISHU_ON = B.type==='feishu'   && !!B.proxyUrl;
const REST_ON   = B.type==='supabase' && !!(B.url && B.key);
const SERVER_ON  = B.type==='server';
const SERVER_URL = B.serverUrl || (() => {
  if (typeof location === 'undefined') return '';
  const origin = location.origin;
  const pathParts = location.pathname.split('/').filter(Boolean);
  const last = pathParts[pathParts.length - 1] || '';
  if (last.endsWith('.html') || last.endsWith('.htm')) {
    return origin + '/' + pathParts.slice(0, -1).join('/');
  }
  return origin;
})();
const BACKEND_MODE = FEISHU_ON ? 'feishu' : (REST_ON ? 'rest' : (SERVER_ON ? 'server' : (CLAUDE ? 'claude' : 'local')));
const restHeaders = REST_ON ? { apikey:B.key, Authorization:'Bearer '+B.key, 'Content-Type':'application/json' } : {};
