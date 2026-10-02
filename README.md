
# SAT Reading & Writing II — interactive project

This project is a local interactive practice app driven by the supplied PDF.

## Important
The source PDF is **not included in this project archive**. Put your copy at:

`data/Reading Writing Professor II.pdf`

The parser is designed around the supplied volume's structure:
- PDF pages 8–507: Questions 1–500
- PDF pages 509–511: answer sheet
- PDF pages 512–1011: one explanation per question, in question order

The app intentionally keeps the answer and explanation out of the initial `/api/questions` response. They are fetched only when the user submits or explicitly asks to reveal them.

## Run

1. Install Python 3.10+.
2. Put the PDF into `data/`.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start:

```bash
python app.py
```

5. Open the local address shown by Flask.

## Interaction behavior

- One question at a time.
- Four choices A–D.
- Submit is required before correctness is shown.
- An incorrect answer does not automatically reveal the correct answer.
- "Show Correct Answer" reveals the answer only when requested.
- "View Explanation" reveals the explanation only when requested.
- "Try Again" lets the student change their answer and resubmit.
- Previous/Next navigation preserves the current session's answer state.
