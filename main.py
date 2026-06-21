# main.py — ScopeCreep Phase 1
# Organized into functions: parse_sow, find_matches, check_scope,
# calculate_pricing, create_change_order

from datetime import date
import json
import os

# Section header keywords — map common SOW phrasings to our two scope buckets
SECTION_KEYWORDS = {
    "in_scope": [
        "deliverables",
        "scope of work",
        "scope",
        "included",
        "what's included",
        "in scope",
    ],
    "out_of_scope": [
        "out of scope",
        "out-of-scope",
        "excluded",
        "exclusions",
        "not included",
        "what's not included",
    ],
}

BULLET_MARKERS = "-*•"

# A sample SOW for testing
SAMPLE_SOW = """
Project: Marketing Website Redesign

Deliverables:
- Homepage design and development
- About page
- Contact form with email integration
- Mobile responsive layout
- Basic SEO setup

Excluded:
- Blog functionality
- E-commerce / shopping cart
- Multi-language support
- Custom CMS
"""


# ===== FUNCTIONS =====

def detect_section(line):
    """Return 'in_scope', 'out_of_scope', or None based on whether the
    line looks like a section header."""
    line_lower = line.lower().strip().rstrip(":").strip()

    # Check out_of_scope first since "scope" appears in both keyword lists
    for keyword in SECTION_KEYWORDS["out_of_scope"]:
        if keyword in line_lower:
            return "out_of_scope"
    for keyword in SECTION_KEYWORDS["in_scope"]:
        if keyword in line_lower:
            return "in_scope"
    return None

def parse_bullet_item(line):
    """If the line is a bullet or numbered list item, return its content
    (with the marker stripped). Otherwise return None."""
    line = line.strip()
    if not line:
        return None

    # Bullet markers: -, *, •
    if line[0] in BULLET_MARKERS:
        return line[1:].strip()

    # Numbered: digit(s) followed by . or )
    # E.g., "1. Homepage" or "12) About page"
    i = 0
    while i < len(line) and line[i].isdigit():
        i += 1
    if i > 0 and i < len(line) and line[i] in ".)":
        return line[i + 1:].strip()

    return None

def parse_sow(sow_text):
    """Parse a scope-of-work string into structured data.
    Returns a dict with project_name, in_scope, and out_of_scope.
    Supports multiple bullet styles (-, *, •, 1., 2.) and section header variations."""
    project_name = ""
    in_scope = []
    out_of_scope = []
    current_section = None

    for line in sow_text.split("\n"):
        line = line.strip()
        if line == "":
            continue

        # Check for project name (handle "Project:" and "Project Name:")
        line_lower = line.lower()
        if line_lower.startswith("project:") or line_lower.startswith("project name:"):
            project_name = line.split(":", 1)[1].strip()
            current_section = None
            continue

        # Check for a section header
        section = detect_section(line)
        if section is not None:
            current_section = section
            continue

        # Check for a list item
        item = parse_bullet_item(line)
        if item and current_section is not None:
            if current_section == "in_scope":
                in_scope.append(item)
            elif current_section == "out_of_scope":
                out_of_scope.append(item)

    return {
        "project_name": project_name,
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
    }

def score_match(item, request_lower):
    """Score how confidently a scope item matches the request.
    Returns (matched_words, confidence_percent) where confidence is 0-100.
    100 = exact phrase match. Otherwise: proportion of significant words found."""
    item_lower = item.lower()

    # Exact phrase match → 100% confidence
    if item_lower in request_lower:
        return [item_lower], 100

    # Otherwise: score by proportion of significant words that appear
    item_words = item_lower.split()
    significant_words = [w for w in item_words if len(w) > 3]

    if not significant_words:
        return [], 0

    matched = [w for w in significant_words if w in request_lower]

    if not matched:
        return [], 0

    confidence = round((len(matched) / len(significant_words)) * 100)
    return matched, confidence


def score_all_matches(items, request_lower):
    """Score every item against the request.
    Returns a list of dicts: [{item, matched_words, confidence}, ...]
    Only includes items with confidence > 0. Sorted highest confidence first."""
    results = []
    for item in items:
        matched, confidence = score_match(item, request_lower)
        if confidence > 0:
            results.append({
                "item": item,
                "matched_words": matched,
                "confidence": confidence,
            })
    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results

def check_scope(request, sow):
    """Check a client request against parsed scope using confidence scoring.
    Returns a dict with verdict and scored matches for each scope side."""
    request_lower = request.lower()

    matched_excluded = score_all_matches(sow["out_of_scope"], request_lower)
    matched_in_scope = score_all_matches(sow["in_scope"], request_lower)

    # The highest-confidence match wins
    top_excluded = matched_excluded[0]["confidence"] if matched_excluded else 0
    top_in_scope = matched_in_scope[0]["confidence"] if matched_in_scope else 0

    if top_excluded > 0 and top_excluded >= top_in_scope:
        verdict = "scope_creep"
    elif top_in_scope > 0:
        verdict = "in_scope"
    else:
        verdict = "unclear"

    return {
        "verdict": verdict,
        "matched_excluded": matched_excluded,
        "matched_in_scope": matched_in_scope,
    }


def calculate_pricing(hours, rate, is_rush=False, discount_percent=0):
    """Calculate the cost of a scope change.
    Returns a dict with subtotal, rush_fee, discount, and total."""
    subtotal = hours * rate
    if is_rush:
        rush_fee = subtotal * 0.5
    else:
        rush_fee = 0
    pre_discount_total = subtotal + rush_fee
    discount = pre_discount_total * (discount_percent / 100)
    total = pre_discount_total - discount
    return {
        "subtotal": subtotal,
        "rush_fee": rush_fee,
        "discount": discount,
        "total": total,
    }


