READ_TOOLS = {"classify_intent", "memory_search", "search_products", "list_shops", "get_plan_status", "list_checkpoints", "get_memory_graph"}
WRITE_LOW_TOOLS = {"write_memory", "publish_dry_run", "request_publish_approval"}
WRITE_HIGH_TOOLS = {"publish_real"}


def classify_tool_risk(tool: str) -> str:
    if tool in READ_TOOLS:
        return "read"
    if tool in WRITE_LOW_TOOLS:
        return "write_low"
    if tool in WRITE_HIGH_TOOLS:
        return "write_high"
    return "unknown"
