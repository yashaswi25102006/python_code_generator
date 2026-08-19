"""
Agentic Dev/Test Crew — Streamlit web app.

A LangGraph-powered mini "crew" of two agents:
  1. Developer  -> writes Python code for a task you describe
  2. Tester     -> generates test scenarios AND actually executes the code

This is a Streamlit adaptation of an interactive notebook script — the
input()-based CLI loop has been replaced with a chat-style web UI, and each
completed task is kept in a session history you can review or clear.
"""

import io
import os
import sys
import traceback
from typing import List, Optional, TypedDict

import streamlit as st
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Agentic Dev/Test Crew", page_icon="🤖", layout="wide")


# ==========================================
# 1. LLM INITIALIZATION
# ==========================================
def get_api_key() -> Optional[str]:
    """Check, in order: Streamlit secrets (Streamlit Cloud), environment
    variable (Render/Railway/Heroku-style deploys), then the sidebar input."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # no secrets.toml present — that's fine on Render
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    return st.session_state.get("api_key_input")


def get_llm(api_key: str, model_name: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)


# ==========================================
# 2. STATE DEFINITION
# ==========================================
class CrewState(TypedDict):
    messages: List[BaseMessage]
    code: Optional[str]
    report: Optional[str]


# ==========================================
# 3. TOOLS
# ==========================================
@tool
def run_python_code(code: str) -> str:
    """Execute python code and return the standard output or error trace."""
    if not isinstance(code, str):
        code = str(code)
    clean_code = code.replace("```python", "").replace("```", "").strip()

    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    try:
        local_scope = {}
        exec(clean_code, {}, local_scope)
        result = new_stdout.getvalue()
    except Exception:
        result = f"Execution Error:\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout

    return result.strip() if result.strip() else "Success (no terminal output)"


def make_generate_test_cases_tool(llm):
    @tool
    def generate_test_cases(task_description: str) -> str:
        """Generate specific test scenarios for a given coding task."""
        prompt = (
            "You are a Senior QA Engineer. Generate 3 to 5 highly specific test "
            f"scenarios for the following coding task: '{task_description}'.\n"
            "Include standard cases and edge cases. Return them as a numbered list."
        )
        response = llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)

    return generate_test_cases


def _extract_text(content) -> str:
    """Normalize Gemini's response content (str or list-of-dict) into plain text."""
    if isinstance(content, list):
        first = content[0]
        return first.get("text", "") if isinstance(first, dict) else str(first)
    return str(content)


# ==========================================
# 4. GRAPH NODES
# ==========================================
def build_graph(llm):
    generate_test_cases = make_generate_test_cases_tool(llm)

    def developer_node(state: CrewState):
        task = state["messages"][-1].content
        dev_prompt = (
            f"Write a clean Python script to solve this: {task}. "
            "Only return the code, no explanation or markdown formatting."
        )
        response = llm.invoke(dev_prompt)
        code_str = _extract_text(response.content)
        return {"code": code_str}

    def tester_node(state: CrewState):
        task = state["messages"][-1].content

        test_cases = generate_test_cases.invoke(task)
        cases_str = _extract_text(test_cases)

        execution_result = run_python_code.invoke({"code": state["code"]})

        report = (
            f"### EXECUTION OUTPUT:\n{execution_result}\n\n"
            f"### TEST SCENARIOS EVALUATED:\n{cases_str}"
        )
        return {"report": report}

    workflow = StateGraph(CrewState)
    workflow.add_node("developer", developer_node)
    workflow.add_node("tester", tester_node)
    workflow.add_edge(START, "developer")
    workflow.add_edge("developer", "tester")
    workflow.add_edge("tester", END)

    return workflow.compile()


# ==========================================
# 5. STREAMLIT UI
# ==========================================
def init_session_state():
    if "history" not in st.session_state:
        st.session_state.history = []  # list of {"task": str, "code": str, "report": str}
    if "api_key_input" not in st.session_state:
        st.session_state.api_key_input = ""


def sidebar():
    st.sidebar.title("⚙️ Settings")

    if get_api_key():
        st.sidebar.success("API key loaded ✅")
    else:
        st.sidebar.text_input(
            "Gemini API Key",
            type="password",
            key="api_key_input",
            help="Set this once, or configure GEMINI_API_KEY as an environment "
            "variable / Streamlit secret for deployment.",
        )

    model_name = st.sidebar.selectbox(
        "Model",
        ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
        index=0,
        help="Pick a currently-available Gemini model for your API key.",
    )

    st.sidebar.divider()
    if st.sidebar.button("🗑️ Clear history"):
        st.session_state.history = []
        st.rerun()

    return model_name


def main():
    init_session_state()
    st.title("🤖 Agentic Dev/Test Crew")
    st.caption("Describe a coding task. A Developer agent writes it, a Tester agent generates test cases and runs the code.")

    model_name = sidebar()
    api_key = get_api_key()

    # --- Task input ---
    with st.form("task_form", clear_on_submit=True):
        task = st.text_area("Describe the coding task", placeholder="e.g. Write a function that checks if a string is a palindrome")
        submitted = st.form_submit_button("Run task ▶️")

    if submitted:
        if not task.strip():
            st.warning("Please enter a task description.")
        elif not api_key:
            st.error("Please provide your Gemini API key in the sidebar first.")
        else:
            with st.spinner("Developer is writing code and Tester is evaluating it..."):
                try:
                    llm = get_llm(api_key, model_name)
                    app = build_graph(llm)
                    result = app.invoke({"messages": [HumanMessage(content=task)]})
                    st.session_state.history.append(
                        {
                            "task": task,
                            "code": result.get("code", ""),
                            "report": result.get("report", ""),
                        }
                    )
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

    # --- History / results (most recent first) ---
    if st.session_state.history:
        st.divider()
        st.subheader("📋 Task Results")
        for i, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"Task {len(st.session_state.history) - i}: {item['task'][:80]}", expanded=(i == 0)):
                st.markdown("**Generated code:**")
                st.code(item["code"], language="python")
                st.markdown("**Report:**")
                st.markdown(item["report"])
    else:
        st.info("No tasks run yet. Enter a task above to get started.")


if __name__ == "__main__":
    main()
