# 双 LLM 配置 + 页面设置面板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 LLM 配置拆分为 GLM（路线建议）和 Grok（点位分析）两套独立配置，并在页面侧边栏提供设置面板，保存后写回 `.env` 并热更新内存，无需重启服务。

**Architecture:** 后端将 `services/llm.py` 中的单一全局变量改为两个模块级 dict（`_guide_cfg` / `_point_cfg`），通过 `GET/POST /api/config` 端点暴露读写接口，端点负责热更新内存 dict 并覆写 `.env`。前端在 sidebar 底部新增折叠设置面板，页面加载时预填当前配置，保存时 POST 并用返回的脱敏 key 更新输入框。

**Tech Stack:** Python / FastAPI / Pydantic v2，原生 HTML/CSS/JS（无框架），httpx（已有）

---

## 文件改动一览

| 文件 | 操作 | 主要变更 |
|---|---|---|
| `.env` | 修改 | `LLM_*` → `GUIDE_LLM_*`，新增 `POINT_LLM_*` |
| `services/llm.py` | 修改 | 双 config dict + 热更新函数 + `generate_point_analysis` 切换为 OpenAI-compatible |
| `models/query.py` | 修改 | 追加 `LLMProviderConfig`、`ConfigRequest`、`ConfigResponse` |
| `main.py` | 修改 | 新增 `_mask_key`、`_write_env_vars` 辅助函数、`GET /api/config`、`POST /api/config` |
| `static/index.html` | 修改 | CSS 新增设置面板样式、HTML 加 ⚙ 按钮和设置面板、JS 加 `loadConfig` / `saveConfig` 及绑定 |

---

## Task 1：更新 `.env` + 重构 `services/llm.py`

**Files:**
- Modify: `.env`
- Modify: `services/llm.py`

这两个文件必须同步修改——环境变量名和代码中的 `os.getenv` key 必须一一对应，拆开提交会导致服务启动失败。

- [ ] **Step 1：更新 `.env`**

将文件完整替换为以下内容（保留 AMAP 两行，删除旧 `LLM_*` 三行，写入新的六行）：

```env
AMAP_API_KEY=bba9097b12637d4cba06f5a30e018661
AMAP_SECURITY_KEY=5693981707d9c610301a59a62fdc2f62
GUIDE_LLM_KEY=da13bde5f5954e1583cfda71314cfc75.p4Y0sOlCJW8rIr3k
GUIDE_LLM_BASE_URL=https://open.bigmodel.cn/api/anthropic
GUIDE_LLM_MODEL=glm-5.1
POINT_LLM_KEY=sk-yYkZZS9GTslzl4EfXdn3DLglQYwhGxWVAaMkq1cF2bNVhHtM
POINT_LLM_BASE_URL=https://windhub.cc
POINT_LLM_MODEL=grok-4.20-beta
```

- [ ] **Step 2：重构 `services/llm.py` — 替换模块级全局变量为双 config dict**

找到第 7–9 行：
```python
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-5.1")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
```

替换为：
```python
_guide_cfg: dict = {
    "key":      os.getenv("GUIDE_LLM_KEY",      ""),
    "base_url": os.getenv("GUIDE_LLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic"),
    "model":    os.getenv("GUIDE_LLM_MODEL",    "glm-5.1"),
}
_point_cfg: dict = {
    "key":      os.getenv("POINT_LLM_KEY",      ""),
    "base_url": os.getenv("POINT_LLM_BASE_URL", "https://windhub.cc"),
    "model":    os.getenv("POINT_LLM_MODEL",    "grok-4.20-beta"),
}


def update_guide_cfg(key: str, base_url: str, model: str) -> None:
    _guide_cfg.update({"key": key, "base_url": base_url, "model": model})


def update_point_cfg(key: str, base_url: str, model: str) -> None:
    _point_cfg.update({"key": key, "base_url": base_url, "model": model})


def get_configs() -> tuple[dict, dict]:
    """Return shallow copies of current guide and point configs."""
    return dict(_guide_cfg), dict(_point_cfg)
```

- [ ] **Step 3：更新 `generate_city_walk_guide` — 使用 `_guide_cfg`（Anthropic-compatible 不变）**

找到第 167–183 行（`async with httpx.AsyncClient()` 块）：
```python
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/v1/messages",
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
```

替换为：
```python
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_guide_cfg['base_url']}/v1/messages",
            headers={
                "x-api-key": _guide_cfg["key"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": _guide_cfg["model"],
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
```

- [ ] **Step 4：更新 `generate_point_analysis` — 切换为 OpenAI-compatible（`_point_cfg`）**

