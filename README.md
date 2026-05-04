# ScopeCreep

AI scope enforcement for freelancers and agencies. Watches client communications, knows the contract, auto-generates change orders with payment collection when out-of-scope work appears.

**Status:** Phase 1 — Manual MVP (Weeks 1–8 of 24). Building in public.

## What It Does

- Parses scope-of-work documents to identify in-scope and out-of-scope items
- Checks incoming client requests against parsed scope
- Generates professional change orders with pricing
- Sends client approval emails with one-click Stripe payment links

## Tech Stack

- Python 3.14 (Phase 1)
- Flask (Phase 2)
- React + Supabase (Phase 3)
- Anthropic Claude API (scope detection)
- Gmail API, Stripe API

## Built By

Miles Lee — building ScopeCreep while learning to code. Following a 24-week gameplan from zero to launched SaaS.