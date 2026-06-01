# On-Call 助手

> 面向值班工程师的 SOP 检索与问答 Web 应用。  
> 输入告警现象或故障问题，系统会从部门 On-Call SOP 中定位相关文档，并给出可演示的搜索结果或处理建议。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-HTTP%20API-009688)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-4B8BBE)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-HTML%20Parser-6A994E)
![DeepSeek](https://img.shields.io/badge/DeepSeek-Optional%20Agent-111827)

## 项目在做什么

这个项目来自 `coding-exam/question-1`，目标是实现一个可通过浏览器和 HTTP API 验证的 On-Call 助手。

系统读取 `data/` 目录中的 SOP HTML 文档，提供三个阶段能力：

| 阶段 | 页面 | API | 能力 |
| --- | --- | --- | --- |
| Phase 1 | `/v1` | `GET /v1/search` | 关键词搜索 SOP |
| Phase 2 | `/v2` | `GET /v2/search` | 自然语言语义搜索 |
| Phase 3 | `/v3` | `POST /v3/chat` | Agent 对话，展示 `readFile` 工具调用 |

浏览器入口：

```text
http://127.0.0.1:8000/v1
http://127.0.0.1:8000/v2
http://127.0.0.1:8000/v3
```

## 技术栈

| 模块 | 技术 | 用途 |
| --- | --- | --- |
| 后端 | FastAPI | HTTP API、页面路由 |
| 服务运行 | Uvicorn | ASGI 服务启动 |
| HTML 解析 | BeautifulSoup4 | 清洗 SOP HTML，排除脚本内容 |
| 页面 | Jinja2 + 原生 JS/CSS | 三个演示页面 |
| 语义搜索 | 本地 hybrid fallback | 无 embedding 依赖的稳定语义匹配 |
| Agent | 本地 Agent / DeepSeek API | SOP 定位与回答生成 |
| 依赖管理 | uv | 虚拟环境和依赖安装 |
| 验证 | pytest + `scripts/verify.py` | 单元测试和接口验收 |

## 快速启动

```powershell
cd C:\Users\he\Desktop\aicoding\oncall\code
uv venv
uv sync
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

启动后打开：

```text
http://127.0.0.1:8000/v1
```

也可以使用脚本启动：

```powershell
.\scripts\run_dev.ps1
```

FastAPI 自动生成的接口文档：

```text
http://127.0.0.1:8000/docs
```

## DeepSeek 配置

Phase 3 支持两种模式：

- `AGENT_MODE=local`：开发测试使用本地 Agent，不消耗 API。
- `AGENT_MODE=deepseek`：上线前验证时调用 DeepSeek API。

复制示例配置：

```powershell
Copy-Item .env.example .env
```

在 `.env` 中配置：

```text
AGENT_MODE=local
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_PROXY=http://127.0.0.1:7897
```

说明：

- `DEEPSEEK_PROXY` 可选。如果终端需要本机代理访问 DeepSeek，可保留；如果可直连，可留空或删除。
- 即使使用 DeepSeek，模型也不能直接访问文件系统。
- 所有文件读取都由后端 `readFile(fname)` 执行，并限制在 `data/` 目录内。

## API 示例

健康检查：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

关键词搜索：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/v1/search?q=OOM"
Invoke-RestMethod "http://127.0.0.1:8000/v1/search?q=CDN"
Invoke-RestMethod "http://127.0.0.1:8000/v1/search?q=%26"
```

新增或更新文档：

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/v1/documents" `
  -ContentType "application/json" `
  -Body '{"id":"sop-test","html":"<html><title>测试 SOP</title><body><p>visible_keyword</p></body></html>"}'
```

语义搜索：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/v2/search?q=%E6%9C%8D%E5%8A%A1%E5%99%A8%E6%8C%82%E4%BA%86"
Invoke-RestMethod "http://127.0.0.1:8000/v2/search?q=%E9%BB%91%E5%AE%A2%E6%94%BB%E5%87%BB"
Invoke-RestMethod "http://127.0.0.1:8000/v2/search?q=%E6%9C%BA%E5%99%A8%E5%AD%A6%E4%B9%A0%E6%A8%A1%E5%9E%8B%E5%87%BA%E9%97%AE%E9%A2%98"
```

Agent 对话：

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/v3/chat" `
  -ContentType "application/json" `
  -Body '{"message":"服务 OOM 了怎么办？"}'
```

## Phase 1：关键词搜索

实现点：

- 读取 `data/` 下的 SOP HTML 文件。
- 解析文档 `id`、`title` 和正文。
- 使用 BeautifulSoup 删除 `script`、`style`、`noscript` 标签。
- 英文关键词大小写不敏感。
- 中文关键词使用包含匹配。
- 返回 `id`、`title`、`snippet`、`score`。
- `/v1` 页面支持输入关键词、示例查询和结果展示。

验收点：

| 查询 | 期望 |
| --- | --- |
| `OOM` | 返回 `sop-001` |
| `故障` | 返回多个文档 |
| `replication` | 返回空 |
| `CDN` | 返回 `sop-003` 和 `sop-010` |
| `&` | 能正确处理特殊字符 |

## Phase 2：语义搜索

实现点：

- 不依赖真实 embedding 服务，使用本地 hybrid fallback。
- 复用 Phase 1 的关键词搜索作为弱基础分。
- 为每个 SOP 维护语义画像，包括自然语言表达和领域关键词。
- 按语义命中和关键词命中混合打分。
- 结果按相关性排序。
- `/v2` 页面支持自然语言输入、示例查询和结果展示。

验收点：

| 查询 | 期望 |
| --- | --- |
| `服务器挂了` | `sop-001`、`sop-004` 靠前 |
| `黑客攻击` | `sop-005` 靠前 |
| `机器学习模型出问题` | `sop-008` 靠前 |

## Phase 3：Agent 对话

实现点：

- 页面 `/v3` 支持输入问题并展示回答。
- API 为 `POST /v3/chat`。
- Agent 首先读取 `readFile("index.json")`。
- 然后读取明确 SOP 文件，例如 `readFile("sop-002.html")`。
- 前端展示完整 `readFile` 工具调用过程。
- P0 问题会综合多个 SOP。
- `AGENT_MODE=deepseek` 时使用 DeepSeek 生成回答；默认 `local` 模式使用本地 Agent。

工具约束：

| 约束 | 实现 |
| --- | --- |
| 只能读 `data/` | `tools.read_file` 限制根目录 |
| 只能按明确文件名读取 | 拒绝路径和子目录 |
| 不能列目录 | Agent 无目录枚举接口 |
| 不能使用通配符 | 拒绝 `*?[]{}` |
| 防路径穿越 | 拒绝 `../README.md` |

验收点：

| 用户问题 | 期望 |
| --- | --- |
| `数据库主从延迟超过30秒怎么处理？` | 读取 `sop-002.html` |
| `服务 OOM 了怎么办？` | 读取 `sop-001.html` |
| `P0 故障的响应流程是什么？` | 综合多个 SOP |
| `怀疑有人入侵了系统` | 读取 `sop-005.html` |
| `推荐结果质量下降了` | 读取 `sop-008.html` |

## 评分点对照表

| 题目要求 | 实现位置 | 验证位置 |
| --- | --- | --- |
| `/v1` 搜索页面 | `app/templates/v1.html`、`app/static/app.js` | 浏览器访问 `/v1` |
| `POST /v1/documents` | `app/routes/v1.py` | `tests/test_phase1.py` |
| `GET /v1/search` | `app/routes/v1.py`、`app/services/keyword_search.py` | `scripts/verify.py` |
| HTML 清洗排除脚本内容 | `app/services/html_parser.py` | `replication` 返回空、`tests/test_phase1.py` |
| `/v2` 语义搜索页面 | `app/templates/v2.html` | 浏览器访问 `/v2` |
| `GET /v2/search` | `app/routes/v2.py`、`app/services/semantic_search.py` | `tests/test_phase2.py` |
| `/v3` Agent 对话页面 | `app/templates/v3.html`、`app/static/app.js` | 浏览器访问 `/v3` |
| `POST /v3/chat` | `app/routes/v3.py`、`app/services/agent.py` | `scripts/verify.py` |
| 只能通过 `readFile(fname)` 读取文件 | `app/services/tools.py` | `tests/test_security.py` |
| 展示工具调用过程 | `app/static/app.js` | `/v3` 页面和 `toolCalls` 响应 |
| DeepSeek 可选模式 | `app/services/deepseek_client.py`、`.env.example` | `AGENT_MODE=deepseek` |

## 验证命令

单元测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

接口验收脚本：

```powershell
.\.venv\Scripts\python.exe scripts\verify.py --base-url http://127.0.0.1:8000
```

一键验收脚本会自动启动临时服务、运行单元测试和接口验证：

```powershell
.\scripts\verify_all.ps1
```

验证脚本会检查：

- `/health`
- Phase 1 的 5 个验收查询
- `GET /v1/search?q=&` 这种未编码特殊字符请求
- Phase 2 的 3 个语义查询
- Phase 3 的 5 个 Agent 问题和 `readFile` 文件记录

## 错误处理与安全验证

- `/v1/documents` 缺少 `id` 或 `html` 时返回 400。
- 空搜索返回空结果，不抛异常。
- `readFile("../README.md")` 会被拒绝。
- `readFile("*.html")` 会被拒绝。
- `readFile("nested/sop-001.html")` 会被拒绝。
- DeepSeek 不可用时会回退到本地 Agent，保证演示不断路。

## 页面截图

### `/v1` 关键词搜索

![Phase 1 关键词搜索](../screenshot/front/v1.png)

### `/v2` 语义搜索

![Phase 2 语义搜索](../screenshot/front/v2.png)

### `/v3` Agent 对话

![Phase 3 Agent 对话](../screenshot/front/v3.png)

## 项目结构

```text
app/
  main.py
  models.py
  routes/
    v1.py
    v2.py
    v3.py
  services/
    agent.py
    deepseek_client.py
    document_store.py
    html_parser.py
    keyword_search.py
    semantic_search.py
    tools.py
  static/
    app.css
    app.js
  templates/
    v1.html
    v2.html
    v3.html
data/
  index.json
  sop-001.html ... sop-010.html
scripts/
  run_dev.ps1
  verify.py
  verify_all.ps1
tests/
  conftest.py
  test_phase1.py
  test_phase2.py
  test_phase3_agent.py
  test_security.py
```

## 已知限制

- Phase 2 是本地语义 fallback，不是真实向量数据库或 embedding 检索。
- `POST /v1/documents` 新增文档保存在内存中，服务重启后不会持久化。
- DeepSeek 模式依赖网络、API Key 和代理配置；不可用时会回退到本地 Agent。
- 本地 Agent 主要面向题目验收样例，不是通用推理系统。
- 前端用于演示功能，没有登录、多用户会话或权限控制。
