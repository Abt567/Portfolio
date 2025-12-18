# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import select
from models_core import get_session, User


bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    # If already logged in, no need to sign up again
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not email or not password or not confirm:
            flash("Email, password, and password confirmation are required.")
            return redirect(url_for("auth.signup"))

        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for("auth.signup"))

        # Basic password rules: min length, at least one digit and one uppercase letter.
        if len(password) < 8:
            flash("Password must be at least 8 characters long.")
            return redirect(url_for("auth.signup"))

        if not any(ch.isdigit() for ch in password):
            flash("Password must have at least one digit.")
            return redirect(url_for("auth.signup"))

        if not any(ch.isalpha() for ch in password):
            flash("Password must have at least one letter.")
            return redirect(url_for("auth.signup"))

        if not any(ch.isupper() for ch in password):
            flash("Password must have at least one uppercase letter.")
            return redirect(url_for("auth.signup"))

        db = get_session()
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            flash("Account already exists. Please log in.")
            return redirect(url_for("auth.login"))

        user = User(email=email, password_hash=generate_password_hash(password))
        db.add(user)
        db.commit()

        login_user(user)
        return redirect(url_for("home"))

    return render_template("signup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, no need to log in again
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        db = get_session()
        user = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid credentials.")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect(url_for("home"))

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    # Only logged-in users can hit this route
    logout_user()
    return redirect(url_for("home"))

