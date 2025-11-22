# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from sqlalchemy import select
from models_core import get_session, User

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("auth.signup"))
        db = get_session()
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            flash("Account already exists. Please log in.")
            return redirect(url_for("auth.login"))
        user = User(email=email, password_hash=generate_password_hash(password))
        db.add(user); db.commit()
        login_user(user)
        return redirect(url_for("home"))
    return render_template("signup.html")

@bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        db = get_session()
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid credentials.")
            return redirect(url_for("auth.login"))
        login_user(user)
        return redirect(url_for("home"))
    return render_template("login.html")

@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))
