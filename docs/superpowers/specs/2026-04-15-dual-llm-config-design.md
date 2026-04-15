# 双 LLM 配置 + 页面设置面板 设计文档

**日期**：2026-04-15  
**状态**：已审批  
**范围**：`services/llm.py`、`main.py`、`static/index.html`、`.env`

---

## 背景

当前项目只有一套全局 LLM 配置（`LLM_API_KEY / LLM_MODEL / LLM_BASE_URL`），全部写死在 `.env`，页面无法修改。且只有点位分析（`/api/analyze-point`）真正调用了 LLM，路线建议生成（`generate_city_walk_guide`）已导入但尚未接入。

目标：
1. 将 LLM 配置拆分为两套独立配置（GLM 用于路线建议、Grok 用于点位分析）
2. 点位分析改用 Grok（OpenAI Compatible 协议）
3. 在页面侧边栏提供设置面板，保存后写回 `.env` 并热更新内存，无需重启服务

---

## 设计决策

| 维度 | 决策 |
|---|---|
| 配置持久化 | 写回 `.env` 文件，服务重启后保留 |
| 内存更新 | 保存同时更新模块级配置 dict，即改即生效 |
| UI 形式 | 侧边栏底部折叠面板，⚙ 按钮开关 |
| 字段数量 | 两个模型各三字段：Base URL / 模型 ID / API Key |
| Grok 协议 | OpenAI Compatible（`Authorization: Bearer`），非 Anthropic-compatible |
| GLM 协议 | 保持 Anthropic-compatible（`x-api-key`）不变 |

---

## 环境变量变更

`.env` 原有 `LLM_*` 三个变量迁移为 `GUIDE_LLM_*`，新增 `POINT_LLM_*`：

```env
# GLM（路线建议模型）
GUIDE_LLM_KEY=da13bde5f5954e1583cfda71314cfc75.p4Y0sOlCJW8rIr3k
GUIDE_LLM_BASE_URL=https://open.bigmodel.cn/api/anthropic
GUIDE_LLM_MODEL=glm-5.1

# Grok（点位分析模型）
POINT_LLM_KEY=sk-yYkZZS9GTslzl4EfXdn3DLglQYwhGxWVAaMkq1cF2bNVhHtM
POINT_LLM_BASE_URL=https://windhub.cc
POINT_LLM_MODEL=grok-4.20-beta
```

旧的 `LLM_API_KEY / LLM_MODEL / LLM_BASE_URL` 从 `.env` 中删除。

---

## 后端架构

### `services/llm.py` 改造

```python
# 模块级配置 dict（支持热更新）
_guide_cfg: dict = {
    "key":      os.getenv("GUIDE_LLM_KEY", ""),
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
```

**`generate_city_walk_guide`**：使用 `_guide_cfg`，保持 Anthropic-compatible 请求格式：
```python
headers = {
    "x-api-key": _guide_cfg["key"],
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}
url = f"{_guide_cfg['base_url']}/v1/messages"
json_body = {"model": _guide_cfg["model"], ...}
```

**`generate_point_analysis`**：使用 `_point_cfg`，切换为 OpenAI-compatible 请求格式：
```python
headers = {
    "Authorization": f"Bearer {_point_cfg['key']}",
    "Content-Type": "application/json",
}
url = f"{_point_cfg['base_url']}/v1/chat/completions"
json_body = {
    "model": _point_cfg["model"],
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 512,
}
# 响应字段：data["choices"][0]["message"]["content"]
```

### `models/query.py` 新增

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
    guide: dict   # key 脱敏
    point: dict   # key 脱敏
```

### `main.py` 新增端点

```python
POST /api/config
Body: ConfigRequest
→ 1. 调用 update_guide_cfg / update_point_cfg 热更新内存
→ 2. 覆写 .env 文件中对应的 6 个变量（保留其他变量不动）
→ 返回 ConfigResponse（key 脱敏：只返回前8位 + "***"）

GET /api/config
→ 返回当前生效的配置（key 同样脱敏）
```

**`.env` 写回逻辑**：读取现有 `.env` 内容，逐行替换对应 key，若 key 不存在则追加，保留其他行（`AMAP_*` 等）不变。

---

## 前端设计

### HTML 结构变更

在 `.sidebar-header` 右上角加 ⚙ 按钮：
```html
<div class="sidebar-header">
    <h2>路线规划</h2>
    <p>点击地图构建起点、途经点、终点，并生成交通路线图</p>
    <button class="settings-btn" id="settingsBtn" type="button" title="模型配置">⚙</button>
</div>
```

在 `</div><!-- sidebar ends -->` 之前插入设置面板：
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

### JS 逻辑

**页面加载时**：`GET /api/config` 预填字段（base_url / model 明文，key 显示脱敏值）。

**⚙ 按钮点击**：切换 `settingsPanel` 的 `display: none / block`。

**👁 按钮**：切换对应 input 的 `type="password" / text"`。

**保存配置**：
```js
async function saveConfig() {
    const body = {
        guide: { key: guideKey.value, base_url: guideBaseUrl.value, model: guideModel.value },
        point: { key: pointKey.value, base_url: pointBaseUrl.value, model: pointModel.value },
    };
    const resp = await fetch('/api/config', { method: 'POST', ... body });
    if (resp.ok) showToast('配置已保存');
    else showToast('保存失败');
}
```

**Key 输入框特殊处理**：若用户未修改 Key（值仍为脱敏字符串），则发送空字符串 `""`，后端检测到空字符串时跳过该字段更新（保留 `.env` 原值）。

---

## 改动范围

| 文件 | 操作 |
|---|---|
| `.env` | 重命名 `LLM_*` → `GUIDE_LLM_*`，新增 `POINT_LLM_*` |
| `services/llm.py` | 双配置 dict + 热更新函数 + `generate_point_analysis` 改为 OpenAI-compatible |
| `models/query.py` | 新增 `LLMProviderConfig / ConfigRequest / ConfigResponse` |
| `main.py` | 新增 `GET /api/config` 和 `POST /api/config` 端点 |
| `static/index.html` | ⚙ 按钮 + 设置面板 HTML / CSS / JS |

---

## 边界情况

| 场景 | 处理 |
|---|---|
| Key 输入框未修改（显示脱敏值） | 发空字符串，后端跳过该字段，保留原值 |
| `.env` 文件中某变量不存在 | 追加到文件末尾 |
| 保存时网络失败 | toast 显示"保存失败"，内存配置不变 |
| Grok API 返回错误（包括 429） | 现有 502 → 前端重试按钮机制已覆盖 |
| 服务重启 | 从 `.env` 读取，配置已持久化 |
