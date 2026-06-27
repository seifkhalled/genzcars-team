import json
from typing import AsyncGenerator
from app.core.llm import GeminiClient

WEBSITE_GUIDE = {
    "post_ad": "To post an ad: click 'Post Ad' in the top nav, fill in your car details, upload up to 10 photos, then click Publish. Your ad will be live within seconds.",
    "filter_search": "Use the filters on the left side of the homepage to narrow by brand, price range, city, fuel type, and more. You can also type naturally in the search bar.",
    "save_car": "Click the heart icon on any car card or ad page to save it. Find all saved cars under your profile → Favorites.",
    "compare": "Click 'Add to Compare' on up to 3 ads. A tray appears at the bottom of the screen. Click 'Compare Now' to get the AI report.",
    "contact_seller": "On any ad page, the seller's phone number is shown below the car details.",
    "delete_ad": "Go to Profile → My Ads → three dots → Delete.",
    "edit_ad": "Go to Profile → My Ads → click Edit on the ad you want to update.",
}

KEYWORDS = {
    "post": "post_ad", "publish": "post_ad", "create ad": "post_ad", "list": "post_ad",
    "filter": "filter_search", "search": "filter_search", "browse": "filter_search",
    "save": "save_car", "favorite": "save_car", "heart": "save_car", "bookmark": "save_car",
    "compare": "compare",
    "contact": "contact_seller", "call": "contact_seller", "phone": "contact_seller",
    "delete": "delete_ad", "remove": "delete_ad",
    "edit": "edit_ad", "update": "edit_ad", "change": "edit_ad",
}


async def handle(
    message: str,
    session: dict,
    llm: GeminiClient,
) -> AsyncGenerator[str, None]:
    msg_lower = message.lower()
    matched_key = None
    for keyword, key in KEYWORDS.items():
        if keyword in msg_lower:
            matched_key = key
            break

    if matched_key and matched_key in WEBSITE_GUIDE:
        yield json.dumps({"type": "token", "content": WEBSITE_GUIDE[matched_key]})
        yield json.dumps({"type": "done", "content": None})
        return

    system = (
        "You are a website guide for a car marketplace. "
        "Answer questions about how to use the website features. "
        "Keep answers short and practical. "
        "Always respond in the same language the user is writing in."
    )
    async for chunk in llm.stream(system, [], message):
        yield json.dumps({"type": "token", "content": chunk})

    yield json.dumps({"type": "done", "content": None})
