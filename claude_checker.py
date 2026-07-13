# claude_checker.py — AI-powered scope creep detection using Claude
#
# Replaces the keyword matcher in main.py with Claude for the web app.
# The CLI (main.py) still uses keywords — that's fine for testing.

import json
import anthropic
from settings import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def check_scope_with_claude(request, sow):
    """Check a client request against the SOW using Claude.

    Returns a dict compatible with what check.html and gmail.html expect:
    {
        verdict: "scope_creep" | "in_scope" | "unclear",
        reason: "explanation from Claude",
        matched_excluded: [{item, confidence, matched_words}],
        matched_in_scope: [{item, confidence, matched_words}],
    }
    """

    in_scope_list  = "\n".join(f"- {item}" for item in sow["in_scope"])
    out_scope_list = "\n".join(f"- {item}" for item in sow["out_of_scope"])

    prompt = f"""You are a scope-of-work analyzer for freelancers and agencies.

PROJECT: {sow["project_name"]}

IN SCOPE:
{in_scope_list}

OUT OF SCOPE (excluded):
{out_scope_list}

CLIENT REQUEST: "{request}"

Determine if this request is scope creep, in scope, or unclear.
Only flag as scope_creep if the request clearly asks for something in the excluded list or something not covered anywhere in the SOW.
Do NOT flag generic emails, newsletters, or unrelated content as scope creep.

Respond with JSON only, no other text:
{{
  "verdict": "scope_creep" or "in_scope" or "unclear",
  "confidence": <0-100>,
  "reason": "<one sentence explanation>",
  "matched_excluded": ["<relevant excluded item>"],
  "matched_in_scope": ["<relevant in-scope item>"]
}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if Claude wrapped the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)

        matched_excluded = [
            {"item": item, "confidence": data["confidence"], "matched_words": [item]}
            for item in data.get("matched_excluded", [])
        ]
        matched_in_scope = [
            {"item": item, "confidence": data["confidence"], "matched_words": [item]}
            for item in data.get("matched_in_scope", [])
        ]

        return {
            "verdict": data["verdict"],
            "reason": data.get("reason", ""),
            "matched_excluded": matched_excluded,
            "matched_in_scope": matched_in_scope,
        }

    except Exception as e:
        # If anything goes wrong, return unclear rather than crashing
        print(f"  [Claude checker error] {e}")
        return {
            "verdict": "unclear",
            "reason": "Could not analyze request — try again.",
            "matched_excluded": [],
            "matched_in_scope": [],
        }


def draft_ghostwriter_response(client_request, sow, tone="diplomatic"):
    """Draft a professional email response to a scope creep request.

    tone: "diplomatic" | "assertive" | "brief"
    Returns the drafted email as a string.
    """

    tone_instructions = {
        "diplomatic": "warm and collaborative — acknowledge the request positively, explain the scope boundary kindly, and offer a clear path forward",
        "assertive":  "professional and direct — clearly state the boundary, reference the agreement, and propose next steps without over-apologizing",
        "brief":      "short and to the point — 3-4 sentences max, no fluff",
    }

    in_scope_list  = "\n".join(f"- {item}" for item in sow["in_scope"])
    out_scope_list = "\n".join(f"- {item}" for item in sow["out_of_scope"])

    prompt = f"""You are a ghostwriter helping a freelancer respond to a client who has made an out-of-scope request.

PROJECT: {sow["project_name"]}

IN SCOPE:
{in_scope_list}

OUT OF SCOPE (excluded):
{out_scope_list}

CLIENT REQUEST: "{client_request}"

Write a {tone_instructions[tone]} email reply from the freelancer to the client.
The email should:
1. Acknowledge the client's request
2. Explain that this falls outside the agreed scope
3. Let them know you're happy to handle it as a change order
4. Keep the relationship intact

Write only the email body (no subject line). Use placeholders like [Client Name] and [Your Name] where appropriate."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"  [Ghostwriter error] {e}")
        return "Could not generate draft — try again."