找到第 227–244 行（`async with httpx.AsyncClient()` 块）：
```python
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/v1/messages",
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
```

替换为：
```python
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_point_cfg['base_url']}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_point_cfg['key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": _point_cfg["model"],
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
```

- [ ] **Step 5：验证服务启动正常**

重启服务后确认无 `ImportError` / `NameError`：

```bash
cd D:\Bob\IdeaProjects\personal\travel
uvicorn main:app --reload
```

预期：服务正常启动，无报错。

- [ ] **Step 6：手动验证点位分析仍然可用**

打开页面，点击地图任意点位，触发点位分析。预期：调用成功，返回 Grok 的分析结果（不再调用 GLM）。

- [ ] **Step 7：提交**

```bash
git add .env services/llm.py
git commit -m "refactor: 双 LLM 配置 — env 变量重命名，point analysis 切换 OpenAI-compatible"
```

---

## Task 2：`models/query.py` + `main.py` 配置端点

**Files:**
- Modify: `models/query.py`
- Modify: `main.py`

- [ ] **Step 1：在 `models/query.py` 末尾追加三个新 Pydantic 模型**

在第 65 行（文件末尾）之后追加：

```python


class LLMProviderConfig(BaseModel):
    key: str
    base_url: str
    model: str


class ConfigRequest(BaseModel):
    guide: LLMProviderConfig
    point: LLMProviderConfig


class ConfigResponse(BaseModel):
    ok: bool
    guide: dict   # {key: str (masked), base_url: str, model: str}
    point: dict   # {key: str (masked), base_url: str, model: str}
```

- [ ] **Step 2：更新 `main.py` 的 import — 引入新模型和新 llm 函数**

找到第 8–13 行：
```python
from models.query import (
    PlanRequest,
    PlanResponse,
    PointAnalysisRequest,
    PointAnalysisResponse,
)
```

替换为：
```python
from pathlib import Path

from models.query import (
    PlanRequest,
    PlanResponse,
    PointAnalysisRequest,
    PointAnalysisResponse,
    ConfigRequest,
    ConfigResponse,
)
```

找到第 27 行：
```python
from services.llm import generate_city_walk_guide, generate_point_analysis
```

替换为：
```python
from services.llm import (
    generate_city_walk_guide,
    generate_point_analysis,
    update_guide_cfg,
    update_point_cfg,
    get_configs,
)
```

- [ ] **Step 3：在 `main.py` 中添加辅助函数 `_mask_key` 和 `_write_env_vars`**

在 `@asynccontextmanager` 之前（第 30 行之前）插入：

```python
def _mask_key(key: str) -> str:
    if not key:
        return ""
    return key[:8] + "***" if len(key) >= 8 else "***"


def _write_env_vars(updates: dict[str, str]) -> None:
    """Overwrite specific key=value lines in .env; append any keys not already present."""
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    written: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            written.add(key)
        else:
            new_lines.append(line)
    for key, value in updates.items():
        if key not in written:
            new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

```

- [ ] **Step 4：在 `main.py` 末尾追加 `GET /api/config` 端点**

在第 174 行（`return await get_history(limit)`）之后追加：

```python


@app.get("/api/config")
async def get_config():
    guide_cfg, point_cfg = get_configs()
    return {
        "guide": {
            "key":      _mask_key(guide_cfg["key"]),
            "base_url": guide_cfg["base_url"],
            "model":    guide_cfg["model"],
        },
        "point": {
            "key":      _mask_key(point_cfg["key"]),
            "base_url": point_cfg["base_url"],
            "model":    point_cfg["model"],
        },
    }


@app.post("/api/config", response_model=ConfigResponse)
async def set_config(req: ConfigRequest):
    guide_cfg, point_cfg = get_configs()

    # 空字符串 = 用户未修改 key，保留原值
    guide_key = req.guide.key if req.guide.key else guide_cfg["key"]
    point_key = req.point.key if req.point.key else point_cfg["key"]

    # 热更新内存
    update_guide_cfg(guide_key, req.guide.base_url, req.guide.model)
    update_point_cfg(point_key, req.point.base_url, req.point.model)

    # 写回 .env（只写有变化的字段，key 为空时不覆写 .env 中的 key）
    env_updates: dict[str, str] = {
        "GUIDE_LLM_BASE_URL": req.guide.base_url,
        "GUIDE_LLM_MODEL":    req.guide.model,
        "POINT_LLM_BASE_URL": req.point.base_url,
        "POINT_LLM_MODEL":    req.point.model,
    }
    if req.guide.key:
        env_updates["GUIDE_LLM_KEY"] = req.guide.key
    if req.point.key:
        env_updates["POINT_LLM_KEY"] = req.point.key
    _write_env_vars(env_updates)

    guide_final, point_final = get_configs()
    return ConfigResponse(
        ok=True,
        guide={
            "key":      _mask_key(guide_final["key"]),
            "base_url": guide_final["base_url"],
            "model":    guide_final["model"],
        },
        point={
            "key":      _mask_key(point_final["key"]),
            "base_url": point_final["base_url"],
            "model":    point_final["model"],
        },
    )
```

