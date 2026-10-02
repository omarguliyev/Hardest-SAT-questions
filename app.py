
from flask import Flask, render_template, jsonify, abort
from pathlib import Path
import fitz
import re
import json

app = Flask(__name__)
PDF_PATH = Path(__file__).parent / "data" / "Reading Writing Professor II.pdf"

def clean_lines(text):
    out = []
    for raw in text.splitlines():
        s = re.sub(r"\s+", " ", raw).strip()
        if not s:
            continue
        # Remove recurring book footer/header artifacts.
        if s == "Telegram channel - @SATLeague":
            continue
        if s == "R E A D I N G  &  W R I T I N G  I I":
            continue
        out.append(s)
    return out

def parse_question_page(page, qnum):
    lines = clean_lines(page.get_text())
    # Drop page/section decoration and the question-number heading.
    while lines and (lines[0].isdigit() or lines[0] in {"R E A D I N G", "READING"}):
        lines.pop(0)

    q_idx = None
    for i, s in enumerate(lines):
        if s.endswith("?") or s.endswith("!"):
            q_idx = i
            break
    if q_idx is None:
        # Most questions have a sentence ending in ?; fall back to the last
        # line before the first A choice.
        q_idx = next((i for i, s in enumerate(lines) if s == "A"), len(lines)-1)

    question = " ".join(lines[q_idx:q_idx+1])
    # In a few layouts the question stem wraps; collect through the first A.
    a_idx = next((i for i, s in enumerate(lines[q_idx+1:], q_idx+1) if s == "A"), None)
    if a_idx is None:
        a_idx = next((i for i, s in enumerate(lines) if s == "A"), len(lines))
    stem_lines = lines[q_idx:a_idx]
    question = " ".join(stem_lines)

    choices = {}
    i = a_idx
    for letter in "ABCD":
        if i >= len(lines) or lines[i] != letter:
            # Search forward a little in case OCR/text extraction split things.
            found = next((j for j in range(i, min(i+8, len(lines))) if lines[j] == letter), None)
            if found is None:
                break
            i = found
        i += 1
        vals = []
        while i < len(lines) and lines[i] not in "ABCD":
            vals.append(lines[i])
            i += 1
        choices[letter] = " ".join(vals).strip()

    # Passage/table material is everything before the question stem.
    passage = " ".join(lines[:q_idx]).strip()

    return {
        "id": qnum,
        "passage": passage,
        "question": question,
        "choices": choices,
        "page": qnum + 7,
    }

def parse_answers(pages):
    text = "\n".join(p.get_text() for p in pages)
    # Answer sheet uses number + letter, sometimes split across lines.
    pairs = re.findall(r"(?m)^\s*(\d{1,3})\s*$\s*([ABCD])\s*$", text)
    ans = {}
    for n, letter in pairs:
        n = int(n)
        if 1 <= n <= 500:
            ans[n] = letter
    return ans

def parse_explanation_page(page, qnum):
    lines = clean_lines(page.get_text())
    # Find the "CORRECT ANSWER X" marker.
    correct = None
    for i, s in enumerate(lines):
        m = re.search(r"CORRECT ANSWER\s+([ABCD])", s, re.I)
        if m:
            correct = m.group(1).upper()
            break
    if correct is None:
        # Usually answer-sheet data is authoritative; explanation page can omit
        # the marker in unusual extraction cases.
        correct = ""

    # Keep explanation headings/content but omit page number and decorative headers.
    body = []
    for s in lines:
        if re.fullmatch(r"\d{3,4}", s):
            continue
        if s.upper().startswith("CORRECT ANSWER"):
            continue
        body.append(s)
    explanation = "\n\n".join(body).strip()
    return {"correct_from_explanation": correct, "explanation": explanation}

def build_bank():
    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"Place the source PDF at: {PDF_PATH}"
        )
    doc = fitz.open(PDF_PATH)
    if len(doc) < 1011:
        raise ValueError(f"Expected the supplied volume to have at least 1011 pages; found {len(doc)}.")

    questions = []
    for q in range(1, 501):
        page = doc[q + 6]       # PDF page 8 -> question 1
        questions.append(parse_question_page(page, q))

    # PDF page 509-511 contain the answer sheet. The exact page numbers are
    # stable in the supplied volume.
    answers = parse_answers([doc[508], doc[509], doc[510]])

    # PDF pages 512-1011: one explanation per question, same order.
    for q in range(1, 501):
        exp = parse_explanation_page(doc[511 + q - 1], q)
        questions[q-1]["answer"] = answers.get(q) or exp["correct_from_explanation"]
        questions[q-1]["explanation"] = exp["explanation"]

    return questions

BANK = None

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/questions")
def questions():
    global BANK
    if BANK is None:
        BANK = build_bank()
    # Do not expose answers/explanations in the initial payload.
    public = []
    for q in BANK:
        public.append({
            "id": q["id"],
            "passage": q["passage"],
            "question": q["question"],
            "choices": q["choices"],
            "page": q["page"],
        })
    return jsonify(public)

@app.get("/api/questions/<int:qnum>")
def question(qnum):
    global BANK
    if BANK is None:
        BANK = build_bank()
    if not 1 <= qnum <= 500:
        abort(404)
    q = BANK[qnum-1]
    return jsonify({
        "id": q["id"],
        "passage": q["passage"],
        "question": q["question"],
        "choices": q["choices"],
        "page": q["page"],
        "answer": q["answer"],
        "explanation": q["explanation"],
    })

if __name__ == "__main__":
    app.run(debug=True)
