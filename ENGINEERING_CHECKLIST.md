# 工程检查清单

> 每次改代码之前，先过一遍这份清单。
> 不是限制你，是帮你少改两遍。

---

## 一、动手前（5 分钟）

### □ 这次改什么？

用一句话说清楚：
```
这次要改的是________________
```

### □ 影响了哪些数据和接口？

列出所有被涉及的 `key` 和 API 路径：

```
key 前缀：day: / member: / config / roster / counts / _password / 其他
API 路径：/api/checkin / /api/checkin/delete / /api/data / /api/auth / 其他
```

### □ 每个接口被哪些前端代码调用了？

```
grep "调用的函数名" frontend/app.js
grep "API 路径" frontend/app.js
```

列出来，一个都不能漏。

---

## 二、改完之后（10 分钟）

### □ grep 检查"有没有漏的"

```bash
# 如果你改了某个函数的逻辑 → 查谁调了它
grep "函数名" frontend/app.js

# 如果你改了某个接口的鉴权 → 查谁调了这个接口
grep "API 路径" frontend/app.js

# 如果你改了一个数据结构的格式 → 查谁读/写了这个结构
grep "字段名" frontend/app.js
grep "字段名" backend/api.py
```

### □ 遍历三种调用者

| 调用者类型 | 例子 | 必须检查 |
|-----------|------|---------|
| 直接调用 | appendById('day:', item) | ✅ |
| 间接调用 | S.set('config') → SHARED.set → POST /api/data | ✅ |
| 兜底/同步 | syncFallbackData → POST /api/data | ✅ |

### □ 检查错误路径

```
正常路径走通之后，想三个"如果"：
如果服务端返回 401 → 前端会不会崩溃？
如果服务端返回 409 → catch 能不能接到？
如果网络断了 → 数据会不会丢？
```

---

## 三、合入之前（5 分钟）

### □ 验证的完整性

```
我测了什么（打 √）：
  [ ] 新的 API
  [ ] 老的 API 调用者
  [ ] 所有的 key 前缀
  [ ] 所有的错误返回码
  [ ] 网络不可达时的降级
```

### □ 有没有"隐含假设"被悄悄改变了？

```
例：
  改动前：POST /api/data 不需要鉴权
  改动后：POST /api/data 需要 Token
  隐含假设改变了 → 所有调 POST /api/data 的地方都必须改
```

---

## 四、一个具体的例子：你这次踩过的坑

```
改动：_check_auth() 移除默认密码绕过

应该做的检查清单：
  [√] 新接口 /api/checkin 带了 Token
  [√] 新接口 /api/checkin/delete 带了 Token
  [×] SHARED.set → POST /api/data → 没带 Token ❌
  [×] SHARED.del → DELETE /api/data → 没带 Token ❌
  [×] syncFallbackData → POST /api/data → 没带 Token ❌
  [×] 转管理员 / 加成员 / 删成员 / 改配置 → 全部失效 ❌
```

如果当时过了前面的检查清单，这三个漏掉的点至少能发现两个。

---

## 五、最终提醒

**"功能跑通了"不等于"系统没坏"。**

你改了一个接口的鉴权，这个接口被 10 个地方调用——你只测了新写的 1 个，另外 9 个悄悄坏了。

每一步多花 5 分钟 grep，能省后面 2 小时的 debug。
