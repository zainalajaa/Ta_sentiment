from flask import Flask, render_template, request, session, redirect
from model.preprocessing import preprocess_text
from model.naive_bayes import predict
from model.database import get_connection

app = Flask(__name__)
app.secret_key = "secret123"

# ======================
# 🔐 LOGIN
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():

    # 🔥 jika sudah login admin
    if session.get("role") == "admin":
        return redirect("/dashboard")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        # 🔥 hanya ambil admin
        query = """
        SELECT id, username, password
        FROM users
        WHERE username=%s
        """

        cursor.execute(query, (username,))
        admin = cursor.fetchone()

        cursor.close()
        conn.close()

        # 🔥 validasi login admin
        if admin and admin[2] == password:

            session["login"] = True
            session["role"] = "admin"
            session["admin_id"] = admin[0]
            session["admin_name"] = admin[1]

            return redirect("/dashboard")

        else:
            return render_template(
                "public/login.html",
                error="Username atau Password salah"
            )

    return render_template("public/login.html")
# ======================
# 🔓 LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ======================
# HALAMAN UTAMA
# ======================
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    text = ""
    scores = {}

    role = session.get("role")  # bisa None (free user)

    if request.method == "POST":
        text = request.form["text"]
        tokens = preprocess_text(text)

        result_data = predict(tokens)
        result = result_data["label"]
        scores = result_data["scores"]

        print("ROLE:", role)

        # 🔥 hanya admin yang simpan
        if role == "admin":
            print("SIMPAN KE DATABASE")

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO hasil_analisis (teks, hasil) VALUES (%s, %s)",
                (text, result)
            )

            conn.commit()
            cursor.close()
            conn.close()

    return render_template("public/index.html", result=result, text=text, scores=scores, role=role)

# ======================
# 📊 DASHBOARD ADMIN
# ======================
@app.route("/dashboard")
def dashboard():
    if "login" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT 
        SUM(CASE WHEN hasil='Positif' THEN 1 ELSE 0 END),
        SUM(CASE WHEN hasil='Negatif' THEN 1 ELSE 0 END)
    FROM hasil_analisis
    """
    cursor.execute(query)
    stats = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("admin/dashboard.html", stats=stats)


# ======================
# 📁 RIWAYAT (ADMIN ONLY)
# ======================
@app.route("/riwayat")
def riwayat():
    if "login" not in session or session.get("role") != "admin":
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id, teks, hasil, created_at FROM hasil_analisis ORDER BY id DESC"
    cursor.execute(query)
    data = cursor.fetchall()

    query2 = """
    SELECT 
        SUM(CASE WHEN hasil='Positif' THEN 1 ELSE 0 END),
        SUM(CASE WHEN hasil='Negatif' THEN 1 ELSE 0 END)
    FROM hasil_analisis
    """
    cursor.execute(query2)
    stats = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("admin/riwayat.html", data=data, stats=stats)


# ======================
# 🗑️ HAPUS DATA
# ======================
@app.route("/hapus/<int:id>")
def hapus(id):
    if "login" not in session or session.get("role") != "admin":
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM hasil_analisis WHERE id=%s", (id,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/riwayat")


# ======================
# 🚀 RUN APP
# ======================
if __name__ == "__main__":
    app.run(debug=True)