- [ ] **Step 5：验证 GET /api/config 返回正确数据**

服务运行中，执行：

```bash
curl http://localhost:8000/api/config
```

预期输出（key 已脱敏）：
```json
{
  "guide": {"key": "da13bde5***", "base_url": "https://open.bigmodel.cn/api/anthropic", "model": "glm-5.1"},
  "point": {"key": "sk-yYkZZS***", "base_url": "https://windhub.cc", "model": "grok-4.20-beta"}
}
```

- [ ] **Step 6：验证 POST /api/config 热更新生效**

```bash
curl -X POST http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"guide":{"key":"","base_url":"https://open.bigmodel.cn/api/anthropic","model":"glm-5.1"},"point":{"key":"","base_url":"https://windhub.cc","model":"grok-4.20-beta"}}'
```

预期：返回 `{"ok": true, "guide": {...}, "point": {...}}`，`.env` 文件中 `GUIDE_LLM_BASE_URL` / `GUIDE_LLM_MODEL` / `POINT_LLM_BASE_URL` / `POINT_LLM_MODEL` 四行已更新，`GUIDE_LLM_KEY` / `POINT_LLM_KEY` 未变（因为发送了空字符串）。

- [ ] **Step 7：提交**

```bash
git add models/query.py main.py
git commit -m "feat: GET/POST /api/config — 双 LLM 配置读写端点，支持热更新和 .env 持久化"
```

---

## Task 3：`static/index.html` — 设置面板 CSS + HTML + JS

**Files:**
- Modify: `static/index.html`

这三部分（CSS / HTML / JS）共同构成设置面板 UI，强耦合，同 Task 提交。

### 3A：CSS

- [ ] **Step 1：在 `.error-banner` 块（第 1130 行 `}`）之后、`@media (max-width: 900px)`（第 1132 行）之前插入设置面板 CSS**

找到：
```css
        .error-banner {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 10px;
            padding: 14px 18px;
            color: #991b1b;
            font-size: 0.85rem;
            margin-bottom: 16px;
        }

        @media (max-width: 900px) {
```

在 `.error-banner` 块的 `}` 和 `@media` 之间插入：

```css

        /* ── Settings panel ── */
        .sidebar-header {
            position: relative;
        }

        .settings-btn {
            position: absolute;
            top: 28px;
            right: 28px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.1rem;
            color: var(--muted);
            padding: 4px;
            line-height: 1;
            transition: color 0.2s ease;
        }

        .settings-btn:hover {
            color: var(--forest);
        }

        .settings-panel {
            border-top: 1px solid rgba(138, 133, 120, 0.12);
            padding: 20px 28px;
            background: var(--cream);
            overflow-y: auto;
        }

        .settings-section {
            margin-bottom: 16px;
        }

        .settings-section h4 {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--forest);
            margin-bottom: 10px;
        }

        .settings-section label {
            display: flex;
            flex-direction: column;
            font-size: 0.78rem;
            color: var(--muted);
            gap: 3px;
            margin-bottom: 8px;
        }

        .settings-section input[type="text"],
        .settings-section input[type="password"] {
            border: 1px solid rgba(138, 133, 120, 0.3);
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 0.82rem;
            background: white;
            color: var(--text);
            outline: none;
            width: 100%;
            box-sizing: border-box;
        }

        .settings-section input:focus {
            border-color: var(--forest);
        }

        .key-input-wrap {
            position: relative;
            display: flex;
            align-items: center;
        }

        .key-input-wrap input {
            padding-right: 32px;
        }

        .eye-btn {
            position: absolute;
            right: 6px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.9rem;
            color: var(--muted);
            padding: 2px;
            line-height: 1;
        }

        .settings-actions {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 4px;
        }

        .settings-actions button {
            background: var(--forest);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 18px;
            font-size: 0.82rem;
            cursor: pointer;
            transition: opacity 0.2s ease;
        }

        .settings-actions button:hover {
            opacity: 0.85;
        }

        #saveConfigStatus {
            font-size: 0.78rem;
            color: var(--muted);
        }
```