def create_change_order(client_name, project_name, scope_item, hours, rate, is_rush=False):
    """Generate a professional change order document as a formatted string."""
    pricing = calculate_pricing(hours, rate, is_rush)
    today = date.today().strftime("%B %d, %Y")

    order = f"""
========================================
              CHANGE ORDER
========================================

Client:   {client_name}
Project:  {project_name}
Date:     {today}

----------------------------------------
REQUESTED CHANGE (OUT OF SCOPE)
----------------------------------------
{scope_item}

----------------------------------------
PRICING
----------------------------------------
Estimated hours:  {hours}
Hourly rate:      ${rate:.2f}
Subtotal:         ${pricing['subtotal']:.2f}"""

    if is_rush:
        order += f"\nRush fee (50%):   ${pricing['rush_fee']:.2f}"

    order += f"""
Total:            ${pricing['total']:.2f}

----------------------------------------
This work falls outside the original scope of work.
Please approve before work begins.

   [ APPROVE & PAY ]      [ DISCUSS ]

========================================
"""
    return order
def save_change_order(order_text, client_name):
    """Save a change order to a .txt file named after the client and date.
    Returns the filename."""
    today = date.today().strftime("%Y-%m-%d")
    safe_client = client_name.lower().replace(" ", "_")
    filename = f"change_order_{safe_client}_{today}.txt"
    with open(filename, "w") as f:
        f.write(order_text)
    return filename
def print_menu():
    """Display the main menu."""
    print()
    print("=" * 40)
    print("  SCOPECREEP")
    print("=" * 40)
    print("  [1] Upload SOW")
    print("  [2] Check a client request")
    print("  [3] Create a change order")
    print("  [4] View change order history")
    print("  [5] Quit")
    print("=" * 40)

HISTORY_File = "change_order_history.json"

def load_history():
    """Load change order history from the JSON file.
    Returns an empty list if the file doesn't exist yet."""
    if os.path.exists(HISTORY_File):
        with open(HISTORY_File, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    """Save the change order history list to the JSON file."""
    with open(HISTORY_File, "w") as f:
        json.dump(history, f, indent=2)


# ===== MAIN PROGRAM =====

# State that persists across the menu loop
current_sow = None
change_order_history = load_history()

while True:
    print_menu()
    choice = input("Choose an option (1-5): ").strip()

    if choice == "1":
        # --- Upload SOW ---
        print("\nPress ENTER to use the sample SOW, or type 'paste' to enter your own:")
        sub_choice = input("> ").strip().lower()
        if sub_choice == "paste":
            print("\nPaste your SOW. Type 'END' on a new line when finished:\n")
            user_lines = []
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                user_lines.append(line)
            sow_text = "\n".join(user_lines)
        else:
            sow_text = SAMPLE_SOW
        current_sow = parse_sow(sow_text)
        print(f"\nLoaded SOW for project: {current_sow['project_name']}")
        print(f"  In scope: {len(current_sow['in_scope'])} items")
        print(f"  Out of scope: {len(current_sow['out_of_scope'])} items")

    elif choice == "2":
        # --- Check a client request ---
        if current_sow is None:
            print("\nNo SOW loaded yet. Use option [1] first.")
            continue
        request = input("\nEnter the client request: ").strip()
        if request == "":
            continue
        result = check_scope(request, current_sow)
        print()
        if result["verdict"] == "scope_creep":
            top = result["matched_excluded"][0]
            print(f"[!] POTENTIAL SCOPE CREEP ({top['confidence']}% confident)")
            for match in result["matched_excluded"]:
                words = ", ".join(match["matched_words"])
                print(f"    - {match['item']} ({match['confidence']}%, matched: {words})")
            print("    Recommendation: create a change order (option 3).")
        elif result["verdict"] == "in_scope":
            top = result["matched_in_scope"][0]
            print(f"[OK] LIKELY IN SCOPE ({top['confidence']}% confident)")
            for match in result["matched_in_scope"]:
                words = ", ".join(match["matched_words"])
                print(f"    - {match['item']} ({match['confidence']}%, matched: {words})")
        else:
            print("[?] UNCLEAR - ask the client to clarify.")

    elif choice == "3":
        # --- Create a change order ---
        if current_sow is None:
            print("\nNo SOW loaded yet. Use option [1] first.")
            continue
        print("\n--- New Change Order ---")
        client_name = input("Client name: ").strip()
        scope_item = input("Describe the out-of-scope work: ").strip()
        hours = float(input("Estimated hours: ").strip())
        rate = float(input("Hourly rate: ").strip())
        rush_input = input("Rush job? (y/n): ").strip().lower()
        is_rush = rush_input == "y"

        order = create_change_order(
            client_name=client_name,
            project_name=current_sow["project_name"],
            scope_item=scope_item,
            hours=hours,
            rate=rate,
            is_rush=is_rush,
        )
        print(order)
        filename = save_change_order(order, client_name)
        print(f"Saved to: {filename}")

        pricing = calculate_pricing(hours, rate, is_rush)
        change_order_history.append({
            "client_name": client_name,
            "scope_item": scope_item,
            "total": pricing["total"],
            "filename": filename,
        })
        save_history(change_order_history)

    elif choice == "4":
        # --- View change order history ---
        if not change_order_history:
            print("\nNo change orders created yet.")
        else:
            print(f"\n--- Change Order History ({len(change_order_history)}) ---")
            for i, order in enumerate(change_order_history, start=1):
                print(f"{i}. {order['client_name']} - {order['scope_item']}")
                print(f"   Total: ${order['total']:.2f}  |  File: {order['filename']}")

    elif choice == "5":
        print("\nGoodbye!")
        break

    else:
        print("\nInvalid choice. Please enter 1-5.")
   