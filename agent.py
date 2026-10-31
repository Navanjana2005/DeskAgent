import dotenv

dotenv.load_dotenv()

from langchain.agents import create_agent
import tools as agent_tools  # New modular tools package
from providers import build_chat_model, configured_model_name, select_provider

tool_list = agent_tools.get_tools()

if not tool_list:
    raise RuntimeError(
        "No tools found — check the tools/ package and ensure functions are decorated with @tool"
    )

print(f"✅ Loaded {len(tool_list)} tools.")

SYSTEM_PROMPT = (
    "You are ARIA, DeskAgent's assistant. Use registered tools when relevant; "
    "availability depends on the environment. Never claim an action succeeded "
    "unless its tool result confirms it. Before consequential actions (such as "
    "sending, submitting, deleting, or changing settings), obtain explicit "
    "user confirmation and use any confirmation parameter the tool requires. "
    "Do not infer confirmation from general intent. Protect secrets and "
    "sensitive data. Report limitations and failures honestly. For multi-step "
    "tasks, briefly state the plan, then summarize verified results. Refuse "
    "harmful requests."
)

def chat(provider=None):
    from tui import run_terminal_chat

    selected_provider = provider or select_provider()
    llm = build_chat_model(selected_provider)
    model_name = configured_model_name(selected_provider)
    print(f"✅ {selected_provider.label} LLM configured with model: {model_name}")
    agent = create_agent(
        model=llm,
        tools=tool_list,
        system_prompt=SYSTEM_PROMPT,
    )
    print("✅ Agent created and ready to use!")

    run_terminal_chat(
        agent,
        tool_list,
        agent_tools.get_tool_metadata(),
        model_name,
        selected_provider.label,
    )


if __name__ == "__main__":
    chat()
