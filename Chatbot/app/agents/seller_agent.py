import json
from typing import AsyncGenerator
from app.core.llm import GeminiClient
from app.core.embedder import Embedder
from app.core.qdrant_client import QdrantSearch


async def handle(
    message: str,
    session: dict,
    llm: GeminiClient,
    embedder: Embedder,
    qdrant: QdrantSearch,
) -> AsyncGenerator[str, None]:
    prefs = session.get("preferences", {})
    is_pricing = "price" in message.lower() or "worth" in message.lower()

    if is_pricing:
        yield json.dumps({"type": "status", "content": "Analyzing similar listings..."})

        car_brand = prefs.get("seller_car_brand") or ""
        car_model = prefs.get("seller_car_model") or ""
        car_year = prefs.get("seller_car_year")
        search_text = f"{car_brand} {car_model} {car_year or ''}".lower()
        vector = embedder.encode(search_text) if search_text else embedder.encode(message.lower())

        results = qdrant.search(
            vector=vector,
            limit=10,
        )

        prices = []
        for r in results:
            p = r.get("price")
            if p:
                try:
                    prices.append(float(p))
                except (ValueError, TypeError):
                    continue

        price_data = {}
        if prices:
            prices.sort()
            price_data = {
                "min": min(prices),
                "max": max(prices),
                "median": prices[len(prices) // 2],
                "recommended": f"{prices[len(prices)//4]:.0f}-{prices[3*len(prices)//4]:.0f}",
                "sample_count": len(prices),
            }

        market_context = f"Found {len(results)} similar listings."
        if price_data:
            market_context += (
                f" Price range: {price_data['min']:.0f} - {price_data['max']:.0f} EGP. "
                f"Median: {price_data['median']:.0f} EGP."
            )

        system = (
            "You are a car pricing advisor for the Egyptian market. "
            "Give specific price recommendations based on market data. "
            "Always respond in the same language the user is writing in."
        )
        async for chunk in llm.stream(
            system, [],
            f"{market_context}\n\nUser question: {message}"
        ):
            yield json.dumps({"type": "token", "content": chunk})

        if price_data:
            yield json.dumps({"type": "price_analysis", "content": price_data})
    else:
        system = (
            "You are a car listing advisor. Give practical tips for selling a car faster: "
            "photo advice, description keywords, price anchoring, best time to post. "
            "Always respond in the same language the user is writing in. "
            "Keep tips concise and actionable."
        )
        async for chunk in llm.stream(system, [], message):
            yield json.dumps({"type": "token", "content": chunk})

    yield json.dumps({"type": "done", "content": None})
