# app.py — ScopeCreep Flask Web App
# Run with: python3 app.py
# Then open: http://127.0.0.1:5000

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
from sqlalchemy import inspect, text
import secrets
import os

from settings import SENDGRID_API_KEY, FROM_EMAIL, STRIPE_SECRET_KEY, SECRET_KEY
from models import db, User, ChangeOrder
from gmail_reader import fetch_recent_emails
from claude_checker import check_scope_with_claude, draft_ghostwriter_response, audit_sow_risk
from main import (
    parse_sow, calculate_pricing,
    create_change_order, save_change_order,
    create_stripe_payment_link, send_change_order_email,
    SAMPLE_SOW,
)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Use PostgreSQL on Railway, SQLite locally
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///scopecreep.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"  # redirect here if @login_required fails
login_manager.login_message = "Please log in to continue."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def ensure_schema():
    """Lightweight migration: add new ChangeOrder columns to an existing
    database if they're missing, and backfill portal tokens. Works on both
    SQLite (local) and PostgreSQL (Railway) for simple ADD COLUMN operations."""
    db.create_all()
    inspector = inspect(db.engine)
    existing = {c["name"] for c in inspector.get_columns("change_order")}
    new_columns = {
        "public_token":      "VARCHAR(48)",
        "client_message":    "TEXT",
        "client_message_at": "TIMESTAMP",
    }
    with db.engine.begin() as conn:
        for name, coltype in new_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE change_order ADD COLUMN {name} {coltype}"))
    # Backfill tokens for any orders created before the portal existed
    for order in ChangeOrder.query.filter(
        (ChangeOrder.public_token.is_(None)) | (ChangeOrder.public_token == "")
    ).all():
        order.public_token = secrets.token_urlsafe(24)
    db.session.commit()


# ===== AUTH ROUTES =====

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            hashed = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(email=email, password_hash=hashed)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email        = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        if not email or not new_password:
            flash("Email and new password are required.", "error")
        elif len(new_password) < 8:
            flash("Password must be at least 8 characters.", "error")
        else:
            user = User.query.filter_by(email=email).first()
            if user:
                user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
                db.session.commit()
            # Always show the same message so we don't reveal which emails exist
            flash("If an account exists for that email, the password has been reset. You can now log in.")
            return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ===== APP ROUTES =====

@app.route("/")
def index():
    if not current_user.is_authenticated:
        return render_template("landing.html")
    orders = ChangeOrder.query.filter_by(user_id=current_user.id)\
                              .order_by(ChangeOrder.created_at.desc()).all()
    history = [o.to_dict() for o in orders]

    stats = {
        "total_orders":    len(orders),
        "captured":        sum(o.total or 0 for o in orders if o.status == "paid"),
        "pending":         sum(o.total or 0 for o in orders if (o.status or "pending") == "pending"),
        "total_value":     sum(o.total or 0 for o in orders),
    }

    return render_template("index.html", history=history, stats=stats)


@app.route("/sow", methods=["GET", "POST"])
@login_required
def sow():
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
@login_required
def check():
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.", "error")
        return redirect(url_for("sow"))

    result = None
    client_request = ""
    if request.method == "POST":
        client_request = request.form.get("client_request", "").strip()
        if client_request:
            result = check_scope_with_claude(client_request, sow_data)

    return render_template("check.html", sow=sow_data, result=result, client_request=client_request)


@app.route("/new-order", methods=["GET", "POST"])
@login_required
def new_order():
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.", "error")
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

        # Unguessable public link the client uses to view + respond to the order
        public_token = secrets.token_urlsafe(24)
        portal_link  = url_for("client_order", token=public_token, _external=True)

        send_change_order_email(
            client_email=client_email,
            client_name=client_name,
            project_name=sow_data["project_name"],
            scope_item=scope_item,
            total=pricing["total"],
            payment_link=payment_link,
            portal_link=portal_link,
        )

        order = ChangeOrder(
            user_id      = current_user.id,
            client_name  = client_name,
            client_email = client_email,
            scope_item   = scope_item,
            total        = pricing["total"],
            filename     = filename,
            payment_link = payment_link,
            status       = "pending",
            created_at   = datetime.utcnow(),
            status_updated_at = datetime.utcnow(),
            public_token = public_token,
        )
        db.session.add(order)
        db.session.commit()

        flash(f"Change order sent to {client_email}.")
        return redirect(url_for("index"))

    scope_item = request.args.get("scope_item", "")
    return render_template("new_order.html", sow=sow_data, scope_item=scope_item)


@app.route("/audit", methods=["GET", "POST"])
@login_required
def audit():
    result = None
    sow_text = ""
    if request.method == "POST":
        sow_text = request.form.get("sow_text", "").strip()
        if sow_text:
            result = audit_sow_risk(sow_text)
    return render_template("audit.html", result=result, sow_text=sow_text)


@app.route("/ghostwrite", methods=["GET", "POST"])
@login_required
def ghostwrite():
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.", "error")
        return redirect(url_for("sow"))

    client_request = request.args.get("client_request", "") or request.form.get("client_request", "")
    tone = request.form.get("tone", "diplomatic")
    draft = None

    if client_request:
        draft = draft_ghostwriter_response(client_request, sow_data, tone)

    return render_template("ghostwriter.html", client_request=client_request, draft=draft, tone=tone, sow=sow_data)


@app.route("/mark-paid/<int:order_id>", methods=["POST"])
@login_required
def mark_paid(order_id):
    order = ChangeOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
    if order:
        order.status = "paid"
        order.status_updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Marked as paid: ${order.total:,.2f} captured.")
    return redirect(url_for("index"))


@app.route("/delete-order/<int:order_id>", methods=["POST"])
@login_required
def delete_order(order_id):
    order = ChangeOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
    if order:
        db.session.delete(order)
        db.session.commit()
        flash("Change order deleted.")
    return redirect(url_for("index"))


# ===== PUBLIC CLIENT PORTAL (no login) =====

@app.route("/order/<token>")
def client_order(token):
    order = ChangeOrder.query.filter_by(public_token=token).first_or_404()
    return render_template("client_order.html", order=order)


@app.route("/order/<token>/respond", methods=["POST"])
def client_respond(token):
    order = ChangeOrder.query.filter_by(public_token=token).first_or_404()
    message = request.form.get("message", "").strip()
    if message:
        order.client_message = message
        order.client_message_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("client_order", token=token))


@app.route("/gmail")
@login_required
def gmail():
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.", "error")
        return redirect(url_for("sow"))

    try:
        emails = fetch_recent_emails()
    except Exception as e:
        flash(f"Gmail error: {e}", "error")
        return redirect(url_for("index"))

    flagged = []   # confident scope creep
    review  = []   # borderline / unclear — surface so nothing slips through
    for email in emails:
        text = email["subject"] + " " + email["body"]
        result = check_scope_with_claude(text, sow_data)
        if result["verdict"] == "scope_creep":
            flagged.append({
                "email": email,
                "matches": result["matched_excluded"],
                "reason": result.get("reason", ""),
            })
        elif result["verdict"] == "unclear":
            review.append({
                "email": email,
                "reason": result.get("reason", ""),
            })

    return render_template("gmail.html", flagged=flagged, review=review, total_scanned=len(emails))


# Initialize + migrate the database on startup.
# Placed at module level so it runs under gunicorn (Railway) on import,
# not just when running app.py directly.
with app.app_context():
    ensure_schema()

if __name__ == "__main__":
    app.run(debug=True)
