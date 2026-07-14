from enum import Enum


class NodeName(str, Enum):
    PREFERENCE_EXTRACTOR = "preference_extractor"
    ROUTER = "router"
    CATALOGUE = "catalogue_node"
    SEARCH = "search_node"
    RECOMMENDATION = "recommendation_node"
    ADVISOR = "advisor_node"
    SELLER = "seller_node"
    GUIDE = "guide_node"
    GENERAL = "general_node"
    RESPONDER = "responder_node"


# Single source of truth for the nodes the router may dispatch to. Both the
# conditional-edge map (builder.py) and the router's validation set (router.py)
# are derived from this, so they cannot drift apart when a specialist is added.
ROUTABLE_NODES = frozenset({
    NodeName.CATALOGUE,
    NodeName.ADVISOR,
    NodeName.SELLER,
    NodeName.GUIDE,
    NodeName.GENERAL,
})


class TaskType(str, Enum):
    ROUTER = "router"
    PREFERENCE_EXTRACTOR = "preference_extractor"
    SEARCH = "search"
    CATALOGUE_CHECK = "catalogue_check"
    GUIDE = "guide"
    GUIDE_TOPIC = "guide_topic"
    SEARCH_DECISION = "search_decision"
    ADVISOR = "advisor"
    SELLER = "seller"
    RECOMMENDATION = "recommendation"
    GENERAL = "general"
    COMPARISON = "comparison"
