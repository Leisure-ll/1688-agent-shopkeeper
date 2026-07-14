STATE_TOOL_WHITELIST = {
    "intent": {"memory_search"},
    "init": {"memory_search", "search_products", "list_shops"},
    "confirmed": {"memory_search", "search_products", "list_shops", "publish_dry_run"},
    "doing": {"memory_search", "search_products", "list_shops", "publish_dry_run", "write_memory", "request_publish_approval"},
    "updating": {"memory_search", "search_products", "list_shops"},
    "done": {"write_memory"},
}

WORKER_TOOL_WHITELIST = {
    "selector": {"search_products", "memory_search"},
    "shop": {"list_shops"},
    "publisher": {"publish_dry_run", "request_publish_approval"},
    "advisor": {"write_memory"},
}


def allowed_for_worker(role: str):
    return WORKER_TOOL_WHITELIST[role]
