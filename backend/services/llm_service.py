import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional
import re

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")


def _clean_llm_output(text: str) -> str:
    # Only remove characters that are genuinely non-Arabic/non-Latin garbage
    # (e.g. CJK, emoji, box-drawing) — keep all Arabic blocks, Latin, digits, punctuation
    text = re.sub(r'[\u4E00-\u9FFF\u3000-\u303F\u2E80-\u2EFF\U0001F000-\U0001FFFF\u2500-\u257F]', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def rewrite_query(query: str) -> List[str]:
    prompt = f"""أنت مترجم طبي متخصص في أمراض القلب. حوّل السؤال التالي بالدارجة التونسية إلى 3 مصطلحات طبية قصيرة بالعربية الفصحى في مجال القلب.
أرجع فقط 3 مصطلحات أو عبارات قصيرة، كل واحدة في سطر منفصل، بدون ترقيم أو شرح أو جمل كاملة.

مثال:
السؤال: احكيلي على التسمع
الجواب:
تسمع القلب
مناطق الإصغاء القلبي
فحص القلب بالسماعة

السؤال: {query}
الجواب:"""
    response = call_openrouter(prompt)
    queries = response.split("\n")
    queries = [q.strip() for q in queries if q.strip()]
    return queries
# -------------------------------
# 1. Build RAG prompt
# -------------------------------
def build_prompt(query: str, context_chunks: List[Dict], history: Optional[List[Dict]]) -> str:
    """
    Build prompt with retrieved context
    """

    context_text = "\n\n".join([
        f"(Page {chunk['page']}) {chunk['text']}"
        for chunk in context_chunks
    ])
    for_history = ""
    if history: 
        for msg in history[-4:]:
            role = "المستخدم" if msg["role"] == "user" else "الطبيب"
            for_history += f"{role}: {msg['content']}\n"

    prompt = f"""أنت طبيب قلب تونسي. تجاوب دايما بالدارجة التونسية العامية فقط.

    قواعد صارمة:
    1. الدارجة التونسية فقط — ممنوع العربية الفصحى تماماً.
    - بدل "يجب" قول "لازم"
    - بدل "يُعتبر" قول "يتحسب"  
    - بدل "يُصنف" قول "نصنفوه"
    - بدل "ينبغي" قول "خاص"
    - بدل "أنا هنا لمساعدتك" — ما تقولهاش خالص
    2. تستعمل بس المعلومات اللي في السياق — ما تختلقش.
    3. إذا ما لقيتش جواب في السياق: "ما عنديش معلومات كافية في الوثيقة."
    4. في الآخر دايما: "هذي للتثقيف — راجع طبيبك."
    5. ممنوع أي حرف غير عربي أو لاتيني في الجواب.
    6. اختصر الإجابة (3 إلى 5 أسطر فقط)
    7. ما تعاودش النص كما هو، فسّر و لخص

    ---------------------
    CONTEXT:
    {context_text}

    ---------------------
    HISTORY:
    {for_history}
    ---------------------

    QUESTION:
    {query}


    ANSWER:
    """

    return prompt.strip()


# -------------------------------
# 2. Call OpenRouter API
# -------------------------------
def call_openrouter(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a helpful cardiologist assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.text}")
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        if content is None:
            return "ما قدرتش نوصل للخادم. حاول مرة أخرى بعد شوية."
        return _clean_llm_output(content)
    except requests.exceptions.Timeout:
        return "الخادم ما جاوبش في الوقت المحدد. حاول مرة أخرى."
    except Exception as e:
        print(f"Groq error: {e}")
        return "ما قدرتش نوصل للخادم. حاول مرة أخرى بعد شوية."


# -------------------------------
# 3. Generate response (main RAG)
# -------------------------------
def generate_response(query: str, context_chunks: List[Dict], history: Optional[List[Dict]]) -> str:
    """
    Full RAG pipeline step:
    context → prompt → LLM → answer
    """

    prompt = build_prompt(query, context_chunks, history)

    answer = call_openrouter(prompt)

    return answer