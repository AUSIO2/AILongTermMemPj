from src import Agent
from src.memory import NoMem

if __name__ == "__main__":
    agent = Agent(mem_module=NoMem())
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        reply = agent.chat(user_input)
        print(f"Agent: {reply}")