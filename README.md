# DocuMind

[English](#english) | [简体中文](#中文)

## English

DocuMind is a private knowledge-base question-answering demo built with retrieval-augmented generation (RAG). It combines query rewriting, vector search, BM25 keyword search, reciprocal rank fusion (RRF), and a BGE cross-encoder reranker. Answers are generated from retrieved document chunks and streamed to the browser.

> **Project status:** This repository is an early-stage demo, not a production-ready enterprise service. It currently supports ingestion from a PDF file path on the server, and it does not include authentication, authorization, or an upload UI.

### Contents

- [Features](#features)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Using the application](#using-the-application)
- [API reference](#api-reference)
- [Project layout](#project-layout)
- [Current limitations](#current-limitations)

### Features

- Parse PDF files page by page and split their text into overlapping chunks.
- Persist document chunks and metadata in a local Chroma database.
- Rewrite a user question into up to three retrieval-oriented queries.
- Retrieve with both semantic vector search and BM25 keyword search, then combine rankings using RRF.
- Rerank candidates with `BAAI/bge-reranker-base` before passing the best chunks to the language model.
- Stream generated answers to the web page using Server-Sent Events (SSE).
- Serve a simple browser interface and FastAPI's interactive API documentation.

### Technology stack

| Area | Technology |
| --- | --- |
| Language and runtime | Python 3.12+ |
| Web framework and ASGI server | FastAPI, Uvicorn |
| LLM | DeepSeek Chat through the OpenAI-compatible API |
| Embeddings | Alibaba Cloud DashScope compatible embeddings API, `text-embedding-v2` |
| Vector store | ChromaDB persistent client |
| Keyword search and fusion | `rank-bm25`, Reciprocal Rank Fusion (RRF) |
| Reranking | Sentence Transformers `CrossEncoder`, `BAAI/bge-reranker-base` |
| PDF parsing and text splitting | pypdf, in-project character-based splitter |
| Configuration | `python-dotenv` |
| Browser UI | Static HTML and JavaScript |

### Architecture

```text
                         ┌──────────────────────────────┐
                         │       Browser / User         │
                         └──────────────┬───────────────┘
                                        │ POST /api/chat
                                        ▼
                         ┌──────────────────────────────┐
                         │ FastAPI chat endpoint        │
                         │ app/api/chat.py              │
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ Query rewrite                │
                         │ DeepSeek: 1-3 search queries │
                         └──────────────┬───────────────┘
                                        ▼
              ┌─────────────────────────┴─────────────────────────┐
              │                                                   │
              ▼                                                   ▼
    ┌─────────────────────┐                           ┌─────────────────────┐
    │ Chroma vector search│                           │ BM25 keyword search │
    │ top 10 candidates   │                           │ top 10 candidates   │
    └──────────┬──────────┘                           └──────────┬──────────┘
               └─────────────────────────┬───────────────────────┘
                                         ▼
                         ┌──────────────────────────────┐
                         │ RRF hybrid ranking           │
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ BGE Cross-Encoder reranking  │
                         │ keep top 2 per rewritten query│
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ Deduplicate; keep up to 5    │
                         │ chunks and build context     │
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ DeepSeek Chat                │
                         │ answer grounded in context   │
                         └──────────────┬───────────────┘
                                        │ streamed SSE chunks
                                        ▼
                         ┌──────────────────────────────┐
                         │       Browser / User         │
                         └──────────────────────────────┘
```

#### Document ingestion

```text
PDF file path on the server
        -> pypdf extracts each page
        -> split into 500-character chunks (50-character overlap)
        -> DashScope creates embeddings
        -> Chroma persists chunk text and source/page metadata
        -> BM25 in-memory index is rebuilt
```

For each rewritten query, the application asks both retrieval methods for up to 10 candidates and combines their rankings using RRF. The reranker keeps up to two candidates per rewritten query; identical chunk texts are deduplicated, and no more than five chunks are included in the final LLM context.

### Requirements

- Python **3.12 or newer**
- [`uv`](https://docs.astral.sh/uv/) for dependency and virtual-environment management
- A DeepSeek API key
- A DashScope API key with access to the compatible embeddings API
- Internet access for the LLM and embedding APIs; the reranker model may also need to be downloaded the first time it is loaded
- A text-based PDF (scanned/image-only PDFs need OCR, which is not included)

### Getting started

1. Clone the repository and open its root directory:

   ```bash
   git clone <repository-url>
   cd documind
   ```

2. Install the locked dependencies:

   ```bash
   uv sync
   ```

3. Create a `.env` file in the repository root and add your API keys:

   ```dotenv
   DEEPSEEK_API_KEY=your_deepseek_api_key
   QWEN_API_KEY=your_dashscope_api_key
   ```

   `DEEPSEEK_API_KEY` is used for query rewriting and answer generation. `QWEN_API_KEY` is used to embed document chunks and queries. Do not commit real credentials to version control.

4. Start the API and web application from the repository root:

   ```bash
   uv run uvicorn app.main:app --reload
   ```

5. Open the web UI at [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Interactive API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), and the health check is [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

The application creates and uses `./chroma_db` relative to the current working directory. Keep the server working directory at the repository root so it uses the expected database and can find the `static` directory.

### Configuration

The current settings are defined in `app/core/config.py`:

| Setting | Default / source | Purpose |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | Read from `.env` / environment | DeepSeek chat API credential |
| LLM base URL | `https://api.deepseek.com/v1` | OpenAI-compatible chat endpoint |
| LLM model | `deepseek-chat` | Query rewriting and answer generation |
| `QWEN_API_KEY` | Read from `.env` / environment | DashScope embedding API credential |
| Embedding base URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` | OpenAI-compatible embeddings endpoint |
| Embedding model | `text-embedding-v2` | Text embedding model |
| Chroma directory | `./chroma_db` | Persistent vector database |
| Reranker model | `BAAI/bge-reranker-base` | Cross-encoder model used for reranking |
| Chunk size / overlap | 500 / 50 characters | PDF text splitting defaults |

The reranker is loaded lazily when the first non-empty candidate set needs reranking. Model download and inference can take additional time and memory, depending on the machine.

### Using the application

1. Start the server and open the browser UI.
2. In **Import local document**, enter a PDF path that is readable by the server process, then select **Import document**.
   - Paths are resolved on the server, not in the browser.
   - The sample path shown by the UI is `./test/刘东旭_前端开发.pdf`; in this repository the included sample is under `tests/`, so enter `./tests/刘东旭_前端开发.pdf` when running from the project root.
3. Wait for the ingestion confirmation, then enter a question and select **Send**.
4. The response is displayed incrementally as the LLM streams tokens.

Document ingestion endpoint example:

```bash
curl -X POST http://127.0.0.1:8000/api/doc/ingest \
  -H "Content-Type: application/json" \
  -d "{\"file_path\":\"./tests/刘东旭_前端开发.pdf\"}"
```

Ask a question endpoint example:

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"请总结这份文档的主要内容\",\"history\":[]}"
```

### API reference

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Serves the browser UI from `static/index.html`. |
| `GET` | `/health` | Returns `{"status":"ok"}` when the app is running. |
| `POST` | `/api/doc/ingest` | Parses a server-local PDF path and stores its chunks in Chroma. |
| `POST` | `/api/chat` | Runs the RAG pipeline and returns an SSE stream. |
| `GET` | `/docs` | FastAPI Swagger UI. |

#### Ingest a PDF

Request body:

```json
{
  "file_path": "./tests/刘东旭_前端开发.pdf"
}
```

Successful response:

```json
{
  "message": "文档成功入库",
  "chunks_count": 12
}
```

The exact chunk count depends on the PDF. A missing path returns HTTP 404; a PDF with no extractable text returns HTTP 400.

#### Ask a question

Request body:

```json
{
  "question": "What skills are listed in the document?",
  "history": []
}
```

The endpoint responds with `Content-Type: text/event-stream`, emitting `data: ...` frames and ending with `data: [DONE]`. Although the request model accepts `history`, the current RAG prompt does not use conversation history.

### Project layout

```text
.
├── app/
│   ├── api/                 # Chat and document endpoints
│   ├── core/                # Settings and shared application configuration
│   ├── models/              # Request and response models
│   ├── services/            # Document, LLM, RAG, and vector services
│   ├── utils/               # Text splitting utilities
│   └── main.py              # FastAPI app, routes, and static UI
├── chroma_db/               # Persistent local Chroma data
├── static/
│   └── index.html           # Browser UI
├── tests/                   # Sample PDF (not an automated test suite)
├── main.py                  # Placeholder script; not the API server entry point
├── pyproject.toml           # Project metadata and dependencies
└── uv.lock                  # Locked dependency versions
```

Run the web server with `uv run uvicorn app.main:app --reload`. The root-level `main.py` is a placeholder and only prints a greeting.

### Current limitations

- Ingestion accepts a local filesystem path in JSON; it does not upload files, and the file must be accessible to the server.
- PDF parsing extracts embedded text only; OCR is not provided.
- TXT parsing exists as a service helper, but there is no API route for TXT ingestion.
- BM25 is held in memory and rebuilt after ingestion or when first needed. Chroma data persists on disk, but no separate BM25 index is persisted.
- The current chat endpoint does not use the supplied `history` field.
- The UI and API have no authentication or authorization. Do not expose this demo to untrusted networks as-is.
- If no relevant documents are retrieved, the LLM prompt instructs the model to say that the information is not mentioned in the documents; answer behavior still depends on the model.

---

## 中文

DocuMind 是一个基于检索增强生成（RAG）的私有知识库问答演示项目。系统结合查询改写、向量检索、BM25 关键词检索、倒数排名融合（RRF）和 BGE Cross-Encoder 重排序，并基于检索到的文档片段生成答案、向浏览器流式返回。

> **项目状态：** 当前仓库属于早期演示版本，尚不具备生产级企业服务能力。目前通过服务器本地 PDF 文件路径导入文档，尚未实现身份认证、权限控制或文件上传界面。

### 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [架构说明](#架构说明)
- [运行要求](#运行要求)
- [快速启动](#快速启动)
- [配置说明](#配置说明)
- [使用方式](#使用方式)
- [API 接口](#api-接口)
- [项目结构](#项目结构)
- [当前限制](#当前限制)

### 功能特性

- 使用 pypdf 按页解析 PDF，并将正文切分为带重叠的文本块。
- 将文档片段及其元数据持久化到本地 Chroma 数据库。
- 将用户问题改写为最多三个更适合检索的查询。
- 同时进行语义向量检索和 BM25 关键词检索，并使用 RRF 融合排序。
- 使用 `BAAI/bge-reranker-base` 对候选结果精排，再将最相关片段传给大语言模型。
- 通过 Server-Sent Events（SSE）将生成结果逐步返回网页。
- 提供简单的浏览器界面以及 FastAPI 交互式 API 文档。

### 技术栈

| 领域 | 技术 |
| --- | --- |
| 语言与运行时 | Python 3.12+ |
| Web 框架与 ASGI 服务 | FastAPI、Uvicorn |
| 大语言模型 | DeepSeek Chat（OpenAI 兼容 API） |
| Embedding | 阿里云 DashScope 兼容 Embedding API，`text-embedding-v2` |
| 向量数据库 | ChromaDB 持久化客户端 |
| 关键词检索与融合 | `rank-bm25`、倒数排名融合（RRF） |
| 重排序 | Sentence Transformers `CrossEncoder`、`BAAI/bge-reranker-base` |
| PDF 解析与文本切分 | pypdf、项目内字符切分工具 |
| 配置管理 | `python-dotenv` |
| 浏览器界面 | 静态 HTML 与 JavaScript |

### 架构说明

```text
                         ┌──────────────────────────────┐
                         │        浏览器 / 用户         │
                         └──────────────┬───────────────┘
                                        │ POST /api/chat
                                        ▼
                         ┌──────────────────────────────┐
                         │ FastAPI 对话接口             │
                         │ app/api/chat.py              │
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ 查询改写                     │
                         │ DeepSeek：生成 1-3 个检索问题│
                         └──────────────┬───────────────┘
                                        ▼
              ┌─────────────────────────┴─────────────────────────┐
              │                                                   │
              ▼                                                   ▼
    ┌─────────────────────┐                           ┌─────────────────────┐
    │ Chroma 向量检索     │                           │ BM25 关键词检索     │
    │ 召回最多 10 个候选  │                           │ 召回最多 10 个候选  │
    └──────────┬──────────┘                           └──────────┬──────────┘
               └─────────────────────────┬───────────────────────┘
                                         ▼
                         ┌──────────────────────────────┐
                         │ RRF 混合排序                 │
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ BGE Cross-Encoder 重排序     │
                         │ 每个改写问题保留最多 2 个    │
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ 去重，最多保留 5 个文本块    │
                         │ 构造上下文                   │
                         └──────────────┬───────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │ DeepSeek Chat                │
                         │ 基于检索上下文生成答案       │
                         └──────────────┬───────────────┘
                                        │ SSE 流式文本片段
                                        ▼
                         ┌──────────────────────────────┐
                         │        浏览器 / 用户         │
                         └──────────────────────────────┘
```

#### 文档入库流程

```text
服务器本地 PDF 路径
        -> pypdf 按页提取文本
        -> 切分为 500 字符文本块（相邻块重叠 50 字符）
        -> DashScope 生成向量
        -> Chroma 持久化文本及来源/页码元数据
        -> 重建内存中的 BM25 索引
```

对每个改写后的查询，系统分别从向量检索和 BM25 检索中最多召回 10 个候选，并使用 RRF 合并排名。重排序阶段每个查询最多保留 2 个候选；相同文本块会去重，最终最多将 5 个文本块放入大模型上下文。

### 运行要求

- Python **3.12 或更高版本**
- 使用 [`uv`](https://docs.astral.sh/uv/) 管理依赖和虚拟环境
- DeepSeek API Key
- 已开通兼容 Embedding API 的 DashScope API Key
- 能访问大模型和 Embedding API 的网络；首次加载 Reranker 时可能还需要下载模型
- 可提取文本的 PDF 文件（扫描版/纯图片 PDF 需要 OCR，本项目未提供 OCR）

### 快速启动

1. 克隆仓库并进入项目根目录：

   ```bash
   git clone <repository-url>
   cd documind
   ```

2. 安装锁定的项目依赖：

   ```bash
   uv sync
   ```

3. 在项目根目录创建 `.env` 文件，配置 API Key：

   ```dotenv
   DEEPSEEK_API_KEY=your_deepseek_api_key
   QWEN_API_KEY=your_dashscope_api_key
   ```

   `DEEPSEEK_API_KEY` 用于查询改写和答案生成，`QWEN_API_KEY` 用于文档片段及查询的向量化。请勿将真实密钥提交到版本控制。

4. 在项目根目录启动 API 和网页服务：

   ```bash
   uv run uvicorn app.main:app --reload
   ```

5. 浏览器访问：
   - 网页：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

应用会将数据保存到当前工作目录下的 `./chroma_db`。请从项目根目录启动服务，确保能够使用预期数据库目录并正确找到 `static` 静态文件目录。

### 配置说明

当前配置定义在 `app/core/config.py`：

| 配置项 | 默认值 / 来源 | 用途 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 从 `.env` / 环境变量读取 | DeepSeek 对话 API 密钥 |
| LLM Base URL | `https://api.deepseek.com/v1` | OpenAI 兼容的对话接口 |
| LLM 模型 | `deepseek-chat` | 查询改写与答案生成 |
| `QWEN_API_KEY` | 从 `.env` / 环境变量读取 | DashScope Embedding API 密钥 |
| Embedding Base URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` | OpenAI 兼容的向量接口 |
| Embedding 模型 | `text-embedding-v2` | 文本向量模型 |
| Chroma 目录 | `./chroma_db` | 持久化向量数据库目录 |
| Reranker 模型 | `BAAI/bge-reranker-base` | Cross-Encoder 重排序模型 |
| 切块长度 / 重叠长度 | 500 / 50 字符 | PDF 文本切分默认值 |

Reranker 会在首次需要对非空候选集重排序时延迟加载。模型下载和推理需要额外时间及内存，具体取决于运行机器。

### 使用方式

1. 启动服务并打开网页。
2. 在 **Import local document**（导入本地文档）中输入服务器进程可读取的 PDF 路径，然后点击 **Import document**（导入文档）。
   - 路径由服务器解析，不是浏览器本地路径。
   - 页面预填路径是 `./test/刘东旭_前端开发.pdf`；仓库里的示例 PDF 实际位于 `tests/` 目录，因此在项目根目录启动时请输入 `./tests/刘东旭_前端开发.pdf`。
3. 等待入库成功提示，然后输入问题并点击 **Send**（发送）。
4. 模型生成的回答会逐步显示在页面中。

文档导入接口示例：

```bash
curl -X POST http://127.0.0.1:8000/api/doc/ingest \
  -H "Content-Type: application/json" \
  -d "{\"file_path\":\"./tests/刘东旭_前端开发.pdf\"}"
```

提问接口示例：

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"请总结这份文档的主要内容\",\"history\":[]}"
```

### API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 返回 `static/index.html` 网页。 |
| `GET` | `/health` | 服务运行时返回 `{"status":"ok"}`。 |
| `POST` | `/api/doc/ingest` | 解析服务器本地 PDF 路径，并将文本块写入 Chroma。 |
| `POST` | `/api/chat` | 执行 RAG 流程并以 SSE 流式返回答案。 |
| `GET` | `/docs` | FastAPI Swagger UI 交互式 API 文档。 |

#### 导入 PDF

请求体：

```json
{
  "file_path": "./tests/刘东旭_前端开发.pdf"
}
```

成功响应：

```json
{
  "message": "文档成功入库",
  "chunks_count": 12
}
```

实际文本块数量取决于 PDF 内容。文件路径不存在时返回 HTTP 404；PDF 未能提取到文本时返回 HTTP 400。

#### 提交问题

请求体：

```json
{
  "question": "文档中列出了哪些技能？",
  "history": []
}
```

接口返回 `Content-Type: text/event-stream`，以 `data: ...` 帧发送内容，并以 `data: [DONE]` 结束。请求模型虽然接受 `history` 字段，但当前 RAG Prompt 尚未使用对话历史。

### 项目结构

```text
.
├── app/
│   ├── api/                 # 对话与文档接口
│   ├── core/                # 配置及应用级公共设置
│   ├── models/              # 请求与响应数据模型
│   ├── services/            # 文档、LLM、RAG、向量检索服务
│   ├── utils/               # 文本切分工具
│   └── main.py              # FastAPI 应用、路由与静态页面
├── chroma_db/               # 本地持久化 Chroma 数据
├── static/
│   └── index.html           # 浏览器界面
├── tests/                   # 示例 PDF（目前并非自动化测试套件）
├── main.py                  # 占位脚本，不是 API 服务入口
├── pyproject.toml           # 项目元数据与依赖
└── uv.lock                  # 锁定后的依赖版本
```

启动 Web 服务请使用 `uv run uvicorn app.main:app --reload`。根目录的 `main.py` 目前只是打印问候语的占位脚本。

### 当前限制

- 文档导入通过 JSON 传入本地文件路径；没有文件上传功能，且文件必须对服务端进程可访问。
- PDF 解析只提取已有文本，不提供 OCR。
- 服务层有 TXT 解析方法，但当前没有对应的 TXT 入库 API。
- BM25 索引保存在内存中，并会在导入文档后或首次检索时重建；Chroma 数据会持久化，但 BM25 索引本身不会单独保存。
- 当前对话接口不会使用请求中的 `history` 字段。
- 网页和 API 均未实现身份认证或授权。请勿在未加防护的情况下将演示服务暴露给不可信网络。
- 无相关检索结果时，Prompt 会要求模型回答“文档中未提及”；最终回答行为仍受模型影响。