from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from db import get_db

app = Flask(__name__)
app.secret_key = "byt-till-nagot-hemligt-och-langt"   



@app.route("/")
def index():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT posts.content, posts.created, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.created DESC
    """)
    posts = cur.fetchall()
    cur.close()
    db.close()
    return render_template("index.html", posts=posts)



@app.route("/post", methods=["POST"])
def new_post():
    if "user_id" not in session:
        return redirect(url_for("login"))

    content = request.form["content"].strip()
    if content:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO posts (user_id, content) VALUES (%s, %s)",
            (session["user_id"], content)
        )
        db.commit()
        cur.close()
        db.close()
    return redirect(url_for("index"))     



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        name = request.form["name"].strip()
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash, name) VALUES (%s, %s, %s)",
                (username, generate_password_hash(password), name)
            )
            db.commit()
        except mysql.connector.errors.IntegrityError:
            flash("Användarnamnet är redan upptaget.")
            return render_template("register.html")
        finally:
            cur.close()
            db.close()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        flash("Fel användarnamn eller lösenord.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)