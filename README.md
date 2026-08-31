# Splitwise 2.0

A receipt-splitting Progressive Web App that lets you photograph a receipt, automatically extract the line items, assign them to people, and calculate exactly who owes what — no manual math required.

**Status:** Actively in development. Core app is deployed and working end-to-end on mobile; ML extraction accuracy is still being tuned.

**Live app:** https://splitwise2.onrender.com/

---

## Why I'm building this

Most receipt-splitting apps either require manual entry of every item or don't handle itemized splits well (some people order more expensive dishes, some don't drink, someone always forgets to Venmo the tax). I wanted to build the whole pipeline myself — from a photo of a crumpled receipt to a fair, itemized breakdown — as a way to go deep on ML, backend architecture, and frontend engineering in a single project, treated as a genuine 0-to-1 build rather than a tutorial clone.

## How it works

1. **Snap a photo** of a receipt on your phone (PWA, so it installs like a native app)
2. **ML model extracts** line items, prices, tax, and total from the image directly — no separate OCR step
3. **Assign items** to people in the group via tap-to-select chips
4. **Splits are calculated** automatically, with support for equal splits, percentage splits, and exact-amount splits
5. **Balances persist** across a group's transaction history, so you can see running totals, not just one-off splits

## Architecture

### Backend — Flask + SQLite
The split-calculation logic is built as an OOP engine using the **Strategy** and **Factory** patterns, so adding a new split type doesn't touch existing code:

- `SplitStrategy` (abstract base) → `EqualSplit`, `PercentSplit`, `ExactSplit`
- `SplitFactory` selects the right strategy at runtime based on `SplitType`
- `Split` orchestrates the calculation and returns per-person amounts

Groups and transactions are persisted in SQLite. Split amounts are computed and stored at insert time (not recalculated on every read), and manual entries and scanned receipts share a single transactions table, with itemization as an optional layer on top.

### ML — Fine-tuned Donut (Document Understanding Transformer)
Rather than a traditional OCR + regex/NLP pipeline, receipt parsing uses [Donut](https://arxiv.org/abs/2111.15664), an OCR-free vision-encoder/decoder model that reads the receipt image directly and generates structured JSON (items, prices, tax, total) as output.

- Fine-tuned from `naver-clova-ix/donut-base` on the **CORD-v2** receipt dataset
- Trained on Google Colab's free T4 GPU using Hugging Face `transformers` + `pytorch-lightning`
- Ground-truth JSON labels are converted into Donut's flattened XML-style token format (e.g. `<s_menu><s_nm>Coffee</s_nm><s_price>3.50</s_price></s_menu>`) so a text decoder can "generate" structured data directly from pixels
- Trained with mixed precision (fp16) and gradient accumulation to fit Donut's memory footprint on a free-tier GPU

**Current limitation:** tax and service-charge field extraction is unreliable, likely due to those fields being underrepresented during training — actively being tuned (see Roadmap).

### Frontend — Vanilla JS PWA
No framework — a single-page app with screen navigation handled via CSS class toggling. Styled with an iOS-inspired design language:

| Role | Color |
|---|---|
| Background | `#F5F5F7` |
| Primary accent | `#5856D6` |
| Text | `#1C1C1E` |
| Secondary / muted | `#8E8E93` |
| Success / positive | `#34C759` |

### Deployment
Containerized with Docker and deployed on Render's free tier. Confirmed working on mobile as an installable PWA.

---

## Tech stack

**Backend:** Flask, SQLite, pytesseract, Pillow
**ML:** Donut / CORD-v2, Hugging Face Transformers, Google Colab (T4 GPU)
**Frontend:** HTML, CSS, vanilla JavaScript
**Deployment:** Docker, Render
**Tooling:** Git/GitHub, VSCode

---

## Engineering notes worth mentioning

A few non-obvious bugs and decisions along the way, because I think how you debug something says more than the feature list:

- **SQLite foreign keys are opt-in per connection.** `ON DELETE CASCADE` silently does nothing unless `PRAGMA foreign_keys = ON` is set on every connection — an easy trap since the schema *looks* correct.
- **Validate before you compute.** Items with zero assignees are caught in a pre-validation pass and rejected with an HTTP 400 (`unassignedItems`) rather than being silently dropped from the split — a wrong total is worse than an error message.
- **CSS specificity bit me more than once.** `.screen.hidden { display: none }` was needed instead of a standalone `.hidden` class, since `.screen { display: flex }` otherwise won.
- **Duplicated HTML markup can cause silent `getElementById` bugs** — if a block gets copy-pasted instead of edited in place, you can end up wiring event listeners to a stale, invisible element while the visible one does nothing.
- **New buttons need explicit event listeners.** Obvious in hindsight, easy to forget when a feature is added quickly.

## Roadmap

- [ ] Improve Donut fine-tuning for tax/service field extraction (likely needs more/better-balanced training examples)
- [ ] Expand test coverage around split-calculation edge cases
- [ ] Polish onboarding/first-run experience
- [ ] Write up ML-focused and full-stack-focused versions of this project for applications

---

## Running it locally

```bash
git clone <your-repo-url>
cd splitwise-2.0
docker build -t splitwise .
docker run -p 5000:5000 splitwise
```

Then open `http://localhost:5000` in a browser (or on your phone via your local network IP, to test the PWA install flow).

---

*This is a personal learning project spanning ML, backend architecture, and frontend development, built end-to-end from scratch — actively evolving.*