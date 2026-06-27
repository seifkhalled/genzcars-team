import json
from langchain_core.messages import SystemMessage, HumanMessage

COMPARE_SYSTEM = """You are an expert automotive analyst for the Egyptian car market.
You have analyzed multiple cars individually. Now compare them head-to-head
and produce a final verdict.
Return ONLY valid JSON — no markdown, no explanation, no extra text.
"""

COMPARE_HUMAN_TEMPLATE = """Here are the individual analyses for {n} cars being compared:

{car_analyses_text}

{language_instruction}Produce a head-to-head comparison and final verdict using this exact JSON structure:
{{
  "head_to_head": {{
    "best_value": "ad_id of best value car",
    "most_reliable": "ad_id of most reliable car",
    "lowest_running_cost": "ad_id of lowest running cost",
    "best_resale": "ad_id of best resale value"
  }},

  "score_comparison": [
    {{
      "category": "Value for Money",
      "scores": {{"ad_id_1": 8, "ad_id_2": 6, "ad_id_3": 7}}
    }},
    {{
      "category": "Reliability",
      "scores": {{"ad_id_1": 7, "ad_id_2": 9, "ad_id_3": 6}}
    }},
    {{
      "category": "Running Cost",
      "scores": {{"ad_id_1": 8, "ad_id_2": 7, "ad_id_3": 9}}
    }},
    {{
      "category": "Resale Value",
      "scores": {{"ad_id_1": 9, "ad_id_2": 6, "ad_id_3": 7}}
    }},
    {{
      "category": "Overall",
      "scores": {{"ad_id_1": 8, "ad_id_2": 7, "ad_id_3": 7}}
    }}
  ],

  "key_differences": [
    "Specific factual difference between the cars",
    "Specific factual difference between the cars",
    "Specific factual difference between the cars"
  ],

  "verdict": {{
    "winner_ad_id": "ad_id of overall best choice",
    "confidence": "high | medium | low",
    "reasoning": "3-4 sentences explaining why this car wins overall, referencing specific data points from the analyses",
    "runner_up_ad_id": "ad_id of second best, or null if only 2 cars",
    "runner_up_reasoning": "1-2 sentences on why this is second choice"
  }},

  "buyer_persona_match": [
    {{
      "persona": "Family with kids",
      "best_match_ad_id": "ad_id",
      "reason": "1 sentence"
    }},
    {{
      "persona": "Daily commuter",
      "best_match_ad_id": "ad_id",
      "reason": "1 sentence"
    }},
    {{
      "persona": "Budget-conscious buyer",
      "best_match_ad_id": "ad_id",
      "reason": "1 sentence"
    }},
    {{
      "persona": "First-time car owner",
      "best_match_ad_id": "ad_id",
      "reason": "1 sentence"
    }}
  ],

  "final_recommendation": "2-3 sentences of direct, honest advice to the buyer. Which car to buy and why, or what to watch out for before deciding."
}}
"""


async def compare(car_analyses: list[dict], llm, language: str = "en") -> dict:
    lang_instr = ""
    if language == "ar":
        lang_instr = "Respond in Arabic. All text fields in the JSON must be in Arabic.\n\n"

    car_texts = []
    for i, ca in enumerate(car_analyses, 1):
        car_texts.append(
            f"CAR {i}: {ca.get('brand', 'Unknown')} {ca.get('model', 'Unknown')} "
            f"{ca.get('year', '')} — {ca.get('price', 0)} EGP\n"
            f"Analysis: {json.dumps(ca, ensure_ascii=False)}"
        )

    human_msg = COMPARE_HUMAN_TEMPLATE.format(
        n=len(car_analyses),
        car_analyses_text="\n\n".join(car_texts),
        language_instruction=lang_instr,
    )

    response = await llm.ainvoke([
        SystemMessage(content=COMPARE_SYSTEM),
        HumanMessage(content=human_msg),
    ])
    content = response.content.strip()

    try:
        cleaned = content.removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError):
        pass

    retry_response = await llm.ainvoke([
        SystemMessage(content=COMPARE_SYSTEM + "\nYour previous response was not valid JSON. Return ONLY the JSON object, nothing else."),
        HumanMessage(content=human_msg),
    ])
    retry_content = retry_response.content.strip()
    try:
        cleaned = retry_content.removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError):
        raise ValueError("LLM failed to return valid JSON after retry")
