# On-Call 助手项目实施方案

## 1. 项目目标

本项目需要实现一个 On-Call 助手 Web 应用，帮助值班工程师从部门 SOP HTML 文档中快速找到故障处理方案，并在最终阶段通过对话方式回答线上故障处理问题。

系统需要同时提供 HTTP API 和前端页面，并按照三个独立阶段实现：

| 阶段 | 路由前缀 | 分值 | 目标 |
| --- | --- | --- | --- |
| Phase 1 | `/v1` | 30 | 基于关键词检索 SOP 文档 |
| Phase 2 | `/v2` | 30 | 支持自然语言语义搜索 |
| Phase 3 | `/v3` | 40 | 通过受限工具读取 SOP，并以 Agent 对话形式回答问题 |

项目代码统一组织在：

```text
oncall/code/
```

原始题目与数据来源位于：

```text
coding-exam/question-1/
```

## 2. 需要实现的功能

### 2.1 基础文档处理

所有阶段都依赖统一的 SOP 文档解析能力：

- 读取 `data/` 目录下的 HTML 文件。
- 提取文档 ID、标题和正文。
- 标题优先从 `<title>` 或 `<h1>` 中提取。
- 正文只保留用户可见内容。
- 必须排除 `script`、`style`、`noscript` 等非正文标签。
- 支持后续新增 SOP 文件，不能写死只支持 10 个文件。

这是项目最重要的基础能力。特别是 `replication` 这个验证词只应该出现在 `script` 标签中，搜索时必须返回空。

### 2.2 Phase 1：关键词搜索

需要实现：

- `POST /v1/documents`
  - 新增或更新文档。
  - 请求体包含 `id` 和 `html`。
  - 返回文档 `id` 和 `title`。
- `GET /v1/search?q={query}`
  - 根据关键词搜索清洗后的标题和正文。
  - 英文大小写不敏感。
  - 中文支持直接包含匹配。
  - 特殊字符，例如 `&`，需要正确处理。
  - 返回 `query` 和 `results`。
- `GET /v1`
  - 关键词搜索页面。
  - 至少包含输入框、搜索按钮、结果列表。

搜索结果结构：

```json
{
  "query": "OOM",
  "results": [
    {
      "id": "sop-001",
      "title": "后端服务 On-Call SOP",
      "snippet": "...单服务OOM崩溃...",
      "score": 1.0
    }
  ]
}
```

必须满足的验证样例：

| 查询 | 期望结果 |
| --- | --- |
| `GET /v1/search?q=OOM` | 返回 `sop-001` |
| `GET /v1/search?q=故障` | 返回多个文档 |
| `GET /v1/search?q=replication` | 返回空 |
| `GET /v1/search?q=CDN` | 返回 `sop-003` 和 `sop-010` |
| `GET /v1/search?q=&` | 返回正文中包含 `&` 字符的文档 |

### 2.3 Phase 2：语义搜索

需要实现：

- `GET /v2/search?q={query}`
  - 支持自然语言查询。
  - 查询词不需要在 SOP 中精确出现。
  - 结果按相关性排序。
  - 返回 `id`、`title`、`snippet`、`score`。
- `GET /v2`
  - 语义搜索页面。

推荐使用本地可控的 hybrid search：

- 复用 Phase 1 的关键词搜索得分。
- 增加领域词表和同义词映射。
- 为每份 SOP 维护部门、故障类型、典型表达等标签。
- 对自然语言查询做意图增强后再打分。

不建议强依赖外部 embedding API。面试演示时，API Key、网络和外部模型响应都可能造成不稳定。

必须满足的验证样例：

| 查询 | 期望结果 |
| --- | --- |
| `GET /v2/search?q=服务器挂了` | `sop-001` 和 `sop-004` 靠前 |
| `GET /v2/search?q=黑客攻击` | `sop-005` 靠前 |
| `GET /v2/search?q=机器学习模型出问题` | `sop-008` 靠前 |

### 2.4 Phase 3：On-Call 助手 Agent

需要实现：

- `GET /v3`
  - 对话页面。
  - 展示用户消息、Agent 回复、工具调用记录。
- `POST /v3/chat`
  - 接收用户问题。
  - 定位相关 SOP。
  - 使用 `readFile(fname)` 读取明确文件。
  - 根据读取内容生成可执行回答。

建议请求格式：

```json
{
  "message": "数据库主从延迟超过30秒怎么处理？"
}
```

建议响应格式：

```json
{
  "answer": "建议先确认主从复制状态、检查延迟来源...",
  "toolCalls": [
    {
      "tool": "readFile",
      "args": {
        "fname": "sop-002.html"
      }
    }
  ]
}
```