### 3B：HTML

- [ ] **Step 2：在 `.sidebar-header` 内（第 1219–1222 行）添加 ⚙ 按钮**

找到：
```html
        <div class="sidebar-header">
            <h2>路线规划</h2>
            <p>点击地图构建起点、途经点、终点，并生成交通路线图</p>
        </div>
```

替换为：
```html
        <div class="sidebar-header">
            <h2>路线规划</h2>
            <p>点击地图构建起点、途经点、终点，并生成交通路线图</p>
            <button class="settings-btn" id="settingsBtn" type="button" title="模型配置">⚙</button>
        </div>
```

- [ ] **Step 3：在 sidebar 关闭 `</div>` 之前（第 1270 行之前）插入设置面板 HTML**

找到：
```html
        </div><!-- 此行是 .result-area 的关闭 -->

    </div>
</div>
```

具体来说，找到第 1268–1271 行：
```html
        </div>

    </div>
</div>
```

在 `    </div>` （sidebar 关闭标签，即 `<div class="sidebar">` 对应的关闭）之前插入：

```html
        <div class="settings-panel" id="settingsPanel" style="display:none">
            <div class="settings-section">
                <h4>🤖 路线建议模型 (GLM)</h4>
                <label>Base URL<input id="guideBaseUrl" type="text"></label>
                <label>模型 ID<input id="guideModel" type="text"></label>
                <label>API Key
                    <div class="key-input-wrap">
                        <input id="guideKey" type="password">
                        <button class="eye-btn" data-target="guideKey" type="button">👁</button>
                    </div>
                </label>
            </div>
            <div class="settings-section">
                <h4>🔍 点位分析模型 (Grok)</h4>
                <label>Base URL<input id="pointBaseUrl" type="text"></label>
                <label>模型 ID<input id="pointModel" type="text"></label>
                <label>API Key
                    <div class="key-input-wrap">
                        <input id="pointKey" type="password">
                        <button class="eye-btn" data-target="pointKey" type="button">👁</button>
                    </div>
                </label>
            </div>
            <div class="settings-actions">
                <button id="saveConfigBtn" type="button">保存配置</button>
                <span id="saveConfigStatus"></span>
            </div>
        </div>
```

插入后 sidebar 结尾结构如下（验证用）：
```html
        </div><!-- .result-area -->

        <div class="settings-panel" id="settingsPanel" style="display:none">
            ...
        </div>

    </div><!-- .sidebar -->
</div><!-- .main-layout -->
```

### 3C：JS

- [ ] **Step 4：在 `initMap()` 函数定义之前（第 1296 行之前）插入 `loadConfig` 和 `saveConfig` 函数**

找到：
```js
    function initMap() {
        map = new AMap.Map('map', {
```

在此之前插入：

```js
    async function loadConfig() {
        try {
            const resp = await fetch('/api/config');
            if (!resp.ok) return;
            const data = await resp.json();
            document.getElementById('guideBaseUrl').value = data.guide.base_url || '';
            document.getElementById('guideModel').value   = data.guide.model    || '';
            document.getElementById('guideKey').value     = data.guide.key      || '';
            document.getElementById('pointBaseUrl').value = data.point.base_url || '';
            document.getElementById('pointModel').value   = data.point.model    || '';
            document.getElementById('pointKey').value     = data.point.key      || '';
        } catch (_) { /* 忽略，面板保持空白 */ }
    }

    async function saveConfig() {
        const guideKeyEl = document.getElementById('guideKey');
        const pointKeyEl = document.getElementById('pointKey');
        // 若 key 仍是脱敏字符串（含 ***），发送空字符串让后端保留原值
        const body = {
            guide: {
                key:      guideKeyEl.value.includes('*') ? '' : guideKeyEl.value,
                base_url: document.getElementById('guideBaseUrl').value,
                model:    document.getElementById('guideModel').value,
            },
            point: {
                key:      pointKeyEl.value.includes('*') ? '' : pointKeyEl.value,
                base_url: document.getElementById('pointBaseUrl').value,
                model:    document.getElementById('pointModel').value,
            },
        };
        const status = document.getElementById('saveConfigStatus');
        status.textContent = '保存中…';
        try {
            const resp = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (resp.ok) {
                const data = await resp.json();
                // 用后端返回的脱敏 key 更新输入框，避免用户看到明文
                document.getElementById('guideKey').value = data.guide.key;
                document.getElementById('pointKey').value = data.point.key;
                status.textContent = '✅ 已保存';
                showToast('配置已保存');
            } else {
                status.textContent = '❌ 保存失败';
                showToast('保存失败');
            }
        } catch (_) {
            status.textContent = '❌ 网络错误';
            showToast('保存失败');
        }
        setTimeout(() => { status.textContent = ''; }, 3000);
    }

```

