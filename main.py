import json
import os
import shutil
import sys
import logging
from typing import Any

import src.memory as memory
from src.agents import Agent, MessageDTO
from src.agents.message_dto import Role
from src.agents.message_enum import Message
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger("AILongTermMem")
logger.setLevel(logging.INFO)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on", "y"}


def _resolve_mode(argv: list[str]) -> str:
    mode = os.getenv("RUN_MODE", "test").strip().lower()
    for i, arg in enumerate(argv):
        if arg == "--mode" and i + 1 < len(argv):
            mode = argv[i + 1].strip().lower()
        elif arg.startswith("--mode="):
            mode = arg.split("=", 1)[1].strip().lower()
    if mode not in {"test", "chat"}:
        logger.warning("未知模式 '%s'，将回退到 test", mode)
        return "test"
    return mode


def _resolve_test_dataset(argv: list[str]) -> str:
    dataset = "conversation_tests.json"
    for i, arg in enumerate(argv):
        if arg == "--test-file" and i + 1 < len(argv):
            dataset = argv[i + 1].strip()
        elif arg.startswith("--test-file="):
            dataset = arg.split("=", 1)[1].strip()
    return dataset or "conversation_tests.json"


def setup_agent_logger(agent_name: str) -> None:
    log_dir = os.path.join(_BASE_DIR, "log")
    os.makedirs(log_dir, exist_ok=True)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(
        os.path.join(log_dir, f"{agent_name}.log"), mode="w", encoding="utf-8"
    )
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
        if name == "BaseMem":
            continue
        if selected_strategies and name not in selected_strategies:
            continue
        mem_class = getattr(memory, name)
        agents.append(Agent(mem_module=mem_class()))

    if selected_strategies and not agents:
        logger.warning("MEMORY_STRATEGIES 未匹配到任何策略: %s", ",".join(sorted(selected_strategies)))
    return agents


def _read_test_file(file_path: str) -> list:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    if not raw_text.strip():
        raise ValueError(f"测试文件为空: {file_path}")
    return json.loads(raw_text)


def loadtest(test_dataset: str = "conversation_tests.json") -> list:
    test_file = test_dataset
    if not os.path.isabs(test_dataset):
        test_file = os.path.join(_BASE_DIR, "test", test_dataset)

    if not os.path.exists(test_file):
        logger.error("找不到测试文件: %s", test_file)
        return []

    try:
        tests: list = _read_test_file(test_file)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("测试文件格式异常: %s | %s", test_file, e)
        return []

    for data in tests:
        for turn in data["turns"]:
            turn["q_dto"] = MessageDTO(role=Role.USER, content=turn["q"])

    logger.info("成功加载了 %d 组测试数据 | 文件: %s", len(tests), test_file)
    return tests


def conversation_loop(agent: Agent, test_dataset: str = "conversation_tests.json") -> None:
    show_short_mem_logs = _env_bool("LOG_SHORT_MEM_RECORDS", default=True)
    current_strategy = agent.mem.__class__.__name__
    tests = loadtest(test_dataset)
    if not tests:
        return

    for data in tests:
        logger.info("--- 运行测试组: %s (类型: %s) ---", data["id"], data["type"])
        agent.mem = agent.mem.__class__()

        for turn in data["turns"]:
            q_dto = turn.get("q_dto")
            q_text = q_dto.content if q_dto else turn.get("q", "")
            logger.info("========== [准备发送的新一轮请求] ==========")
            logger.info("[Agent 系统设定] %s", Message.SYSTEM_CONTEXT.value)

            for m in agent.mem.get_mem(q_text):
                if m.role.value == "system" and "长期记忆" in m.content:
                    logger.info("[长期记忆注入] \n%s", m.content)
                elif m.role.value == "system" and "摘要" in m.content:
                    logger.info("[短期记忆摘要] \n%s", m.content)
                elif current_strategy == "LongMem":
                    logger.info("[长期记忆检索] [%s]: %s", m.role.name, m.content)
                elif show_short_mem_logs:
                    logger.info("[短期记忆记录] [%s]: %s", m.role.name, m.content)

            logger.info("[当前用户输入] [USER]: %s", q_text)
            try:
                reply = agent.chat(q_text)
                logger.info("Agent回复: %s\n", reply)
            except Exception as e:
                logger.error("Agent Error: %s\n", e)


def chat_loop(agent: Agent) -> None:
    print("进入对话模式，输入 exit / quit / q 退出。")
    while True:
        try:
            q_text = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出对话模式。")
            break
        if not q_text:
            continue
        if q_text.lower() in {"exit", "quit", "q"}:
            print("已退出对话模式。")
            break
        try:
            reply = agent.chat(q_text)
            print(f"Agent: {reply}\n")
        except Exception as e:
            logger.error("Agent Error: %s", e)
            print("Agent: 抱歉，当前请求失败，请查看日志。")


def run_test_mode(test_dataset: str = "conversation_tests.json") -> None:
    store_path = os.path.join(_BASE_DIR, "memorystore")
    if os.path.exists(store_path):
        shutil.rmtree(store_path, ignore_errors=True)

    for ag in init():
        agent_name = ag.mem.__class__.__name__
        setup_agent_logger(agent_name)
        logger.info(" 开始评测策略: %s", agent_name)
        conversation_loop(ag, test_dataset)


def run_chat_mode() -> None:
    agents = init()
    if not agents:
        logger.error("没有可用的记忆策略，请检查 MEMORY_STRATEGIES 配置")
        return
    if len(agents) > 1:
        logger.warning("chat 模式只使用第一个策略: %s", agents[0].mem.__class__.__name__)
    ag = agents[0]
    setup_agent_logger(ag.mem.__class__.__name__)
    logger.info(" 开始对话模式: %s", ag.mem.__class__.__name__)
    chat_loop(ag)

