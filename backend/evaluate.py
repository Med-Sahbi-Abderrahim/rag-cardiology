import csv
import time
import requests

BACKEND_URL = "https://rag-cardiology.up.railway.app"

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
    response = ask(question, history)
    latency = round((time.time() - start) * 1000)

    answer = response.get("answer", "")
    print(f"  answer preview: {answer[:80]}")
    time.sleep(3)
    sources = response.get("sources", [])

    hits, score = score_keywords(answer, row["expected_keywords_in_answer"])
    retrieval_ok = check_retrieval(sources, should_succeed)
    scope_pass = check_scope_refusal(answer, should_succeed)

    # update history AFTER getting the answer
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

with open("evaluation_results.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=output_fields)
    writer.writeheader()
    writer.writerows(results)

# --- summary ---
total = len(results)
in_scope = [r for r in results if r["retrieval_should_succeed"] == "TRUE"]
out_of_scope = [r for r in results if r["retrieval_should_succeed"] == "FALSE"]

print(f"\nTotal questions:    {total}")
print(f"Keyword score avg:  {sum(r['keyword_score'] for r in results) / total:.2f}")
print(f"Retrieval success:  {sum(1 for r in in_scope if r['retrieval_ok'])}/{len(in_scope)}")
print(f"Scope refusals:     {sum(1 for r in out_of_scope if r['scope_check_pass'])}/{len(out_of_scope)}")
print(f"Avg latency:        {sum(r['latency_ms'] for r in results) / total:.0f}ms")