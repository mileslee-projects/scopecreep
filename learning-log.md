# ScopeCreep Learning Log

A running journal of what I learn each week and how it connects to the product.

## Week 1 — May 3, 2026

### What I learned today
- I learned about different types of loops (for, while) and how to use them to iterate over data
- I learned how to merge and split strings, and modify them in other ways
- I learned assign vs compare

### What I built
- I built a parser that buckets a SOW document into in-scope work and out-of-scope work
- This is interactive, as it prompts someone to input their SOW doc
- It goes through and puts things in those bucekts
- I also built a scopecreep tracker that goes through a sent client request and checks it against the SOW for things in vs out of scope

### Ideas for ScopeCreep
**Limitations of v1 keyword matching (found Week 1 — fix in Week 13 with AI):**
- "Add a new Pricing page" → false positive IN SCOPE because "page" matches "About page". Need semantic understanding.
- "Build a registration form" → false positive IN SCOPE because "form" matches "Contact form".
- "Translate the site into Spanish" → currently works because "language" appears in "Multi-language support" — but only by luck. AI would catch synonyms ("translate", "Spanish", "i18n") too.
- "Make it pop more" / "Can you tweak the vibe?" → vague client requests; keyword matching has nothing to grip. AI can ask clarifying questions.

**Possible v1 improvements (without AI):**
- Stop-word list to filter common words: "page", "form", "page", "design", "site" appear too generically.
- Match against full-phrase substrings, not just single words ("shopping cart" as a phrase vs the word "shopping" or "cart" alone).
- Require multiple keyword matches per scope item to count as a hit.

**Long-term ideas:**
- Negation handling — "we don't need a blog anymore" mentions "blog" but shouldn't flag scope creep.
- Tone customization — clients of friendly designer vs. corporate consultant need different change order voices.
- Confidence-weighted match scoring instead of binary in/out.

### Questions for next session
- (fill in at end of session)

## Week 2 — May 25, 2026

### What I learned today

Functions (def, parameters, return vs print, default arguments, keyword arguments)
Dictionaries (key-value pairs, dict["key"] access)
How functions eliminate duplication (find_matches replaced the two copied loops)
File writing (with open(...) as f, "w"/"r" modes)
JSON (json.dump, json.load) for persistence
float() to convert input strings to numbers; os.path.exists(); enumerate()
Indentation is structure, not decoration (learned the hard way via IndentationError)
NameError means "used a name that doesn't exist"

### What I built:

Refactored parser + checker into parse_sow(), find_matches(), check_scope()
Change Order Template Engine (calculate_pricing(), create_change_order(), save_change_order())
Unified menu-driven CLI app
JSON persistence for change order history