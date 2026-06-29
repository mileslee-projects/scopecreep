# main.py — ScopeCreep Phase 1
# Organized into functions: parse_sow, find_matches, check_scope,
# calculate_pricing, create_change_order

from datetime import date, datetime
import json
import os
import stripe
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from settings import SENDGRID_API_KEY, FROM_EMAIL, STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY


# ===== CONSTANTS =====

HISTORY_FILE = "change_order_history.json"

VALID_STATUSES = ["pending", "approved", "declined", "paid"]

BULLET_MARKERS = "-*•"

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

def load_history():
    """Load change order history from the JSON file.
    Returns an empty list if the file doesn't exist yet."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    """Save the change order history list to the JSON file."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

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
    print("  [5] Update change order status")
    print("  [6] Quit")
    print("=" * 40)

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

def create_stripe_payment_link(amount, description):
    """Create a Stripe payment link for the given dollar amount.
    Returns the URL string, or None if it fails."""
    try:
        product = stripe.Product.create(name=description)
        price = stripe.Price.create(
            product=product.id,
            unit_amount=int(amount * 100),  # Stripe uses cents
            currency="usd",
        )
        link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}]
        )
        return link.url
    except Exception as e:
        print(f"  [Warning] Could not create Stripe payment link: {e}")
        return None

def send_change_order_email(client_email, client_name, project_name, scope_item, total, payment_link):
    """Send a change order email to the client via SendGrid.
    Returns True if sent successfully, False otherwise."""
    subject = f"Change Order Request — {project_name}"

    pay_button = f'<a href="{payment_link}" style="background:#2563eb;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;">Approve & Pay ${total:,.2f}</a>' if payment_link else f"<p>Total due: ${total:,.2f}</p>"

    html = f"""
    <p>Hi {client_name},</p>
    <p>The following work falls outside the original scope of our agreement and requires a change order:</p>
    <blockquote style="border-left:4px solid #e5e7eb;padding-left:16px;color:#374151;">
        {scope_item}
    </blockquote>
    <p><strong>Total: ${total:,.2f}</strong></p>
    <p>Please approve and pay to proceed:</p>
    <p>{pay_button}</p>
    <p>Reply to this email if you'd like to discuss.</p>
    <p>— Miles</p>
    """

    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=client_email,
            subject=subject,
            html_content=html,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        return True
    except Exception as e:
        print(f"  [Warning] Could not send email: {e}")
        return False

def save_change_order(order_text, client_name):
    """Save a change order to a .txt file named after the client and date.
    Returns the filename."""
    today = date.today().strftime("%Y-%m-%d")
    safe_client = client_name.lower().replace(" ", "_")
    filename = f"change_order_{safe_client}_{today}.txt"
    with open(filename, "w") as f:
        f.write(order_text)
    return filename


# ===== MAIN PROGRAM =====

# State that persists across the menu loop
current_sow = None
change_order_history = load_history()

while True:
    print_menu()
    choice = input("Choose an option (1-6): ").strip()

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
        client_email = input("Client email: ").strip()
        scope_item = input("Describe the out-of-scope work: ").strip()
        hours = float(input("Estimated hours: ").strip())
        rate = float(input("Hourly rate: ").strip())
        rush_input = input("Rush job? (y/n): ").strip().lower()
        is_rush = rush_input == "y"

        pricing = calculate_pricing(hours, rate, is_rush)

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

        # Generate Stripe payment link
        print("\nGenerating payment link...", end=" ")
        payment_link = create_stripe_payment_link(pricing["total"], scope_item)
        if payment_link:
            print(f"Done.\n  {payment_link}")
        else:
            print("Skipped (no payment link).")

        # Send email
        print("Sending email to client...", end=" ")
        sent = send_change_order_email(
            client_email=client_email,
            client_name=client_name,
            project_name=current_sow["project_name"],
            scope_item=scope_item,
            total=pricing["total"],
            payment_link=payment_link,
        )
        if sent:
            print(f"Sent to {client_email}.")
        else:
            print("Failed — check your SendGrid key and verified sender.")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        change_order_history.append({
            "id": len(change_order_history) + 1,
            "client_name": client_name,
            "client_email": client_email,
            "scope_item": scope_item,
            "total": pricing["total"],
            "filename": filename,
            "payment_link": payment_link,
            "status": "pending",
            "created_at": now_str,
            "status_updated_at": now_str,
        })
        save_history(change_order_history)

    elif choice == "4":
        # --- View change order history ---
        if not change_order_history:
            print("\nNo change orders created yet.")
        else:
            print(f"\n--- Change Order History ({len(change_order_history)}) ---")
            for order in change_order_history:
                order_id = order.get("id", "?")
                status = order.get("status", "pending").upper()
                created = order.get("created_at", "unknown")
                status_updated = order.get("status_updated_at", created)
                client = order.get("client_name", "Unknown Client")
                scope_item = order.get("scope_item", "")
                total = order.get("total", 0.0)
                filename = order.get("filename", "")
                print(f"#{order_id} [{status}] {client} — {scope_item}")
                print(f"Total: ${total:.2f}  |  Created: {created}  |  File: {filename}")
                if status_updated != created or created == "unknown":
                    print(f"Status changed: {status} at {status_updated}")

    elif choice == "5":
        # --- Update change order status ---
        if not change_order_history:
            print("No change orders yet.")
            continue
        print("\n--- Update Change Order Status ---")
        for order in change_order_history:
            oid = order.get("id", "?")
            status = order.get("status", "pending").upper()
            client = order.get("client_name", "Unknown Client")
            print(f"{oid}: [{status}] {client}")

        try:
            id_str = input("Enter change order id to update: ").strip()
            update_id = int(id_str)
        except ValueError:
            print("Invalid id. Please enter a numeric id.")
            continue

        match = None
        for order in change_order_history:
            if order.get("id") == update_id:
                match = order
                break
        if match is None:
            print(f"No change order with id {update_id}")
            continue

        while True:
            new_status = input("Enter new status (pending/approved/declined/paid), or 'cancel' to abort: ").strip().lower()
            if new_status == "cancel":
                print("Cancelled.")
                break
            if new_status in VALID_STATUSES:
                break
            print("Invalid status. Valid: pending/approved/declined/paid.")

        if new_status == "cancel":
            continue

        match["status"] = new_status
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        match["status_updated_at"] = now_str
        save_history(change_order_history)
        print(f"Updated change order #{update_id} to {new_status.upper()} at {now_str}")

    elif choice == "6":
        print("\nGoodbye!")
        break

    else:
        print("\nInvalid choice. Please enter 1-6.")
