import json
import re

BRAND_ORIGINS = {
    "german": ["BMW", "Mercedes", "Audi", "Volkswagen", "Porsche", "Opel"],
    "germany": ["BMW", "Mercedes", "Audi", "Volkswagen", "Porsche", "Opel"],
    "japanese": ["Toyota", "Honda", "Nissan", "Mazda", "Suzuki", "Mitsubishi", "Subaru"],
    "japan": ["Toyota", "Honda", "Nissan", "Mazda", "Suzuki", "Mitsubishi", "Subaru"],
    "american": ["Ford", "Chevrolet", "Dodge", "Jeep", "GMC", "Cadillac", "Lincoln", "Tesla"],
    "usa": ["Ford", "Chevrolet", "Dodge", "Jeep", "GMC", "Cadillac", "Lincoln", "Tesla"],
    "america": ["Ford", "Chevrolet", "Dodge", "Jeep", "GMC", "Cadillac", "Lincoln", "Tesla"],
    "korean": ["Hyundai", "Kia", "Genesis", "SsangYong"],
    "south korea": ["Hyundai", "Kia", "Genesis", "SsangYong"],
    "european": ["BMW", "Mercedes", "Audi", "Volkswagen", "Peugeot", "Renault", "Fiat", "Volvo"],
    "europe": ["BMW", "Mercedes", "Audi", "Volkswagen", "Peugeot", "Renault", "Fiat", "Volvo"],
    "italian": ["Fiat", "Alfa Romeo", "Lamborghini", "Ferrari", "Maserati"],
    "italy": ["Fiat", "Alfa Romeo", "Lamborghini", "Ferrari", "Maserati"],
    "british": ["Land Rover", "Jaguar", "MINI", "Bentley", "Rolls-Royce"],
    "uk": ["Land Rover", "Jaguar", "MINI", "Bentley", "Rolls-Royce"],
    "england": ["Land Rover", "Jaguar", "MINI", "Bentley", "Rolls-Royce"],
}


def get_brands_for_origin(origin: str) -> list[str]:
    key = origin.strip().lower()
    return BRAND_ORIGINS.get(key, [])


def format_brand_origins_prompt() -> str:
    lines = []
    for origin, brands in {
        "German/Germany": ["BMW", "Mercedes", "Audi", "Volkswagen", "Porsche", "Opel"],
        "Japanese/Japan": ["Toyota", "Honda", "Nissan", "Mazda", "Suzuki", "Mitsubishi", "Subaru"],
        "American/USA": ["Ford", "Chevrolet", "Dodge", "Jeep", "GMC", "Cadillac", "Lincoln", "Tesla"],
        "Korean/South Korea": ["Hyundai", "Kia", "Genesis", "SsangYong"],
        "European/Europe": ["BMW", "Mercedes", "Audi", "Volkswagen", "Peugeot", "Renault", "Fiat", "Volvo"],
        "Italian/Italy": ["Fiat", "Alfa Romeo", "Lamborghini", "Ferrari", "Maserati"],
        "British/UK/England": ["Land Rover", "Jaguar", "MINI", "Bentley", "Rolls-Royce"],
    }.items():
        lines.append(f'- "{origin}" -> {json.dumps(brands)}')
    return "\n".join(lines)


def detect_origin_brands(message: str) -> list[str]:
    """Detect origin/country keywords in the message and return expanded brand names.

    Uses word-boundary matching so 'american' matches but 'americana' doesn't.
    Returns a deduplicated list preserving BRAND_ORIGINS insertion order.
    """
    text = message.lower()
    seen: set[str] = set()
    result: list[str] = []
    for origin in BRAND_ORIGINS:
        pattern = r'\b' + re.escape(origin) + r'\b'
        if re.search(pattern, text):
            for brand in BRAND_ORIGINS[origin]:
                if brand not in seen:
                    result.append(brand)
                    seen.add(brand)
    return result


def detect_origin_label(message: str) -> str | None:
    """Return the human-readable origin label detected in the message, or None."""
    text = message.lower()
    labels = {
        "american": "American", "usa": "American", "america": "American",
        "german": "German", "germany": "German",
        "japanese": "Japanese", "japan": "Japanese",
        "korean": "Korean", "south korea": "Korean",
        "european": "European", "europe": "European",
        "italian": "Italian", "italy": "Italian",
        "british": "British", "uk": "British", "england": "British",
    }
    for keyword, label in labels.items():
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text):
            return label
    return None
