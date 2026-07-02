import json

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