Agent 工具限制：

- 只能使用 `readFile(fname: string) -> string`。
- 只能读取 `data/` 目录下的文件。
- 只能按明确文件名读取。
- 不能列目录。
- 不能使用通配符。
- 不能通过 `../` 读取项目外文件。
- 对话过程必须展示工具调用过程。

Agent 回答要求：

- 必须先读取相关 SOP，再回答。
- 回答应包含处理步骤、排查方向、升级建议和禁止操作。
- P0 或跨团队故障允许读取多个 SOP 并综合回答。

必须满足的验证样例：

| 用户问题 | 期望行为 |
| --- | --- |
| 数据库主从延迟超过30秒怎么处理？ | 读取 `sop-002.html` |
| 服务 OOM 了怎么办？ | 读取 `sop-001.html` |
| P0 故障的响应流程是什么？ | 综合多个 SOP |
| 怀疑有人入侵了系统 | 读取 `sop-005.html` |
| 推荐结果质量下降了 | 读取 `sop-008.html` |

## 3. 推荐技术栈

推荐使用：

- 后端框架：Python + FastAPI
- HTML 解析：BeautifulSoup4
- 页面渲染：Jinja2
- 前端：原生 HTML、CSS、JavaScript
- 搜索实现：
  - Phase 1：本地关键词匹配和简单相关性打分
  - Phase 2：本地 hybrid search，同义词映射加权
- 测试：pytest
- 启动服务：uvicorn

选择理由：

- FastAPI 适合快速实现 HTTP API，接口清晰，测试方便。
- BeautifulSoup 能稳定清洗 HTML。
- 原生前端足够满足题目演示要求，避免引入不必要复杂度。
- 本地语义增强比外部模型更适合面试题演示，稳定、可控、无 API Key 依赖。

## 4. 代码目录组织

项目实现代码放在 `oncall/code/` 下，推荐结构如下：

```text
oncall/code/
  app/
    main.py
    models.py

    routes/
      v1.py
      v2.py
      v3.py

    services/
      document_store.py
      html_parser.py
      keyword_search.py
      semantic_search.py
      agent.py
      tools.py

    templates/
      base.html
      v1.html
      v2.html
      v3.html

    static/
      app.css
      app.js

  data/
    sop-001.html
    sop-002.html
    ...
    index.json

  tests/
    test_html_parser.py
    test_v1_search.py
    test_v2_search.py
    test_agent.py

  README.md
  requirements.txt
```
核心原则是把几块逻辑拆开：

  - html_parser.py：只负责 HTML 清洗和标题/正文提取。
  - document_store.py：负责加载和管理 SOP 文档。
  - keyword_search.py：Phase 1。
  - semantic_search.py：Phase 2。
  - agent.py：问题分类、SOP 定位、回答生成。
  - tools.py：实现受限的 readFile(fname)，重点做安全校验。

目录职责：

| 路径 | 职责 |
| --- | --- |
| `app/main.py` | 创建 FastAPI 应用，注册路由，挂载静态资源 |
| `app/models.py` | 定义 Document、SearchResult、ChatResponse 等数据结构 |
| `app/routes/v1.py` | Phase 1 API 和页面路由 |
| `app/routes/v2.py` | Phase 2 API 和页面路由 |
| `app/routes/v3.py` | Phase 3 对话 API 和页面路由 |
| `app/services/html_parser.py` | HTML 清洗、标题和正文提取 |
| `app/services/document_store.py` | 加载、保存和查询文档集合 |
| `app/services/keyword_search.py` | 关键词搜索和 snippet 生成 |
| `app/services/semantic_search.py` | 语义搜索、同义词扩展和混合打分 |
| `app/services/tools.py` | 受限 `readFile(fname)` 工具 |
| `app/services/agent.py` | SOP 定位、工具调用编排和回答生成 |
| `app/templates/` | `/v1`、`/v2`、`/v3` 页面模板 |
| `app/static/` | 页面样式和前端交互脚本 |
| `data/` | SOP HTML 数据和可选索引文件 |
| `tests/` | 自动化测试 |

## 5. 实现顺序

### 阶段一：基础文档处理

目标：

- 能读取 `data/` 下所有 HTML。
- 能提取 `id`、`title`、`text`。
- 能删除 `script`、`style`、`noscript`。

建议先写测试：

- 文档标题能正确提取。
- 正文不包含脚本内容。
- `replication` 不出现在清洗后的正文里。

### 阶段二：Phase 1 关键词搜索

目标：

- 完成 `/v1/documents`。
- 完成 `/v1/search`。
- 完成 `/v1` 页面。

优先跑通：

