from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.graph.state import CarsChatState
from app.graph.nodes.preference_extractor import preference_extractor_node
from app.graph.router import router_node
from app.graph.nodes.catalogue_node import catalogue_node
from app.graph.nodes.search_node import search_node
from app.graph.nodes.recommendation_node import recommendation_node
from app.graph.nodes.advisor_node import advisor_node
from app.graph.nodes.seller_node import seller_node
from app.graph.nodes.guide_node import guide_node
from app.graph.nodes.general_node import general_node
from app.graph.nodes.responder_node import responder_node


def route_after_catalogue(state: CarsChatState) -> str:
    return state.get("next_node", "search_node")


def build_graph() -> "CompiledGraph":
    builder = StateGraph(CarsChatState)

    builder.add_node("preference_extractor", preference_extractor_node)
    builder.add_node("router", router_node)
    builder.add_node("catalogue_node", catalogue_node)
    builder.add_node("search_node", search_node)
    builder.add_node("recommendation_node", recommendation_node)
    builder.add_node("advisor_node", advisor_node)
    builder.add_node("seller_node", seller_node)
    builder.add_node("guide_node", guide_node)
    builder.add_node("general_node", general_node)
    builder.add_node("responder_node", responder_node)

    builder.set_entry_point("preference_extractor")
    builder.add_edge("preference_extractor", "router")

    builder.add_conditional_edges(
        "router",
        lambda state: state["next_node"],
        {
            "catalogue_node": "catalogue_node",
            "advisor_node": "advisor_node",
            "seller_node": "seller_node",
            "guide_node": "guide_node",
            "general_node": "general_node",
        }
    )

    builder.add_conditional_edges(
        "catalogue_node",
        route_after_catalogue,
        {
            "search_node": "search_node",
            "recommendation_node": "recommendation_node",
        }
    )

    for node in ["search_node", "recommendation_node", "advisor_node", "seller_node", "guide_node", "general_node"]:
        builder.add_edge(node, "responder_node")

    builder.add_edge("responder_node", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
