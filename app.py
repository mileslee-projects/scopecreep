# app.py — ScopeCreep Flask Web App
# Run with: python3 app.py
# Then open: http://localhost:5000

from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import os

from settings import SENDGRID_API_KEY, FROM_EMAIL, STRIPE_SECRET_KEY
from gmail_reader import fetch_recent_emails
from claude_checker import check_scope_with_claude
from main import (
    parse_sow, check_scope, calculate_pricing,
    create_change_order, save_change_order,
    create_stripe_payment_link, send_change_order_email,
    load_history, save_history, SAMPLE_SOW,
)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # needed to encrypt session cookies


# ===== ROUTES =====

@app.route("/")
def index():
    history = load_history()
    return render_template("index.html", history=history)


@app.route("/sow", methods=["GET", "POST"])
def sow():
    # GET  → show the form
    # POST → parse the submitted SOW, store in session, redirect to dashboard
    if request.method == "POST":
        sow_text = request.form.get("sow_text", "").strip()
        if sow_text == "":
            sow_text = SAMPLE_SOW
        parsed = parse_sow(sow_text)
        session["sow"] = parsed
        flash(f"SOW loaded: {parsed['project_name']} ({len(parsed['in_scope'])} in scope, {len(parsed['out_of_scope'])} excluded)")
        return redirect(url_for("index"))
    return render_template("sow.html")


@app.route("/check", methods=["GET", "POST"])
def check():
    # GET  → show the form (requires SOW in session)
    # POST → run scope check, show result on same page
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.")
        return redirect(url_for("sow"))

    result = None
    client_request = ""
    if request.method == "POST":
        client_request = request.form.get("client_request", "").strip()
        if client_request:
            result = check_scope_with_claude(client_request, sow_data)

    return render_template("check.html", sow=sow_data, result=result, client_request=client_request)


@app.route("/new-order", methods=["GET", "POST"])
def new_order():
    # GET  → show the form (requires SOW in session)
    # POST → create change order, generate payment link, send email, save to history
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.")
        return redirect(url_for("sow"))

    if request.method == "POST":
        client_name  = request.form.get("client_name", "").strip()
        client_email = request.form.get("client_email", "").strip()
        scope_item   = request.form.get("scope_item", "").strip()
        hours        = float(request.form.get("hours", 0))
        rate         = float(request.form.get("rate", 0))
        is_rush      = request.form.get("is_rush") == "on"

        pricing      = calculate_pricing(hours, rate, is_rush)
        order_text   = create_change_order(client_name, sow_data["project_name"], scope_item, hours, rate, is_rush)
        filename     = save_change_order(order_text, client_name)
        payment_link = create_stripe_payment_link(pricing["total"], scope_item)

        send_change_order_email(
            client_email=client_email,
            client_name=client_name,
            project_name=sow_data["project_name"],
            scope_item=scope_item,
            total=pricing["total"],
            payment_link=payment_link,
        )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        history = load_history()
        history.append({
            "id": len(history) + 1,
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
        save_history(history)

        flash(f"Change order sent to {client_email}.")
        return redirect(url_for("index"))

    scope_item = request.args.get("scope_item", "")
    return render_template("new_order.html", sow=sow_data, scope_item=scope_item)


@app.route("/gmail")
def gmail():
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.")
        return redirect(url_for("sow"))

    try:
        emails = fetch_recent_emails()
    except Exception as e:
        flash(f"Gmail error: {e}")
        return redirect(url_for("index"))

    # Run scope check on every email body
    flagged = []
    for email in emails:
        text = email["subject"] + " " + email["body"]
        result = check_scope_with_claude(text, sow_data)
        if result["verdict"] == "scope_creep":
            flagged.append({
                "email": email,
                "matches": result["matched_excluded"],
            })

    return render_template("gmail.html", flagged=flagged, total_scanned=len(emails))


if __name__ == "__main__":
    app.run(debug=True)
