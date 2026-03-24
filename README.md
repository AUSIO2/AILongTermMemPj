# AI Long-Term Memory Project

一个基于策略模式的 AI Agent，支持可插拔的长期/短期记忆模块。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入真实的 API Key

# 3. 运行
python main.py
```

## 项目结构

```
src/
├── agents/
│   ├── agent.py          # Agent 主类
│   ├── message_dto.py    # MessageDTO / Role 数据模型
│   └── message_enum.py   # 系统 Prompt 枚举
└── memory/
    ├── base_mem.py       # 抽象记忆基类
    ├── no_mem.py         # 无记忆策略
    ├── short_mem.py      # 短期记忆策略（待实现）
    └── long_mem.py       # 长期记忆策略（待实现）
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | API Key（必填） | — |
| `OPENAI_BASE_URL` | 接口地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o-mini` |
