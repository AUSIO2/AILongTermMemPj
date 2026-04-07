import src.memory as memory
from src.agents import Agent, MessageDTO

import os
import logging
from src.agents.message_enum import Message

logger = logging.getLogger("AILongTermMem")
logger.setLevel(logging.INFO)


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on", "y"}

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
    selected_strategies = {
        name.strip()
        for name in os.getenv("MEMORY_STRATEGIES", "").split(",")
        if name.strip()
    }

    agents = []
    for name in memory.__all__:
        if name != "BaseMem":
            if selected_strategies and name not in selected_strategies:
                continue
            mem_class = getattr(memory, name)
            agents.append(Agent(mem_module = mem_class()))
    if selected_strategies and not agents:
        logger.warning("MEMORY_STRATEGIES 未匹配到任何策略: %s", ",".join(sorted(selected_strategies)))
    return agents

def loadtest() -> list[MessageDTO]:
    import json
    from src.agents.message_dto import MessageDTO, Role
    # 获取测试文件的绝对路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(base_dir, "test", "conversation_tests.json")
    fallback_files = [
        os.path.join(base_dir, "test", "conversation_tests.json.example2"),
        os.path.join(base_dir, "test", "conversation_tests.json.example"),
    ]

    def _read_test_file(file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        # 允许测试文件为空白字符，并给出更清晰的日志
        if not raw_text.strip():
            raise ValueError(f"测试文件为空: {file_path}")
        return json.loads(raw_text)

    tests = []
    if os.path.exists(test_file):
        try:
            tests = _read_test_file(test_file)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("测试文件格式异常，将尝试回退到示例文件: %s", e)
    else:
        logger.warning("找不到测试文件，将尝试示例文件: %s", test_file)

    if not tests:
        for fallback_file in fallback_files:
            if not os.path.exists(fallback_file):
                continue
            try:
                tests = _read_test_file(fallback_file)
                logger.info("已回退使用示例测试文件: %s", fallback_file)
                break
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("示例测试文件不可用: %s | %s", fallback_file, e)
        if not tests:
            logger.error("无法加载任何可用的测试文件")
            return []
        
    for data in tests:
        for turn in data["turns"]:
            turn["q_dto"] = MessageDTO(role=Role.USER, content=turn["q"])
                
    logger.info(f"成功加载了 {len(tests)} 组测试数据")
    return tests

def conversation_loop(agent: Agent):
    show_short_mem_logs = _env_bool("LOG_SHORT_MEM_RECORDS", default=True)
    current_strategy = agent.mem.__class__.__name__
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
                    # 仅长期记忆策略下，非 system 记忆来自向量检索，不应标记为短期记忆
                    if current_strategy == "LongMem":
                        logger.info("[长期记忆检索] [%s]: %s", m.role.name, m.content)
                    elif show_short_mem_logs:
                        logger.info("[短期记忆记录] [%s]: %s", m.role.name, m.content)
            
            logger.info("[当前用户输入] [USER]: %s", q_text)
            
            try:
                reply = agent.chat(q_text)
                logger.info("Agent回复: %s\n", reply)
            except Exception as e:
                logger.error("Agent Error: %s\n", e)

def run():
    #删库
    import shutil
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    store_path = os.path.join(base_dir, "memorystore")
    if os.path.exists(store_path):
        shutil.rmtree(store_path, ignore_errors=True)

    agents = init()
    for ag in agents:
        agent_name = ag.mem.__class__.__name__
        setup_agent_logger(agent_name)
        logger.info(" 开始评测策略: %s", agent_name)
        conversation_loop(ag)

if __name__ == '__main__':
    run()
