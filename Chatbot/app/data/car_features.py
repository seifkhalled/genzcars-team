FEATURE_QUERY_EXPANSIONS = {
    "conditioner": "air conditioning air conditioner AC",
    "ac": "air conditioning air conditioner AC",
    "4x4": "4x4 four wheel drive 4wd",
    "sunroof": "sunroof moonroof",
    "leather": "leather seats leather interior",
    "gps": "GPS navigation nav",
    "navigation": "GPS navigation nav",
    "camera": "backup camera rear camera",
    "bluetooth": "bluetooth handsfree",
    "push start": "push start keyless",
    "cruise": "cruise control",
    "sensor": "sensors parking sensor",
}


def format_expansions_prompt() -> str:
    lines = []
    for term, expansion in FEATURE_QUERY_EXPANSIONS.items():
        lines.append(f'  - "{term}" -> "{expansion}"')
    return "\n".join(lines)
