WEBSITE_FEATURES = {
    "post_ad": (
        "Top navigation bar -> 'Post Ad' button -> fill car details -> "
        "upload up to 10 photos -> click Publish. Goes live immediately."
    ),
    "filter_search": (
        "Homepage left sidebar has filters (brand, price, city, fuel, "
        "body type, transmission, year range). Search bar accepts natural language."
    ),
    "save_favorites": (
        "Heart icon on any car card or ad page. View at Profile -> Favorites."
    ),
    "compare": (
        "'Add to Compare' on up to 3 ads -> comparison tray at page bottom -> "
        "'Compare Now' -> full AI report with pros/cons and final recommendation."
    ),
    "contact_seller": (
        "Phone number shown on every ad page below car details."
    ),
    "edit_ad": (
        "Profile -> My Ads -> Edit button on the ad."
    ),
    "delete_ad": (
        "Profile -> My Ads -> three-dot menu -> Delete."
    ),
    "account_settings": (
        "Profile -> Settings (name, phone, avatar, password)."
    ),
}


def format_website_guide() -> str:
    lines = []
    for feature, description in [
        ("Post Ad", WEBSITE_FEATURES["post_ad"]),
        ("Filter/Search", WEBSITE_FEATURES["filter_search"]),
        ("Save/Favorites", WEBSITE_FEATURES["save_favorites"]),
        ("Compare", WEBSITE_FEATURES["compare"]),
        ("Contact seller", WEBSITE_FEATURES["contact_seller"]),
        ("Edit ad", WEBSITE_FEATURES["edit_ad"]),
        ("Delete ad", WEBSITE_FEATURES["delete_ad"]),
        ("Account settings", WEBSITE_FEATURES["account_settings"]),
    ]:
        lines.append(f"- {feature}: {description}")
    return "\n".join(lines)
