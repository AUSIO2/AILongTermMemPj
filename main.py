import src.memory as memory
from src.agents import Agent, MessageDTO

import os
import logging
from src.agents.message_enum import Message

logger = logging.getLogger("AILongTermMem")
logger.setLevel(logging.INFO)

def setup_agent_logger(agent_name: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"{agent_name}.log")
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def init() -> list[Agent]:
    agents = []
    for name in memory.__all__:
        if name != "BaseMem":
            mem_class = getattr(memory, name)
            agents.append(Agent(mem_module = mem_class()))
    return agents

def loadtest() -> list[MessageDTO]:
    import json
    from src.agents.message_dto import MessageDTO, Role
    # 获取测试文件的绝对路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 读取标准的 .json 文件
    test_file = os.path.join(base_dir, "test", "conversation_tests.json")
    
    if not os.path.exists(test_file):
        logger.error(f"找不到测试文件: {test_file}")
        return []
        
    with open(test_file, "r", encoding="utf-8") as f:
        # 将整个 JSON 数组反序列化为 Python 列表
        tests = json.load(f)
        
    for data in tests:
        for turn in data["turns"]:
            turn["q_dto"] = MessageDTO(role=Role.USER, content=turn["q"])
                
    logger.info(f"成功加载了 {len(tests)} 组测试数据")
    return tests

def conversation_loop(agent: Agent):
    tests = loadtest()
    if not tests:
        return
    for data in tests:
        logger.info(f"--- 运行测试组: {data['id']} (类型: {data['type']}) ---")
        # 分配一个记忆实例
        agent.mem = agent.mem.__class__()
        
        for turn in data["turns"]:
            q_dto = turn.get("q_dto")
            q_text = q_dto.content if q_dto else turn.get("q", "")
            logger.info("========== [准备发送的新一轮请求] ==========")
            logger.info("[Agent 系统设定] %s", Message.SYSTEM_CONTEXT.value)
            
            mem_dtos = agent.mem.get_mem(q_text)
            for m in mem_dtos:
                if m.role.value == "system" and "长期记忆" in m.content:
                    logger.info("[长期记忆注入] \n%s", m.content)
                elif m.role.value == "system" and "摘要" in m.content:
                    logger.info("[短期记忆摘要] \n%s", m.content)
                else:
                    logger.info("[短期记忆记录] [%s]: %s", m.role.name, m.content)
            
            logger.info("[当前用户输入] [USER]: %s", q_text)
            
            try:
                reply = agent.chat(q_text)
                logger.info("Agent回复: %s\n", reply)
            except Exception as e:
                logger.error("Agent Error: %s\n", e)

def run():
    agents = init()
    for ag in agents:
        agent_name = ag.mem.__class__.__name__
        setup_agent_logger(agent_name)
        logger.info(" 开始评测策略: %s", agent_name)
        conversation_loop(ag)

if __name__ == '__main__':
    run()
