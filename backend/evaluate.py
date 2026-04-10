import csv
import time
import requests

BACKEND_URL = "https://rag-cardiology.up.railway.app"
ERROR_PHRASES = ["ما قدرتش نوصل للخادم", "حاول مرة أخرى", "الخادم ما جاوبش"]

def score_keywords(answer: str, keywords_raw: str) -> tuple[int, float]:
    keywords = [k.strip() for k in keywords_raw.split("|")]
    hits = sum(1 for kw in keywords if kw in answer)
    return hits, round(hits / len(keywords), 2)

def check_scope_refusal(answer: str, should_succeed: bool) -> bool:
    refusal_phrase = "ما عنديش معلومات كافية"
    if not should_succeed:
        return refusal_phrase in answer
    return True

def check_retrieval(sources: list, should_succeed: bool) -> bool:
    if should_succeed:
        return len(sources) > 0
    return True

def ask(question: str, history: list) -> dict:
    response = requests.post(
        f"{BACKEND_URL}/ask",
        json={"pdf_id": "default", "question": question, "history": history},
        timeout=60
    )
    return response.json()

def ask_with_retry(question: str, history: list, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            response = ask(question, history)
            answer = response.get("answer", "")
            if not any(phrase in answer for phrase in ERROR_PHRASES):
                return response
            print(f"  ⚠ rate limited (attempt {attempt + 1}/{retries}), waiting 20s...")
            time.sleep(20)
        except Exception as e:
            print(f"  ⚠ request failed (attempt {attempt + 1}/{retries}): {e}, waiting 20s...")
            time.sleep(20)
    print("  ✗ all retries exhausted, recording as failed")
    return {"answer": "FAILED", "sources": []}

# --- main ---
with open("evaluation_dataset.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

output_fields = [
    "question_darija", "expected_topic", "retrieval_should_succeed",
    "answer", "sources_count", "keyword_hits", "keyword_score",
    "retrieval_ok", "scope_check_pass", "latency_ms"
]

history = []
results = []

for row in rows:
    is_followup = "follow-up" in row["notes"]
    if not is_followup:
        history = []

    question = row["question_darija"]
    should_succeed = row["retrieval_should_succeed"].strip().upper() == "TRUE"

    start = time.time()
    response = ask_with_retry(question, history)
    latency = round((time.time() - start) * 1000)

    answer = response.get("answer", "")
    sources = response.get("sources", [])

    print(f"  answer preview: {answer[:80]}")

    hits, score = score_keywords(answer, row["expected_keywords_in_answer"])
    retrieval_ok = check_retrieval(sources, should_succeed)
    scope_pass = check_scope_refusal(answer, should_succeed)

    history.append({"role": "user", "content": question})
    history.append({"role": "ai", "content": answer})
    history = history[-4:]

    results.append({
        "question_darija": question,
        "expected_topic": row["expected_topic"],
        "retrieval_should_succeed": row["retrieval_should_succeed"],
        "answer": answer,
        "sources_count": len(sources),
        "keyword_hits": hits,
        "keyword_score": score,
        "retrieval_ok": retrieval_ok,
        "scope_check_pass": scope_pass,
        "latency_ms": latency
    })

    print(f"✓ [{row['expected_topic']}] score={score} latency={latency}ms")
    time.sleep(10)

with open("evaluation_results.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=output_fields)
    writer.writeheader()
    writer.writerows(results)

# --- summary ---
total = len(results)
failed = [r for r in results if r["answer"] == "FAILED"]
valid = [r for r in results if r["answer"] != "FAILED"]
in_scope = [r for r in results if r["retrieval_should_succeed"] == "TRUE"]
out_of_scope = [r for r in results if r["retrieval_should_succeed"] == "FALSE"]

print(f"\n{'='*40}")
print(f"Total questions:    {total}")
print(f"Valid responses:    {len(valid)}/{total}")
print(f"Failed (API):       {len(failed)}/{total}")
if valid:
    print(f"Keyword score avg:  {sum(r['keyword_score'] for r in valid) / len(valid):.2f}")
print(f"Retrieval success:  {sum(1 for r in in_scope if r['retrieval_ok'])}/{len(in_scope)}")
if out_of_scope:
    print(f"Scope refusals:     {sum(1 for r in out_of_scope if r['scope_check_pass'])}/{len(out_of_scope)}")
print(f"Avg latency:        {sum(r['latency_ms'] for r in results) / total:.0f}ms")
print(f"{'='*40}")