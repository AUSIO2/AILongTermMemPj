from enum import Enum


class Message(Enum):
    SYSTEM_CONTEXT = "你是一个有记忆的AI助手，给出简短回答："
    MEMORY_EXTRACT_CONTEXT = "请将以下对话内容提炼为简洁的摘要，保留关键信息和结论："
    RESULT_CONTEXT = "[以下是之前对话的摘要]"
    LONG_MEM_CONTEXT = "[以下是长期记忆回顾]"