- [ ] **Step 5：在 `bindEvents()` 中追加设置面板相关事件绑定**

找到 `bindEvents()` 末尾（移动端拖拽把手 IIFE 之后，函数关闭 `}` 之前）：

```js
        // 移动端拖拽把手
        (function () {
            let dragStartY = 0;
            const handle = document.getElementById('routeCardDragHandle');
            if (!handle) return;
            handle.addEventListener('touchstart', function (e) {
                dragStartY = e.touches[0].clientY;
            }, { passive: true });
            handle.addEventListener('touchend', function (e) {
                const dy = e.changedTouches[0].clientY - dragStartY;
                if (dy > 30 && !routeCardCollapsed) toggleRouteCard();   // 下划 → 折叠
                if (dy < -30 && routeCardCollapsed)  toggleRouteCard();  // 上划 → 展开
            }, { passive: true });
        }());
    }
```

在 `}());` 和函数关闭 `}` 之间插入：

```js

        // ⚙ 设置面板切换
        document.getElementById('settingsBtn').addEventListener('click', function () {
            const panel = document.getElementById('settingsPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        });

        // 保存配置
        document.getElementById('saveConfigBtn').addEventListener('click', saveConfig);

        // 👁 API Key 明文切换
        document.querySelectorAll('.eye-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const input = document.getElementById(btn.dataset.target);
                input.type = input.type === 'password' ? 'text' : 'password';
            });
        });
```

- [ ] **Step 6：在 `initMap()` 中的 `bindEvents()` 调用后追加 `loadConfig()`**

找到：
```js
        map.on('click', onMapClick);
        bindEvents();
        bootstrapLocation();
```

替换为：
```js
        map.on('click', onMapClick);
        bindEvents();
        loadConfig();
        bootstrapLocation();
```

- [ ] **Step 7：端到端验证**

测试步骤：
1. 刷新页面，点击侧边栏右上角 ⚙ 按钮，确认设置面板展开，GLM / Grok 两节表单字段预填了从 `/api/config` 拿到的值（Base URL / 模型 ID 明文，Key 显示脱敏字符串如 `da13bde5***`）
2. 再次点击 ⚙，确认面板收起
3. 点击某个 Key 输入框旁的 👁 按钮，确认切换为明文/密文
4. 修改 Grok 的 Base URL 为 `https://windhub.cc`（不改 Key），点击"保存配置"
5. 确认按钮旁显示"✅ 已保存"，toast 出现"配置已保存"
6. 查看 `.env` 文件，确认 `POINT_LLM_BASE_URL` 已更新，`POINT_LLM_KEY` 未变
7. 不重启服务，触发点位分析，确认仍然正常调用 Grok（内存已热更新）

- [ ] **Step 8：提交**

```bash
git add static/index.html
git commit -m "feat: 侧边栏 ⚙ 设置面板 — 双 LLM 配置页面可编辑，保存热更新"
```

---

## 自查：Spec 覆盖确认

| Spec 需求 | 对应 Task |
|---|---|
| `GUIDE_LLM_*` / `POINT_LLM_*` 环境变量 | Task 1 Step 1 |
| `generate_city_walk_guide` 使用 `_guide_cfg`（Anthropic-compatible） | Task 1 Step 3 |
| `generate_point_analysis` 使用 `_point_cfg`（OpenAI-compatible） | Task 1 Step 4 |
| `LLMProviderConfig / ConfigRequest / ConfigResponse` 模型 | Task 2 Step 1 |
| `GET /api/config` 返回脱敏配置 | Task 2 Step 4 |
| `POST /api/config` 热更新内存 + 写回 `.env` | Task 2 Step 4 |
| 空 key 字符串 → 跳过该字段更新 | Task 2 Step 4 |
| `.env` key 不存在则追加 | Task 2 Step 3（`_write_env_vars`） |
| 页面加载时预填字段（base_url / model 明文，key 脱敏） | Task 3 Step 4（`loadConfig`） |
| ⚙ 按钮切换设置面板 | Task 3 Step 5 |
| 👁 按钮切换 key 输入框明文/密文 | Task 3 Step 5 |
| 保存后 key 输入框显示脱敏值 | Task 3 Step 4（`saveConfig` 回填） |
| 保存失败 toast 提示 | Task 3 Step 4（`saveConfig` catch 块） |
