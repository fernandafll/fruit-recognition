from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import load_img, img_to_array
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import numpy as np

# ---------------------------
# FLASK CONFIG
# ---------------------------
app = Flask(__name__)
app.secret_key = "fruit_secret_key"

# ---------------------------
# DATABASE CONNECTION (NEON)
# ---------------------------
DB_URL = "postgresql://neondb_owner:npg_9oBNCDZ6yzMw@ep-lingering-wave-a4x48h6a-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_connection():
    return psycopg2.connect(DB_URL)

# ---------------------------
# LOAD MODEL
# ---------------------------
MODEL_PATH = "fruit_mnv2_final.keras"
model = load_model(MODEL_PATH)
IMG_SIZE = (224, 224)

class_labels = [
    'apple','avocado','banana','cherry','kiwi',
    'mango','orange','pineapple','strawberry','watermelon'
]

# ---------------------------
# LOGIN REQUIRED DECORATOR
# ---------------------------
def login_required(f):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ---------------------------
# ROUTES
# ---------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/catalog")
def catalog():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT fruit_id, name, description FROM fruits ORDER BY fruit_id;")
    fruits = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("catalog.html", fruits=fruits)

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id, password FROM users WHERE email=%s;", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            return "❌ Email not found"

        user_id, hashed_pw = user

        if not check_password_hash(hashed_pw, password):
            return "❌ Incorrect password"

        session["user_id"] = user_id
        return redirect("/")

    return render_template("login.html")

# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed = generate_password_hash(password)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s);
        """, (username, email, hashed))
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# PREDICT
@app.route("/predict", methods=["POST"])
@login_required
def predict():
    file = request.files["file"]

    os.makedirs("static/uploads", exist_ok=True)
    filepath = os.path.join("static/uploads", file.filename)
    file.save(filepath)

    img = load_img(filepath, target_size=IMG_SIZE)
    x = img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)

    pred = model.predict(x)
    fruit = class_labels[np.argmax(pred)]
    confidence = round(float(np.max(pred) * 100), 2)

    return render_template(
        "index.html",
        prediction=fruit,
        confidence=confidence,
        image=file.filename
    )

# ---------------------------
# RUN LOCAL
# ---------------------------
if __name__ == "__main__":
    app.run()
