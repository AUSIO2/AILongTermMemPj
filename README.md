# AI Long-Term Memory Agent Evaluation Framework (PJ-AG2)

这是一个轻量级但功能完备的对话型 LLM Agent 记忆管理评估框架。该项目旨在通过自动化的测试手段，研究、实现并对比大语言模型对多轮复杂对话信息的存储模式（包括固定窗口遗忘、动态摘要压缩以及向量数据库持久化）的优劣差异。

## 🌟 核心理念及记忆策略功能
框架完全解耦了底层的记忆管理（Strategy Pattern）和 LLM 请求层（Agent）。我们内置了以下几种记忆模块供横向评测比对：

- `NoMem`: 完全无记忆，每次交互仅包含当前 query。
- `ShortMem`: 给定 Token 水位保护线的经典滑动窗口模型，超水位时自动丢弃最旧的历史对话。
- `ShortMemExtracted`: 基于 LLM 归纳的高级短期记忆。超水位时会将早期的对话重写凝炼为高度概括的 [短期记忆摘要] 注入给系统层。
- `LongMem`: 基于 ChromaDB 向量数据库。把每条单句嵌入（Embeddings）成向量，在回答前先执行 Top-K 语义检索，跨越时间和轮次的障碍拉取关联历史。
- `CombinedMem / CombinedMemExtracted`: 将长短记忆优势融为一体。长记忆作为背景知识注入 SYSTEM 设定；短记忆作为直接的对话上下文承接。

## 🚀 快速启动

### 1. 环境准备
项目基于 Python 构建（推荐 >=3.11），在根目录运行命令极速安装：

```bash
# （推荐）用可编辑模式安装本包，这会自动把核心命令注册到全局 
pip install -e .
```

当然你也可以完全通过常规 `pip install -r requirements.txt` 或 `pip install openai chromadb pydantic python-dotenv tiktoken` 搞定。

### 2. 配置环境变量
在项目根目录创建 `.env` 文件，填入你的大模型 API 信息（默认使用的是 `gpt-4o-mini`）：
```env
OPENAI_API_KEY=sk-xxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 3. 一键运行自动化评测！
在任何地方，直接触发以下命令：
```bash
run-agent-tests
```
*(或者执行传统入口 `python main.py`)*

随着程序的推进，它会全自动读取测试用例，重置虚拟大脑环境，并按顺序循环测试每一种策略，最后在终端输出排版精良的高级对比日志（包括长短记忆被调用分类等），并将原日志归档记录落盘在 `log/` 目录下！

## 🧪 评测脚本编写指南
你可以在 `test/conversation_tests.json` 内按照需求自由设计 JSON 测试用例，框架目前默认定义了三类典型考验：

- **Consistency (一致性测试)**：测试是否能记住几十轮前告诉它的人设/爱好。
- **Forgetting (遗忘率测试)**：通过故意穿插无关垃圾话，观察信息是否因为上下文窗口截断而丢失。
- **Pollution (错误记忆污染测试)**：通过架空世界设定或者错误逻辑，考验模型是否在长记忆中无法自拔、失去基础判断力。

**测试体格式示例：**
```json
[
  {
    "id": "forgetting_example",
    "type": "forgetting",
    "turns": [
      { "q": "暗号是芝麻开门" },
      { "q": "今天天气真好" },
      { "q": "对了，刚才那个暗号是什么？" }
    ]
  }
]
```

## 🌐 Web 可视化聊天界面

除自动化评测模式外，项目还提供了一套完整的 Web 聊天界面，可在浏览器中与不同记忆策略的 Agent 实时对话。

### 前置依赖

- Python 环境已安装所有依赖（见上方快速启动）
- [Node.js](https://nodejs.org)（用于运行前端开发服务器）
- Node 安装后需将其目录（如 `F:\nodejs`）添加到系统 **用户 Path** 环境变量，并重启终端/IDE 生效

### 启动步骤

需要开启**两个终端**分别运行后端和前端。

**终端 1 — 后端 API 服务**（在项目根目录，激活你的 Python 环境后运行）：

```bash
uvicorn api.app:app --reload --port 8000
```

启动成功标志：
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     AI Long-Term Memory API 启动
```

**终端 2 — 前端开发服务器**（在 `frontend/` 目录）：

```bash
# 首次运行需先安装依赖
npm install

# 启动前端
npm run dev
```

启动成功标志：
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

打开浏览器访问 **http://localhost:5173** 即可看到聊天界面。

### 安全退出

| 进程 | 退出方式 |
|------|---------|
| 后端 uvicorn | 在对应终端按 `Ctrl + C` |
| 前端 Vite | 在对应终端按 `Ctrl + C` |

> 两个服务相互独立，按任意顺序退出均可，不会影响已存储的数据。

### 界面功能说明

- **左侧栏**：选择记忆策略（`ShortMemExtracted` / `LongMem` / `CombinedMem` 等）→ 点击「新建对话」
- **右侧区**：消息气泡展示，用户消息蓝色右对齐，AI 回复灰色左对齐
- **多会话**：可同时建立多个对话，每个会话独立持有自己的记忆实例
- **输入框**：`Enter` 发送，`Shift + Enter` 换行

### 长期记忆的删除

```bash
# 删除所有记录 
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/memory/long/clear" -Method POST
# 获取记忆目录 
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sessions/<your session_id>/memory/long" -Method Get
# 删除单条记录
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/sessions/<你的session_id>/memory/long/<item_id>" -Method Delete
```
---

## 📁 目录结构
```text
AILongTermMemPj/
│
├── api/
│   ├── app.py             # FastAPI 后端，提供 REST 接口
│   └── session_manager.py # 会话状态管理（Agent 实例隔离）
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # 主聊天界面组件
│   │   ├── api.js         # 封装后端接口调用
│   │   └── App.css        # 深色主题样式
│   ├── package.json
│   └── vite.config.js     # 代理配置（/api → :8000）
│
├── src/
│   ├── agents/            # OpenAI 请求通信层、实体(MessageDTO)以及预设 Prompt 定义
│   ├── memory/            # 核心：所有记忆策略的具象类（ShortMem, LongMem...）都存放于此
│
├── test/
│   └── conversation_tests.json  # 你的评测剧本
│
├── log/                   # （自动生成）每一次跑测时产生的独立策略日志报告
├── memorystore/           # （自动生成/删除）ChromaDB 持久化向量集合目录
│
├── main.py                # 脚本执行主循环（评测模式 & 命令行对话模式）
├── pyproject.toml         # 包/环境配置
└── .env                   # API KEY 密钥
```

***

*Enjoy building intelligent companions with eternal memories!*