def evaluation_IO(question: str, answer: str, expected: str) -> int:
    """
    return:
        1 = correct
        0 = incorrect
    """

    prompt = f"""
You are a strict evaluator.

Task:
Determine whether the model's answer matches the expected meaning.

Rules:
- Ignore wording differences
- Focus on semantic equivalence
- If same meaning → 1
- Otherwise → 0

Question:
{question}

Expected answer:
{expected}

Model answer:
{answer}

Return ONLY 1 or 0.
"""
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
    )

    result = response.choices[0].message.content.strip()

    return 1 if "1" in result else 0

def evaluation_forgetting(question: str, answer: str, expectation: str) -> float:
    """
    expectation: 多个 memory points（可以是 list 或 string）
    """

    prompt = f"""
You are an evaluator for memory recall.

Task:
Check how many memory points in EXPECTATION are correctly reflected in the ANSWER.

Rules:
- Each memory point is counted separately
- A point is correct if meaning is preserved in answer
- Return format MUST be:
  correct_count / total_count

Question:
{question}

Expected memory points:
{expectation}

Model answer:
{answer}

Return ONLY the fraction (e.g. 2/3).
"""

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


def load_data_new(path: str) -> list[dict[str, Any]]:
    """
    读取新的 JSON 数据格式（list 或单个 dict 都兼容）
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return [data]
    return data

def answer_evaluation(conv_type: str, evaluations: list[dict], answers: dict) -> float:
    """
    evaluations: 所有 role == evaluation 的节点
    answers: {question: answer}
    """

    if conv_type == "consistency":
        scores = []
        for ev in evaluations:
            q = ev["q"]
            expected = ev["expected"]
            ans = answers.get(q, "")
            scores.append(evaluation_IO(q, ans, expected))

        return sum(scores) / len(scores) if scores else 0.0

    elif conv_type == "forgetting":
        # 只取最后一个 evaluation
        ev = evaluations[-1]
        q = ev["q"]
        expected = ev["expected"]
        ans = answers.get(q, "")
        return evaluation_forgetting(ans, expected)

    else:
        raise ValueError(f"Unknown type: {conv_type}")

def conversation_loop(agent, test_dataset: str = "conversation_tests.json") -> None:
    tests = load_data_new(test_dataset)
    if not tests:
        return

    for data in tests:
        conv_id = data.get("id")
        conv_type = data.get("type")

        logger.info("--- 运行测试组: %s (类型: %s) ---", conv_id, conv_type)

        # 每组对话重置 memory
        agent.mem = agent.mem.__class__()

        turns = data.get("turns", [])

        answers: dict[str, str] = {}
        evaluation_nodes: list[dict] = []

        # =========================
        # 1. 逐轮对话执行
        # =========================
        for turn in turns:
            role = turn.get("role")
            q_text = turn.get("q", "")

            # evaluation 不进入对话，只记录
            if role == "evaluation":
                evaluation_nodes.append(turn)
                continue

            logger.info("========== [准备发送的新一轮请求] ==========")
            logger.info("[Agent 系统设定] %s", Message.SYSTEM_CONTEXT.value)

            # memory log（沿用你的风格）
            for m in agent.mem.get_mem(q_text):
                if m.role.value == "system" and "长期记忆" in m.content:
                    logger.info("[长期记忆注入] \n%s", m.content)

                elif m.role.value == "system" and "摘要" in m.content:
                    logger.info("[短期记忆摘要] \n%s", m.content)

                elif "LongMem" in agent.mem.__class__.__name__:
                    logger.info("[长期记忆检索] [%s]: %s", m.role.name, m.content)

                else:
                    logger.info("[短期记忆记录] [%s]: %s", m.role.name, m.content)

            logger.info("[当前用户输入] [USER]: %s", q_text)

            try:
                reply = agent.chat(q_text)
                answers[q_text] = reply
                logger.info("Agent回复: %s\n", reply)

            except Exception as e:
                logger.error("Agent Error: %s\n", e)

        # =========================
        # 2. evaluation 阶段
        # =========================
        logger.info("========== [开始评测阶段] ==========")

        score = None

        if conv_type == "consistency":
            scores = []

            for ev in evaluation_nodes:
                q = ev["q"]
                expected = ev["expected"]

                ans = answers.get(q, "")
                s = evaluation_IO(q, ans, expected)

                scores.append(s)

                logger.info(
                    "[CONSISTENCY评测] Q: %s | expected: %s | score: %s",
                    q, expected, s
                )

            score = sum(scores) / len(scores) if scores else 0.0

        elif conv_type == "forgetting":
            if not evaluation_nodes:
                score = 0.0
            else:
                ev = evaluation_nodes[-1]
                q = ev["q"]
                expected = ev["expected"]

                ans = answers.get(q, "")
                score = evaluation_forgetting(ans, expected)

                logger.info(
                    "[FORGETTING评测] Q: %s | expected: %s | score: %s",
                    q, expected, score
                )

        else:
            logger.warning("未知类型: %s", conv_type)
            score = 0.0

        # =========================
        # 3. 最终结果输出
        # =========================
        logger.info(
            "========== [测试组结束] id=%s | type=%s | score=%.4f ==========\n",
            conv_id, conv_type, score
        )

def run() -> None:
    argv = sys.argv[1:]
    mode = _resolve_mode(argv)
    if mode == "chat":
        run_chat_mode()
    else:
        run_test_mode(_resolve_test_dataset(argv))


if __name__ == "__main__":
    run()
