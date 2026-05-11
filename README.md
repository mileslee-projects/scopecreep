# ScopeCreep

AI scope enforcement for freelancers and agencies. Watches client communications, knows the contract, auto-generates change orders with payment collection when out-of-scope work appears.

**Status:** Phase 1 — Manual MVP (Weeks 1–8 of 24). Building in public.

## Progress

- **Week 1 (May 10, 2026):** ✅ SOW Parser v1 + Scope Checker v1 (CLI, keyword matching)
- **Week 2:** Conditionals deep-dive, planning email/Stripe integration
- **Week 3–4:** Functions, smarter parsing, change order template engine
- **Week 5–6:** Stripe payment links + client email sending
- **Week 7–8:** Refactor to OOP + simple Flask web form

## What It Does (Today)

- Parses pasted scope-of-work text into project name, in-scope deliverables, and excluded items
- Accepts a client request and flags it as IN SCOPE, POTENTIAL SCOPE CREEP, or UNCLEAR
- Lists all matched scope items so the freelancer can act on the right ones

## How to Run
python3 main.py

Press Enter to use the sample SOW, or type `paste` to enter your own contract text. Then submit client requests at the prompt. Type `quit` to exit.

## Tech Stack

- Python 3.14 (Phase 1)
- Flask (Phase 2, Weeks 9–16)
- React + Supabase (Phase 3, Weeks 17–24)
- Anthropic Claude API for AI scope detection (Week 13+)
- Gmail API, Asana/Notion/Trello, Stripe

## Built By

Miles Lee — building ScopeCreep while learning to code.