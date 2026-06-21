# ScopeCreep — Session Briefing for AI Tutors

## Who I Am
- Name: Miles Lee
- Email: miles@yuzu.health
- Company: Yuzu Health (TPA, Series B). This is a side hustle to make money, nothing to do with Yuzu
- Coding background: starting from near-zero, ~3 months into learning
- Time budget: 1 weeknight (~1-2 hrs) + Sundays (4-5 hrs)

## What I'm Building
ScopeCreep — SaaS that auto-detects scope creep in client communications and generates change orders with payment links. Phase 1 = manual Python MVP. Target: ship beta by late August 2026.

## Current Progress (as of {today's date})
- Repo: https://github.com/mileslee-projects/scopecreep
- Phase 1 Week 3 complete: Smart SOW Parser v2, Scope Checker with confidence scoring, Change Order Engine, Unified CLI, JSON persistence, discount support
- Next sprint (Weeks 4–13): pricing models → email sending → Stripe → Flask web app → Gmail API → Claude API → auth → deployment → beta launch

## Editor & Tools
- Cursor (with Claude Sonnet)
- Python 3.14, Flask (Phase 2), Anthropic SDK (Week 13), SendGrid + smtplib, Stripe
- macOS

## How I Want to Be Taught
- Walk me through step-by-step when concepts are new
- Plan/architect with you in chat, type with Cursor, review with you again
- "Never accept AI code I can't explain" — quiz me on what I commit
- I'm shipping by late August so we move fast; cut tutorials, build more

## Active Decisions
- Cutting from MVP: PM tool integrations, React rebuild, multiple pricing models, OOP refactor
    When the MVP is creating we will want to re-eval these options and figure out what makes the most sense to do next
- Keeping: Gmail-only V1, Flask web app, Claude API for scope detection, Stripe payments

## Locked Plan (revised June 14, 2026)

**Ship target:** App live at a URL + 3–5 beta users by August 23, 2026.

**Working model:** Plan with Cowork tutor, build with Cursor, review with tutor. Moderate AI lean.

**Cut from MVP (defer to V1.1):** PM tools, React rebuild, fixed/milestone pricing models, OOP refactor, Product Hunt launch.

**Compressed roadmap:**
- Week 4 (Jun 21): Change order status tracking + settings module
- Week 5 (Jun 28): Email sending + Stripe payment links
- Week 6 (Jul 5): Flask web app
- Week 7 (Jul 12): Gmail API integration
- Week 8 (Jul 19): Claude API for scope detection
- Week 9 (Jul 26): Auth + database
- Week 10 (Aug 2): Polish + deploy + landing page
- Week 11 (Aug 9): Onboarding + first 2 beta users
- Week 12 (Aug 16): Beta feedback iteration
- Week 13 (Aug 23): Public launch with 3–5 active beta users

**Scope discipline rule:** Every feature must answer "does this need to exist by Aug 23?" If no → V1.1 backlog. Push back if the tutor drifts.

## Files to Read First
- `main.py` — the entire current app
- `learning-log.md` — what I've learned each week + product ideas surfaced
- `README.md` — project overview + week-by-week progress