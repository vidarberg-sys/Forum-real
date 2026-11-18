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
        SELECT topics.id, topics.title, topics.created,
            users.username AS author, COUNT(posts.id) AS post_count,
            MAX(posts.created) AS latest_post
        FROM topics
        JOIN users ON topics.user_id = users.id
        LEFT JOIN posts ON posts.topic_id = topics.id
        GROUP BY topics.id, topics.title, topics.created, users.username
        ORDER BY latest_post DESC, topics.created DESC
    """)
    topics = cur.fetchall()
    cur.execute("""
        SELECT posts.content, posts.created, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.topic_id IS NULL
        ORDER BY posts.created DESC
    """)
    unthreaded_posts = cur.fetchall()
    cur.close()
    db.close()
    return render_template(
        "index.html", topics=topics, unthreaded_posts=unthreaded_posts
    )


@app.route("/topics/new", methods=["GET", "POST"])
def new_topic():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Fyll i både rubrik och inlägg.")
            return render_template("topic_form.html")

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                "INSERT INTO topics (user_id, title) VALUES (%s, %s)",
                (session["user_id"], title)
            )
            topic_id = cur.lastrowid
            cur.execute(
                "INSERT INTO posts (user_id, topic_id, content) VALUES (%s, %s, %s)",
                (session["user_id"], topic_id, content)
            )
            db.commit()
        except mysql.connector.Error:
            db.rollback()
            raise
        finally:
            cur.close()
            db.close()
        return redirect(url_for("topic", topic_id=topic_id))

    return render_template("topic_form.html")


@app.route("/topics/<int:topic_id>", methods=["GET", "POST"])
def topic(topic_id):
    if request.method == "POST" and "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT topics.id, topics.title, topics.created, users.username AS author
        FROM topics
        JOIN users ON topics.user_id = users.id
        WHERE topics.id = %s
    """, (topic_id,))
    current_topic = cur.fetchone()
    if current_topic is None:
        cur.close()
        db.close()
        return "Tråden finns inte.", 404

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if not content:
            flash("Skriv ett svar innan du skickar.")
        else:
            cur.execute(
                "INSERT INTO posts (user_id, topic_id, content) VALUES (%s, %s, %s)",
                (session["user_id"], topic_id, content)
            )
            db.commit()
            cur.close()
            db.close()
            return redirect(url_for("topic", topic_id=topic_id))

    cur.execute("""
        SELECT posts.content, posts.created, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        WHERE posts.topic_id = %s
        ORDER BY posts.created ASC
    """, (topic_id,))
    posts = cur.fetchall()
    cur.close()
    db.close()
    return render_template("topic.html", topic=current_topic, posts=posts)



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