import requests
import json
import time
from dotenv import load_dotenv
import os

# 1. Load Environment Variables
load_dotenv()
OPENROUTER_API_KEY = "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"
# 2. Safety Check: Stop if key is missing
if not OPENROUTER_API_KEY:
    print("❌ ERROR: OPENROUTER_API_KEY not found. Check your .env file!")
    exit()

URL = "https://openrouter.ai/api/v1/chat/completions"

# 3. Use current/active model IDs
MODELS_TO_TEST = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "stepfun/step-3.5-flash:free/api",
    "openai/gpt-oss-120b:free",
    "qwen/qwen3-coder:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free"

]

test_cases = [
    {
        "id": 1,
        "query": "شنوا العادات اللي لازم نبدلها كي يبدا عندي ضغط دم؟",
        "context": "ارتفاع ضغط الدم هو كي يبدا الدم يضغط بقوة على عروقك. الملح هو العدو اللول. لازم تنقص منه وتتبع دواك بانتظام باش تحمي قلبك."
    },
    {
        "id": 2,
        "query": "وجيعة الصدر وقتاش تولي تخوف؟",
        "context": "وجيعة الصدر تنجم تكون علامة جلطة. إذا الوجيعة قوية وماشية لليد اليسار، لازم تمشي للاستعجالي طول (Urgence)."
    }
]

def call_model(model_id, query, context):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000", # Required for OpenRouter Free models
    }
    
    prompt = f"""
    استعمل المعلومات التالية فقط للإجابة على السؤال. 
    جاوب بالدارجة التونسية ببساطة.
    
    المعلومات: {context}
    
    السؤال: {query}
    """
    
    data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "You are a helpful Tunisian medical assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Request failed: {str(e)}"

# --- EXECUTION ---
all_results = []
print(f"🚀 Starting Comparison using key starting with: {OPENROUTER_API_KEY[:5]}...")

for case in test_cases:
    case_results = {"case_id": case['id'], "query": case['query'], "responses": {}}
    print(f"\nTesting Query: {case['query']}")
    
    for model in MODELS_TO_TEST:
        print(f"  - Running {model}...")
        answer = call_model(model, case['query'], case['context'])
        case_results["responses"][model] = answer
        time.sleep(1.5) # Slight delay to be safe
    
    all_results.append(case_results)

with open("model_comparison_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=4)

print("\n✅ Done! Check 'model_comparison_results.json'")