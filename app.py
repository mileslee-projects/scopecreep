# app.py — ScopeCreep Flask Web App
# Run with: python3 app.py
# Then open: http://127.0.0.1:5000

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

from settings import SENDGRID_API_KEY, FROM_EMAIL, STRIPE_SECRET_KEY, SECRET_KEY
from models import db, User, ChangeOrder
from gmail_reader import fetch_recent_emails
from claude_checker import check_scope_with_claude, draft_ghostwriter_response
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
        flash("Invalid email or password.")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.")
        else:
            hashed = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(email=email, password_hash=hashed)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ===== APP ROUTES =====

@app.route("/")
@login_required
def index():
    orders = ChangeOrder.query.filter_by(user_id=current_user.id)\
                              .order_by(ChangeOrder.created_at.desc()).all()
    history = [o.to_dict() for o in orders]
    return render_template("index.html", history=history)


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
@login_required
def new_order():
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
        )
        db.session.add(order)
        db.session.commit()

        flash(f"Change order sent to {client_email}.")
        return redirect(url_for("index"))

    scope_item = request.args.get("scope_item", "")
    return render_template("new_order.html", sow=sow_data, scope_item=scope_item)


@app.route("/ghostwrite", methods=["GET", "POST"])
@login_required
def ghostwrite():
    sow_data = session.get("sow")
    if not sow_data:
        flash("Load a SOW first.")
        return redirect(url_for("sow"))

    client_request = request.args.get("client_request", "") or request.form.get("client_request", "")
    tone = request.form.get("tone", "diplomatic")
    draft = None

    if client_request:
        draft = draft_ghostwriter_response(client_request, sow_data, tone)

    return render_template("ghostwriter.html", client_request=client_request, draft=draft, tone=tone, sow=sow_data)


@app.route("/delete-order/<int:order_id>", methods=["POST"])
@login_required
def delete_order(order_id):
    order = ChangeOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
    if order:
        db.session.delete(order)
        db.session.commit()
        flash("Change order deleted.")
    return redirect(url_for("index"))


@app.route("/gmail")
@login_required
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
    with app.app_context():
        db.create_all()  # creates scopecreep.db if it doesn't exist
    app.run(debug=True)
