import logging
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import llm_router
from app.enums import TaskType

logger = logging.getLogger(__name__)

ARABIC_CORRECTIONS = """أنت مساعد تصحيح للتعرف على الصوت في سوق السيارات.
مهمتك: إصلاح الأخطاء الشائعة في التعرف على الكلام (STT) في سياق السيارات.

قواعد التصحيح:
1. صحح أسماء ماركات السيارات (مثال: "تويوتا" ← "تويوتا"، "بي إم دبليو" ← "بي إم دبليو")
2. صحح أسماء موديلات السيارات (مثال: "كورلا" ← "كورولا"، "كامري" ← "كامري")
3. صحح المصطلحات الفنية (مثال: "أوتوماتيك" ← "أوتوماتيك"، "دفع رباعي" ← "دفع رباعي")
4. حافظ على المعنى الأصلي للجملة
5. لا تغير الكلمات التي تبدو صحيحة
6. أعد النص المصحح فقط، بدون أي إضافات أو تعليقات"""

ENGLISH_CORRECTIONS = """You are a speech recognition autocorrection assistant for a car marketplace.
Your task: fix common STT (speech-to-text) errors in the context of cars and automotive.

Correction rules:
1. Fix car brand names (e.g., "Toyoto" → "Toyota", "BM Double You" → "BMW", "Mercedes" → "Mercedes-Benz")
2. Fix car model names (e.g., "Corolla" → "Corolla", "Camry" → "Camry", "Civic" → "Civic")
3. Fix automotive terms (e.g., "automatic" → "automatic", "all-wheel drive" → "all-wheel drive")
4. Fix numbers and prices (e.g., "fifteen thousand" → "15000", "twenty twenty three" → "2023")
5. Fix common homophone errors (e.g., "there" → "their" if context appropriate, "to" → "too"/"two")
6. Preserve the original meaning of the sentence
7. Return ONLY the corrected text, no explanations or extra text"""


async def autocorrect_transcript(text: str, language: str) -> str:
    if not text or not text.strip():
        return text

    system_prompt = ARABIC_CORRECTIONS if language == "ar" else ENGLISH_CORRECTIONS

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Original transcript:\n{text}\n\nCorrected transcript:"),
    ]

    try:
        result = await llm_router.ainvoke_task(
            TaskType.ROUTER,
            messages,
        )
        corrected = result.content.strip() if hasattr(result, "content") else str(result).strip()

        if corrected:
            logger.info(
                "Autocorrect: '%s' -> '%s' (lang=%s)",
                text[:80], corrected[:80], language,
            )
            return corrected

        logger.warning("Autocorrect returned empty result, using original text")
        return text

    except Exception as e:
        logger.warning("Autocorrect failed for lang=%s: %s, using original text", language, e)
        return text
