from flask import Flask, render_template, request, session, redirect, flash
from functools import wraps

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from ml.preprocessing import preprocess_text
from ml.naive_bayes import predict
from ml.database import get_connection

app = Flask(__name__)
app.secret_key = "secret123"

# =====================================================
# DECORATOR LOGIN
# =====================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("login"):
            return redirect("/login")

        return f(*args, **kwargs)

    return decorated_function

# =====================================================
# DECORATOR ADMIN
# =====================================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("login"):
            return redirect("/login")

        if session.get("role") != "admin":
            return redirect("/")

        return f(*args, **kwargs)

    return decorated_function


# =====================================================
# REGISTER
# =====================================================
@app.route("/register", methods=["GET", "POST"])
def register():

    if session.get("login"):
        return redirect("/")

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        # cek email
        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,)
        )

        check_email = cursor.fetchone()

        if check_email:

            cursor.close()
            conn.close()

            return render_template(
                "public/register.html",
                error="Email sudah terdaftar"
            )

        # hash password
        hashed_password = generate_password_hash(password)

        # insert user baru
        query = """
        INSERT INTO users
        (username, email, password, role)
        VALUES (%s, %s, %s, %s)
        """

        cursor.execute(query, (
            username,
            email,
            hashed_password,
            "user"
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/login")

    return render_template("public/register.html")


# =====================================================
# LOGIN
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():

    # jika sudah login
    if session.get("login"):

        if session.get("role") == "admin":
            return redirect("/dashboard")

        return redirect("/")

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT id, username, email, password, role
        FROM users
        WHERE email=%s
        """

        cursor.execute(query, (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        # email tidak ditemukan
        if not user:

            return render_template(
                "public/login.html",
                error="Email tidak terdaftar"
            )

        # password salah
        if not check_password_hash(user[3], password):

            return render_template(
                "public/login.html",
                error="Password salah"
            )

        # login berhasil
        session["login"] = True
        session["user_id"] = user[0]
        session["username"] = user[1]
        session["email"] = user[2]
        session["role"] = user[4]

        # redirect role
        if user[4] == "admin":
            return redirect("/dashboard")

        return redirect("/")

    return render_template("public/login.html")


# =====================================================
# LOGOUT
# =====================================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =====================================================
# FORGOT PASSWORD
# =====================================================
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        # email tidak ditemukan
        if not user:

            return render_template(
                "public/forgot_password.html",
                error="Email tidak ditemukan"
            )

        return render_template(
            "public/forgot_password.html",
            success="Fitur reset password akan dikirim ke email"
        )

    return render_template("public/forgot_password.html")


# =====================================================
# HALAMAN UTAMA ANALISIS
# =====================================================
@app.route("/", methods=["GET", "POST"])
def index():

    result = None
    text = ""
    scores = {}

    if request.method == "POST":

        text = request.form["text"]

        # preprocessing
        tokens = preprocess_text(text)

        # prediksi naive bayes
        result_data = predict(tokens)

        result = result_data["label"]
        scores = result_data["scores"]

        # simpan histori jika login
        if session.get("login"):

            conn = get_connection()
            cursor = conn.cursor()

            query = """
            INSERT INTO hasil_analisis
            (user_id, teks, hasil)
            VALUES (%s, %s, %s)
            """

            cursor.execute(query, (
                session.get("user_id"),
                text,
                result
            ))

            conn.commit()

            cursor.close()
            conn.close()

    return render_template(
        "public/index.html",
        result=result,
        text=text,
        scores=scores,
        role=session.get("role")
    )


# =====================================================
# DASHBOARD ADMIN
# =====================================================
@app.route("/dashboard")
@admin_required
def dashboard():

    conn = get_connection()
    cursor = conn.cursor()

    # statistik sentimen
    query = """
    SELECT
        SUM(CASE WHEN hasil='Positif' THEN 1 ELSE 0 END),
        SUM(CASE WHEN hasil='Negatif' THEN 1 ELSE 0 END)
    FROM hasil_analisis
    """

    cursor.execute(query)

    stats = cursor.fetchone()

    # total user
    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE role='user'"
    )

    total_user = cursor.fetchone()[0]

    # total analisis
    cursor.execute(
        "SELECT COUNT(*) FROM hasil_analisis"
    )

    total_analisis = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        total_user=total_user,
        total_analisis=total_analisis
    )


# =====================================================
# MANAJEMEN USER
# =====================================================
@app.route("/users")
@admin_required
def users():

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT id, username, email, role
    FROM users
    ORDER BY
        CASE
            WHEN role = 'admin' THEN 0
            ELSE 1
        END,
        id DESC
    """

    cursor.execute(query)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/users/users.html",
        data=data
    )


# =====================================================
# TAMBAH USER
# =====================================================
@app.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        conn = get_connection()
        cursor = conn.cursor()

        # cek email
        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,)
        )

        check_email = cursor.fetchone()

        if check_email:

            cursor.close()
            conn.close()

            return render_template(
                "admin/users/add_user.html",
                error="Email sudah digunakan"
            )

        hashed_password = generate_password_hash(password)

        query = """
        INSERT INTO users
        (username, email, password, role)
        VALUES (%s, %s, %s, %s)
        """

        cursor.execute(query, (
            username,
            email,
            hashed_password,
            role
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash('User berhasil ditambahkan', 'success')
        return redirect("/users")

    return render_template(
        "admin/users/add_user.html"
    )


# =====================================================
# EDIT USER
# =====================================================
@app.route("/users/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_user(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email, role FROM users WHERE id=%s",
        (id,)
    )

    user = cursor.fetchone()

    if not user:

        cursor.close()
        conn.close()

        return redirect("/users")

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        role = request.form["role"]

        query = """
        UPDATE users
        SET username=%s,
            email=%s,
            role=%s
        WHERE id=%s
        """

        cursor.execute(query, (
            username,
            email,
            role,
            id
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash('User berhasil diupdate', 'success')

        return redirect("/users")

    cursor.close()
    conn.close()

    return render_template(
        "admin/users/edit_user.html",
        user=user
    )


# =====================================================
# DETAIL USER
# =====================================================
@app.route("/users/detail/<int:id>")
@admin_required
def detail_user(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email, role FROM users WHERE id=%s",
        (id,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return redirect("/users")

    return render_template(
        "admin/users/detail_user.html",
        user=user
    )


# =====================================================
# HAPUS USER
# =====================================================
@app.route("/users/delete/<int:id>")
@admin_required
def delete_user(id):

    conn = get_connection()
    cursor = conn.cursor()

    # cek role
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (id,)
    )

    user = cursor.fetchone()

    # admin tidak bisa dihapus
    if user and user[0] == "admin":

        cursor.close()
        conn.close()

        return redirect("/users")

    cursor.execute(
        "DELETE FROM users WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash('User berhasil dihapus', 'success')
    return redirect("/users")


# =====================================================
# DATA PREPROCESSING
# =====================================================
@app.route("/preprocessing")
@login_required
def preprocessing():

    return render_template(
        "admin/preprocessing.html"
    )


# =====================================================
# HASIL KLASIFIKASI
# =====================================================
@app.route("/result")
@login_required
def result():

    conn = get_connection()
    cursor = conn.cursor()

    # admin melihat semua data
    if session.get("role") == "admin":

        query = """
        SELECT id, teks, hasil, created_at
        FROM hasil_analisis
        ORDER BY id DESC
        """

        cursor.execute(query)

    # user hanya melihat data sendiri
    else:

        query = """
        SELECT id, teks, hasil, created_at
        FROM hasil_analisis
        WHERE user_id=%s
        ORDER BY id DESC
        """

        cursor.execute(query, (
            session.get("user_id"),
        ))

    data = cursor.fetchall()

    # statistik
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

    return render_template(
        "admin/result.html",
        data=data,
        stats=stats
    )


# =====================================================
# HAPUS HASIL
# =====================================================
@app.route("/hapus/<int:id>")
@admin_required
def hapus(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM hasil_analisis WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/result")


# =====================================================
# RUN APP
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)