- `OOM`
- `故障`
- `replication`
- `CDN`
- `&`

### 阶段三：Phase 2 语义搜索

目标：

- 完成 `/v2/search`。
- 完成 `/v2` 页面。
- 增加领域词表和同义词映射。

建议先覆盖这些语义映射：

| 用户表达 | 关联领域 |
| --- | --- |
| 服务器挂了、服务不可用、服务崩了 | 后端服务、SRE |
| 黑客攻击、入侵、漏洞、异常登录 | 安全团队 |
| 机器学习、模型、推荐质量、GPU | AI & 算法 |
| 主从延迟、慢查询、连接池 | 数据库 DBA |
| 白屏、资源加载失败、兼容性 | 前端、CDN |

### 阶段四：Phase 3 Agent

目标：

- 实现安全的 `readFile(fname)`。
- 实现 `/v3/chat`。
- 实现 `/v3` 对话页面。
- 展示工具调用记录。

建议流程：

1. 根据用户问题识别领域。
2. 定位一个或多个候选 SOP 文件。
3. 调用 `readFile("具体文件名")`。
4. 从读取内容中提取处理步骤。
5. 返回答案和 `toolCalls`。

### 阶段五：项目整理

目标：

- 补齐 `oncall/code/README.md`。
- 写清启动命令。
- 写清 API 示例。
- 写清验证命令。
- 写清已知限制。
- 确保浏览器可以访问 `/v1`、`/v2`、`/v3`。

## 6. 面试官重点关注点

### 6.1 HTML 清洗正确性

这是 Phase 1 最容易被精准验证的点。`replication` 必须返回空，因为它只应该出现在 `script` 标签内。如果误命中，说明 HTML 清洗不合格。

### 6.2 API 完整性

面试官可能直接访问：

```text
POST /v1/documents
GET /v1/search
GET /v2/search
GET /v1
GET /v2
GET /v3
```

所有接口都应返回稳定结果。

### 6.3 搜索结果格式

每条搜索结果都应包含：

- `id`
- `title`
- `snippet`
- `score`

结果必须按相关性排序。

### 6.4 语义搜索稳定性

语义搜索不一定要使用大模型，但必须能稳定通过验收样例。面试官重点看自然语言表达是否能关联到正确 SOP。

### 6.5 Agent 工具约束

`readFile` 是 Phase 3 的核心安全点。需要特别防御：

- `../`
- 绝对路径
- 子目录绕过
- 通配符
- 空文件名
- 非 `data/` 内文件

### 6.6 Agent 是否基于 SOP 回答

Agent 不能只做模板回复。它应该展示读取了哪些文件，并基于文件内容总结处理步骤。

### 6.7 可演示性

最终项目应能通过浏览器和 HTTP 请求验证。README 中必须提供明确启动方式和验证命令。

### 6.8 可维护性

文档解析、关键词搜索、语义搜索、Agent 逻辑应解耦。三个阶段复用同一套文档结构和 HTML 清洗逻辑，不要重复实现。

## 7. 验收清单

### API 验收

- [ ] `POST /v1/documents` 可新增或更新文档。
- [ ] `GET /v1/search?q=OOM` 返回 `sop-001`。
- [ ] `GET /v1/search?q=故障` 返回多个文档。
- [ ] `GET /v1/search?q=replication` 返回空。
- [ ] `GET /v1/search?q=CDN` 返回 `sop-003` 和 `sop-010`。
- [ ] `GET /v1/search?q=&` 能正确处理特殊字符。
- [ ] `GET /v2/search?q=服务器挂了` 返回 `sop-001` 和 `sop-004` 靠前。
- [ ] `GET /v2/search?q=黑客攻击` 返回 `sop-005` 靠前。
- [ ] `GET /v2/search?q=机器学习模型出问题` 返回 `sop-008` 靠前。
- [ ] `/v3` 页面可完成对话。
- [ ] Agent 响应中展示 `readFile` 工具调用过程。

### 页面验收

- [ ] `/v1` 可以输入关键词并展示搜索结果。
- [ ] `/v2` 可以输入自然语言并展示语义搜索结果。
- [ ] `/v3` 可以输入问题并展示对话历史。
- [ ] `/v3` 可以展示 Agent 读取了哪些文件。

### Agent 验收

- [ ] “数据库主从延迟超过30秒怎么处理？”读取 `sop-002.html`。
- [ ] “服务 OOM 了怎么办？”读取 `sop-001.html`。
- [ ] “P0 故障的响应流程是什么？”综合多个 SOP。
- [ ] “怀疑有人入侵了系统”读取 `sop-005.html`。
- [ ] “推荐结果质量下降了”读取 `sop-008.html`。
