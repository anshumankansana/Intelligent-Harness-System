"""LangGraph workflow definition (optional explicit graph)."""

from typing import TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError:
    StateGraph = None


class HarnessState(TypedDict, total=False):
    run_id: str
    user_idea: str
    approval_status: str
    human_edits: str
    human_instructions: str
    stage: str


def build_harness_graph():
    """Minimal LangGraph scaffold mirroring orchestrator stages."""
    if StateGraph is None:
        return None

    graph = StateGraph(HarnessState)

    def plan(state: HarnessState) -> HarnessState:
        return {**state, "stage": "planned"}

    def debate(state: HarnessState) -> HarnessState:
        return {**state, "stage": "debated"}

    def await_approval(state: HarnessState) -> HarnessState:
        return {**state, "stage": "awaiting_approval"}

    def build(state: HarnessState) -> HarnessState:
        return {**state, "stage": "built"}

    def validate(state: HarnessState) -> HarnessState:
        return {**state, "stage": "validated"}

    graph.add_node("plan", plan)
    graph.add_node("debate", debate)
    graph.add_node("approve", await_approval)
    graph.add_node("build", build)
    graph.add_node("validate", validate)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "debate")
    graph.add_edge("debate", "approve")
    graph.add_edge("approve", "build")
    graph.add_edge("build", "validate")
    graph.add_edge("validate", END)

    return graph.compile()
