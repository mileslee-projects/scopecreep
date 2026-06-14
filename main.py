# main.py — ScopeCreep Phase 1
# Organized into functions: parse_sow, find_matches, check_scope,
# calculate_pricing, create_change_order

from datetime import date
import json
import os

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

def parse_sow(sow_text):
    """Parse a scope-of-work string into structured data.
    Returns a dict with project_name, in_scope, and out_of_scope."""
    project_name = ""
    in_scope = []
    out_of_scope = []
    current_section = None

    for line in sow_text.split("\n"):
        line = line.strip()
        if line == "":
            continue

        line_lower = line.lower()

        if line_lower.startswith("project:"):
            project_name = line.split(":", 1)[1].strip()
            current_section = None
        elif line_lower.startswith("deliverables"):
            current_section = "in_scope"
        elif line_lower.startswith("excluded"):
            current_section = "out_of_scope"
        elif line.startswith("-"):
            item = line.lstrip("-").strip()
            if current_section == "in_scope":
                in_scope.append(item)
            elif current_section == "out_of_scope":
                out_of_scope.append(item)

    return {
        "project_name": project_name,
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
    }


def find_matches(items, request_lower):
    """Return all items that share a significant word with the request.
    This is the matching logic we used to write twice — now it's one function."""
    matches = [
        item
        for item in items
        if any(
            len(word) > 3 and word in request_lower
            for word in item.lower().split()
        )
    ]
    return matches

def check_scope(request, sow):
    """Check a client request against parsed scope.
    Returns a dict with verdict, matched_excluded, and matched_in_scope."""
    request_lower = request.lower()

    matched_excluded = find_matches(sow["out_of_scope"], request_lower)
    matched_in_scope = find_matches(sow["in_scope"], request_lower)

    if matched_excluded:
        verdict = "scope_creep"
    elif matched_in_scope:
        verdict = "in_scope"
    else:
        verdict = "unclear"

    return {
        "verdict": verdict,
        "matched_excluded": matched_excluded,
        "matched_in_scope": matched_in_scope,
    }


def calculate_pricing(hours, rate, is_rush=False):
    """Calculate the cost of a scope change.
    Returns a dict with subtotal, rush_fee, and total."""
    subtotal = hours * rate
    if is_rush:
        rush_fee = subtotal * 0.5
    else:
        rush_fee = 0
    total = subtotal + rush_fee
    return {
        "subtotal": subtotal,
        "rush_fee": rush_fee,
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
            print("[!] POTENTIAL SCOPE CREEP")
            for item in result["matched_excluded"]:
                print(f"    - matches excluded: {item}")
            print("    Recommendation: create a change order (option 3).")
        elif result["verdict"] == "in_scope":
            print("[OK] LIKELY IN SCOPE")
            for item in result["matched_in_scope"]:
                print(f"    - matches deliverable: {item}")
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
   