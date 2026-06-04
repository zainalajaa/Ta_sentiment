# =========================================
# STANDARD LIBRARY
# =========================================

import os
import re
import string

# =========================================
# THIRD PARTY LIBRARY
# =========================================

import nltk
import pandas as pd
import numpy as np
from flask import url_for

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    flash
)

from flask import session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)


from functools import wraps

from werkzeug.utils import secure_filename

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from sklearn.model_selection import train_test_split

# =========================================
# NLTK & NLP
# =========================================

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from Sastrawi.Stemmer.StemmerFactory import (
    StemmerFactory
)

# =========================================
# LOCAL MODULE
# =========================================

from ml.database import get_connection

# =========================================
# DOWNLOAD NLTK
# =========================================

try:
    nltk.data.find('tokenizers/punkt')

except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')

except LookupError:
    nltk.download('punkt_tab')

try:
    nltk.data.find('corpora/stopwords')

except LookupError:
    nltk.download('stopwords')

# =========================================
# STEMMER & STOPWORDS
# =========================================

factory = StemmerFactory()

stemmer = factory.create_stemmer()

stop_words = set(
    stopwords.words('indonesian')
)


from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)



# =========================================
# FLASK APP
# =========================================

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

    # Jika sudah login
    if session.get("login"):
        return redirect(url_for("index"))

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        # Cek email
        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
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

        # Hash password
        hashed_password = generate_password_hash(password)

        # Simpan user baru
        cursor.execute("""
            INSERT INTO users
            (username, email, password, role)
            VALUES (%s, %s, %s, %s)
        """, (
            username,
            email,
            hashed_password,
            "user"
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash(
            "Registrasi berhasil, silakan login.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("public/register.html")


# =====================================================
# LOGIN
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():

    # Jika sudah login
    if session.get("login"):

        if session.get("role") == "admin":
            return redirect(url_for("dashboard"))

        return redirect(url_for("index"))

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, email, password, role
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        # Email tidak ditemukan
        if not user:

            return render_template(
                "public/login.html",
                error="Email tidak terdaftar"
            )

        # Password salah
        if not check_password_hash(user[3], password):

            return render_template(
                "public/login.html",
                error="Password salah"
            )

        # Login berhasil
        session["login"] = True
        session["user_id"] = user[0]
        session["username"] = user[1]
        session["email"] = user[2]
        session["role"] = user[4]

        # Redirect berdasarkan role
        if user[4] == "admin":
            return redirect(url_for("dashboard"))

        return redirect(url_for("index"))

    return render_template("public/login.html")

# =====================================================
# LOGOUT
# =====================================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/sentiment")


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
# HALAMAN PROFILE PUBLIK
# =====================================================
@app.route('/user-profile')
def public_profile():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template(
        'public/profile.html'
    )


# =====================================================
# EDIT PROFILE PUBLIK
# =====================================================

@app.route('/user-profile/update', methods=['POST'])
@login_required
def update_public_profile():

    username = request.form['username'].strip()
    email = request.form['email'].strip()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM users
        WHERE email=%s
        AND id != %s
    """, (
        email,
        session['user_id']
    ))

    existing_user = cursor.fetchone()

    if existing_user:

        cursor.close()
        conn.close()

        flash(
            'Email sudah digunakan oleh pengguna lain.',
            'error'
        )

        return redirect(
            url_for('public_profile')
        )

    cursor.execute("""
        UPDATE users
        SET username=%s,
            email=%s
        WHERE id=%s
    """, (
        username,
        email,
        session['user_id']
    ))

    conn.commit()

    cursor.close()
    conn.close()

    session['username'] = username
    session['email'] = email

    flash(
        'Profil berhasil diperbarui.',
        'success'
    )

    return redirect(
        url_for('public_profile')
    )

# =====================================================
# EDIT PASSWORD PROFILE PUBLIK
# =====================================================

@app.route('/user-profile/change-password', methods=['POST'])
@login_required
def change_public_password():

    old_password = request.form['old_password'].strip()
    new_password = request.form['new_password'].strip()
    confirm_password = request.form['confirm_password'].strip()

    if new_password != confirm_password:

        flash(
            'Konfirmasi password tidak cocok.',
            'error'
        )

        return redirect(
            url_for('public_profile')
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT password
        FROM users
        WHERE id=%s
    """, (
        session['user_id'],
    ))

    user = cursor.fetchone()

    if not user:

        cursor.close()
        conn.close()

        flash(
            'User tidak ditemukan.',
            'error'
        )

        return redirect(
            url_for('public_profile')
        )

    if not check_password_hash(
        user[0],
        old_password
    ):

        cursor.close()
        conn.close()

        flash(
            'Password lama salah.',
            'error'
        )

        return redirect(
            url_for('public_profile')
        )

    hashed_password = generate_password_hash(
        new_password
    )

    cursor.execute("""
        UPDATE users
        SET password=%s
        WHERE id=%s
    """, (
        hashed_password,
        session['user_id']
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash(
        'Password berhasil diubah.',
        'success'
    )

    return redirect(
        url_for('public_profile')
    )


# =====================================================
# HALAMAN UTAMA ANALISIS
# =====================================================

def process_sentiment_analysis(text):
    """
    Proses preprocessing, prediksi sentimen,
    dan penyimpanan histori jika user login.
    """

    text = text.strip()

    if not text:
        return None, {}

    # preprocessing
    tokens = preprocess_text(text)

    # prediksi
    result_data = predict(tokens)

    result = result_data["label"]
    scores = result_data["scores"]

    # simpan histori jika login
    if session.get("login"):

        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
            INSERT INTO hasil_analisis
            (user_id, teks, hasil)
            VALUES (%s, %s, %s)
            """

            cursor.execute(
                query,
                (
                    session.get("user_id"),
                    text,
                    result
                )
            )

            conn.commit()

        except Exception as e:
            print(f"Error simpan histori: {e}")

        finally:
            cursor.close()
            conn.close()

    return result, scores


# =====================================================
# HALAMAN UTAMA USER LOGIN
# =====================================================
@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    result = None
    text = ""

    scores = {}

    positif_score = 0
    negatif_score = 0

    if request.method == "POST":

        text = request.form.get(
            "text",
            ""
        ).strip()

        if text:

            # =====================
            # PREPROCESSING
            # =====================

            tokens = preprocess_text(
                text
            )

            # =====================
            # PREDIKSI
            # =====================

            result_data = predict(
                tokens
            )

            result = result_data["label"]

            scores = result_data["scores"]

            positif_score = scores.get(
                "positif",
                0
            )

            negatif_score = scores.get(
                "negatif",
                0
            )

            # =====================
            # SIMPAN HISTORI
            # =====================

            try:

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO hasil_analisis
                    (
                        user_id,
                        teks,
                        hasil
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                """, (
                    session["user_id"],
                    text,
                    result
                ))

                conn.commit()

            except Exception as e:

                print(
                    f"Error simpan histori: {e}"
                )

            finally:

                cursor.close()
                conn.close()

    return render_template(
        "public/index.html",

        result=result,
        text=text,

        scores=scores,

        positif_score=positif_score,
        negatif_score=negatif_score,

        role=session.get("role")
    )


# =====================================================
# HALAMAN FREE USER
# =====================================================
@app.route("/sentiment", methods=["GET", "POST"])
def sentiment():

    result = None
    text = ""

    scores = {}

    positif_score = 0
    negatif_score = 0

    if request.method == "POST":

        text = request.form.get(
            "review",
            ""
        ).strip()

        if text:

            tokens = preprocess_text(
                text
            )

            result_data = predict(
                tokens
            )

            result = result_data["label"]

            scores = result_data["scores"]

            positif_score = scores.get(
                "positif",
                0
            )

            negatif_score = scores.get(
                "negatif",
                0
            )

    return render_template(
        "public/sentiment.html",

        result=result,
        text=text,

        scores=scores,

        positif_score=positif_score,
        negatif_score=negatif_score,

        role=session.get("role")
    )



# =====================================================
# ABOUT SYSTEM
# =====================================================

@app.route('/about')
def about():
    return render_template(
        'public/about.html'
    )



# =========================================
# PREPROCESSING UNTUK PREDIKSI USER
# =========================================
# =========================================
# PREPROCESSING UNTUK PREDIKSI PUBLIK
# =========================================

def preprocess_text(text):

    # CASE FOLDING
    text = text.lower()

    # CLEANING
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)

    text = re.sub(r'\d+', '', text)

    text = re.sub(
        r'[^a-zA-Z\s]',
        ' ',
        text
    )

    text = re.sub(
        r'\s+',
        ' ',
        text
    ).strip()

    # TOKENIZING
    tokens = word_tokenize(text)

    # NORMALISASI
    normalization_dict = {

        "gk": "tidak",
        "ga": "tidak",
        "nggak": "tidak",
        "tdk": "tidak",

        "apk": "aplikasi",

        "bgt": "banget",
        "bgtt": "banget",

        "sy": "saya",
        "gw": "saya",

        "dgn": "dengan",

        "udh": "sudah",
        "blm": "belum",

        "jg": "juga",

        "trs": "terus",

        "jls": "jelas"
    }

    normalized_words = []

    for word in tokens:

        normalized_words.append(
            normalization_dict.get(
                word,
                word
            )
        )

    # STOPWORD KHUSUS
    negasi = [
        'tidak',
        'bukan',
        'jangan',
        'belum',
        'kurang'
    ]

    custom_stopwords = [
        word
        for word in stop_words
        if word not in negasi
    ]

    filtered_words = []

    for word in normalized_words:

        if word not in custom_stopwords:

            filtered_words.append(word)

    # STEMMING
    stemmed_words = []

    for word in filtered_words:

        stemmed_words.append(
            stemmer.stem(word)
        )

    return stemmed_words


# =========================================
# TRAIN MODEL
# =========================================

def train_model():

    X_train, X_test, y_train, y_test = get_split_data()

    vectorizer = get_vectorizer()

    X_train_tfidf = vectorizer.fit_transform(
        X_train
    )

    model = MultinomialNB()

    model.fit(
        X_train_tfidf,
        y_train
    )

    return model, vectorizer


# =========================================
# PREDICT SENTIMENT
# =========================================

def predict(tokens):

    if not tokens:

        return {
            "label": "-",
            "scores": {}
        }

    model, vectorizer = train_model()

    text = " ".join(tokens)

    input_tfidf = vectorizer.transform(
        [text]
    )

    prediction = model.predict(
        input_tfidf
    )[0]

    probabilities = model.predict_proba(
        input_tfidf
    )[0]

    classes = model.classes_

    scores = {}

    for i, label in enumerate(classes):

        scores[str(label)] = float(
            round(
                probabilities[i] * 100,
                2
            )
        )

    return {
        "label": prediction,
        "scores": scores
    }



# =====================================================
# DASHBOARD ADMIN DAN PROFILE
# =====================================================
@app.route('/dashboard')
@admin_required
def dashboard():


    conn = get_connection()
    cursor = conn.cursor()

    # ======================
    # TOTAL DATASET DIGUNAKAN
    # ======================

    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label IN ('positif', 'negatif')
    """)

    total_dataset = cursor.fetchone()[0]

    # ======================
    # POSITIF
    # ======================

    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label = 'positif'
    """)

    total_positif = cursor.fetchone()[0]

    # ======================
    # NEGATIF
    # ======================

    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label = 'negatif'
    """)

    total_negatif = cursor.fetchone()[0]

    # ======================
    # NETRAL
    # ======================

    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label = 'netral'
    """)

    total_netral = cursor.fetchone()[0]

    # ======================
    # HASIL ANALISIS
    # ======================

    cursor.execute("""
        SELECT COUNT(*)
        FROM hasil_analisis
    """)

    total_prediksi = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    # ======================
    # SPLIT DATASET
    # ======================

    try:

        X_train, X_test, y_train, y_test = get_split_data()

        train_count = len(X_train)
        test_count = len(X_test)

        # ======================
        # RASIO SPLIT
        # ======================

        test_size = session.get('test_size', 0.2)

        split_ratio_map = {
            0.1: '90 : 10',
            0.2: '80 : 20',
            0.3: '70 : 30',
            0.4: '60 : 40'
        }

        split_ratio = split_ratio_map.get(
            test_size,
            '80 : 20'
        )

        # ======================
        # TF-IDF
        # ======================

        vectorizer = get_vectorizer()

        X_train_tfidf = vectorizer.fit_transform(X_train)
        X_test_tfidf = vectorizer.transform(X_test)

        # ======================
        # NAÏVE BAYES
        # ======================

        model = MultinomialNB()

        model.fit(
            X_train_tfidf,
            y_train
        )

        predictions = model.predict(X_test_tfidf)

        # ======================
        # EVALUATION
        # ======================

        accuracy = round(
            accuracy_score(
                y_test,
                predictions
            ) * 100,
            2
        )

        precision = round(
            precision_score(
                y_test,
                predictions,
                average='weighted',
                zero_division=0
            ) * 100,
            2
        )

        recall = round(
            recall_score(
                y_test,
                predictions,
                average='weighted',
                zero_division=0
            ) * 100,
            2
        )

        f1_score_value = round(
            f1_score(
                y_test,
                predictions,
                average='weighted',
                zero_division=0
            ) * 100,
            2
        )

    except Exception:

        train_count = 0
        test_count = 0

        accuracy = 0
        precision = 0
        recall = 0
        f1_score_value = 0

        split_ratio = '-'

    return render_template(
        'admin/main/dashboard.html',

        total_dataset=total_dataset,
        total_positif=total_positif,
        total_negatif=total_negatif,
        total_netral=total_netral,

        total_prediksi=total_prediksi,

        train_count=train_count,
        test_count=test_count,

        split_ratio=split_ratio,

        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score_value
    )




@app.route('/profile')
@login_required
def profile():
    return render_template(
        'admin/main/profile.html'
    )

# =====================================================
# EDIT PROFILE
# =====================================================

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():

    username = request.form['username'].strip()
    email = request.form['email'].strip()

    conn = get_connection()
    cursor = conn.cursor()

    # cek email dipakai user lain
    cursor.execute("""
        SELECT id
        FROM users
        WHERE email=%s
        AND id != %s
    """, (
        email,
        session['user_id']
    ))

    existing_user = cursor.fetchone()

    if existing_user:

        cursor.close()
        conn.close()

        flash('Email sudah digunakan oleh pengguna lain.', 'error')

        return redirect('/profile')

    # update data
    cursor.execute("""
        UPDATE users
        SET username=%s,
            email=%s
        WHERE id=%s
    """, (
        username,
        email,
        session['user_id']
    ))

    conn.commit()

    cursor.close()
    conn.close()

    # update session
    session['username'] = username
    session['email'] = email

    flash('Profil berhasil diperbarui.', 'success')

    return redirect('/profile')

# =====================================================
# EDIT PASSWORD PROFILE
# =====================================================

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():

    old_password = request.form['old_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:

        flash('Konfirmasi password tidak cocok.', 'error')

        return redirect('/profile')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT password
        FROM users
        WHERE id=%s
    """, (
        session['user_id'],
    ))

    user = cursor.fetchone()

    if not user:

        cursor.close()
        conn.close()

        flash('User tidak ditemukan.', 'error')

        return redirect('/profile')

    if not check_password_hash(user[0], old_password):

        cursor.close()
        conn.close()

        flash('Password lama salah.', 'error')

        return redirect('/profile')

    hashed_password = generate_password_hash(new_password)

    cursor.execute("""
        UPDATE users
        SET password=%s
        WHERE id=%s
    """, (
        hashed_password,
        session['user_id']
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash('Password berhasil diubah.', 'success')

    return redirect('/profile')

# =====================================================
# MANAJEMEN USER
# =====================================================
@app.route("/users")
@admin_required 
def users():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, role, photo
        FROM users
    """)

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

        photo = request.files.get("photo")

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

        # hash password
        hashed_password = generate_password_hash(password)

        # default photo
        photo_name = None

        # upload photo
        if photo and photo.filename != "":

            filename = secure_filename(photo.filename)

            upload_folder = os.path.join(
                app.root_path,
                "static/uploads/users"
            )

            os.makedirs(upload_folder, exist_ok=True)

            photo_path = os.path.join(
                upload_folder,
                filename
            )

            photo.save(photo_path)

            photo_name = filename

        query = """
        INSERT INTO users
        (username, email, password, role, photo)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            username,
            email,
            hashed_password,
            role,
            photo_name
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
        """
        SELECT id, username, email, role, photo
        FROM users
        WHERE id=%s
        """,
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
        password = request.form.get("password")

        photo = request.files.get("photo")

        photo_name = user[4]

        # upload photo baru
        if photo and photo.filename != "":

            filename = secure_filename(photo.filename)

            upload_folder = os.path.join(
                app.root_path,
                "static/uploads/users"
            )

            os.makedirs(upload_folder, exist_ok=True)

            photo_path = os.path.join(
                upload_folder,
                filename
            )

            photo.save(photo_path)

            photo_name = filename

        # update dengan password baru
        if password and password.strip() != "":

            hashed_password = generate_password_hash(password)

            query = """
            UPDATE users
            SET username=%s,
                email=%s,
                password=%s,
                role=%s,
                photo=%s
            WHERE id=%s
            """

            cursor.execute(query, (
                username,
                email,
                hashed_password,
                role,
                photo_name,
                id
            ))

        # update tanpa password
        else:

            query = """
            UPDATE users
            SET username=%s,
                email=%s,
                role=%s,
                photo=%s
            WHERE id=%s
            """

            cursor.execute(query, (
                username,
                email,
                role,
                photo_name,
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
        """
        SELECT id, username, email, role, photo
        FROM users
        WHERE id=%s
        """,
        (id,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return redirect("/users")

    # convert tuple ke list
    user = list(user)

    # pastikan photo string
    if user[4]:

        user[4] = user[4].strip()

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

@app.route('/preprocessing')
@admin_required
def preprocessing():

    page = request.args.get('page', 1, type=int)

    per_page = 10

    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor()

    # TOTAL DATA
    cursor.execute(
        "SELECT COUNT(*) FROM preprocessing"
    )

    total_data = cursor.fetchone()[0]

    total_pages = (total_data + per_page - 1) // per_page

    # GET DATA
    cursor.execute(
        """
        SELECT
            id,
            content,
            casefolding,
            cleaning,
            tokenizing,
            normalisasi,
            stopword,
            stemming,
            label
        FROM preprocessing
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (per_page, offset)
    )

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin/preprocessing/index.html',
        data=data,
        page=page,
        total_pages=total_pages,
        total_data=total_data
    )


@app.route('/preprocessing/import', methods=['POST'])
@admin_required
def import_data():

    file = request.files['file']

    if not file:

        flash('File wajib dipilih')
        return redirect('/preprocessing')

    filename = secure_filename(file.filename)

    upload_folder = os.path.join(
        app.root_path,
        'static/uploads/datasets'
    )

    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)

    file.save(filepath)

    # READ FILE
    if filename.endswith('.csv'):

        df = pd.read_csv(filepath)

    else:

        df = pd.read_excel(filepath)

    # NORMALISASI KOLOM
    df.columns = df.columns.str.strip().str.lower()

    conn = get_connection()
    cursor = conn.cursor()

    for index, row in df.iterrows():

        content = row['content']
        score = row['score']

        # Skip data kosong
        if pd.isna(content) or pd.isna(score):
            continue

        content = str(content).strip()

        if content == "":
            continue

        # KONVERSI SCORE → SENTIMEN
        if score >= 4:
            label = 'positif'

        elif score == 3:
            label = 'netral'

        else:
            label = 'negatif'

        cursor.execute(
            """
            INSERT INTO preprocessing(content, label)
            VALUES(%s, %s)
            """,
            (content, label)
        )

    conn.commit()

    cursor.close()
    conn.close()

    flash('Dataset berhasil diimport')

    return redirect('/preprocessing')


@app.route('/preprocessing/process')
@admin_required
def process_preprocessing():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, content
        FROM preprocessing
    """)

    data = cursor.fetchall()

    # =================================
    # STOPWORD KHUSUS
    # =================================

    negasi = ['tidak', 'bukan', 'jangan', 'belum', 'kurang']

    custom_stopwords = [
        word for word in stop_words
        if word not in negasi
    ]

    for item in data:

        id_data = item[0]
        content = item[1]

        # =================================
        # 1. CASE FOLDING
        # =================================

        casefolding = content.lower()

        # =================================
        # 2. CLEANING
        # =================================

        cleaning = re.sub(r'http\S+', '', casefolding)
        cleaning = re.sub(r'@\w+', '', cleaning)
        cleaning = re.sub(r'#\w+', '', cleaning)

        # hapus angka
        cleaning = re.sub(r'\d+', '', cleaning)

        # hapus karakter selain huruf dan spasi
        cleaning = re.sub(r'[^a-zA-Z\s]', ' ', cleaning)

        # hapus huruf berulang
        cleaning = re.sub(r'(.)\1{2,}', r'\1', cleaning)

        # hapus spasi berlebih
        cleaning = re.sub(r'\s+', ' ', cleaning).strip()

        # =================================
        # 3. TOKENIZING
        # =================================

        tokens = word_tokenize(cleaning)

        # hapus token kosong
        tokens = [word for word in tokens if word.strip()]

        tokenizing = ', '.join(tokens)

        # =================================
        # 4. NORMALISASI
        # =================================

        # =========================================
        # NORMALIZATION WORDS
        # =========================================

        normalization_dict = {

            "gk": "tidak",
            "ga": "tidak",
            "nggak": "tidak",
            "tdk": "tidak",

            "apk": "aplikasi",

            "bgt": "banget",
            "bgtt": "banget",

            "sy": "saya",
            "gw": "saya",

            "dgn": "dengan",

            "udh": "sudah",
            "blm": "belum",

            "jg": "juga",

            "trs": "terus",

            "jls":"jelas"

        }

        normalized_words = []

        for word in tokens:

            normalized_word = normalization_dict.get(word, word)

            normalized_words.append(normalized_word)

        normalisasi = ', '.join(normalized_words)

        # =================================
        # 5. STOPWORD REMOVAL
        # =================================

        filtered_words = []

        for word in normalized_words:

            if word not in custom_stopwords:

                filtered_words.append(word)

        stopword = ', '.join(filtered_words)

        # =================================
        # 6. STEMMING
        # =================================

        stemmed_words = []

        for word in filtered_words:

            stemmed_word = stemmer.stem(word)

            stemmed_words.append(stemmed_word)

        stemming = ' '.join(stemmed_words)

        # =================================
        # UPDATE DATABASE
        # =================================

        cursor.execute("""
            UPDATE preprocessing
            SET
                casefolding=%s,
                cleaning=%s,
                tokenizing=%s,
                normalisasi=%s,
                stopword=%s,
                stemming=%s
            WHERE id=%s
        """, (
            casefolding,
            cleaning,
            tokenizing,
            normalisasi,
            stopword,
            stemming,
            id_data
        ))

    # commit sekali saja
    conn.commit()

    cursor.close()
    conn.close()

    flash('Preprocessing NLP berhasil dilakukan')

    return redirect('/preprocessing')




@app.route('/preprocessing/delete-all')
@admin_required
def delete_all():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "TRUNCATE TABLE preprocessing"
        )

        conn.commit()

        flash(
            'Semua data preprocessing berhasil dihapus',
            'success'
        )

    except Exception as e:

        conn.rollback()

        flash(
            f'Gagal menghapus data: {str(e)}',
            'error'
        )

    finally:

        cursor.close()
        conn.close()

    return redirect('/preprocessing')


@app.route('/preprocessing/split-data', methods=['GET', 'POST'])
@admin_required
def split_data():

    # DEFAULT SESSION
    if 'test_size' not in session:
        session['test_size'] = 0.2

    conn = get_connection()
    cursor = conn.cursor()

    # ==========================================
    # STATISTIK DATASET AWAL
    # ==========================================

    cursor.execute("""
        SELECT label, COUNT(*)
        FROM preprocessing
        GROUP BY label
    """)

    label_stats = cursor.fetchall()

    positif_count = 0
    negatif_count = 0
    netral_count = 0

    for label, total in label_stats:

        if label == 'positif':
            positif_count = total

        elif label == 'negatif':
            negatif_count = total

        elif label == 'netral':
            netral_count = total

    total_dataset = (
        positif_count +
        negatif_count +
        netral_count
    )

    total_used = (
        positif_count +
        negatif_count
    )

    # ==========================================
    # DATA YANG DIGUNAKAN MODEL
    # ==========================================

    cursor.execute("""
        SELECT stemming, label
        FROM preprocessing
        WHERE stemming IS NOT NULL
        AND stemming != ''
        AND label IN ('positif', 'negatif')
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    if not data:

        flash('Data preprocessing kosong')
        return redirect('/preprocessing')

    texts = [row[0] for row in data]
    labels = [row[1] for row in data]

    # AMBIL DARI SESSION
    test_size = session.get('test_size', 0.2)

    # JIKA USER GANTI RATIO
    if request.method == 'POST':

        ratio = request.form.get('ratio')

        ratio_map = {
            '90-10': 0.1,
            '80-20': 0.2,
            '70-30': 0.3,
            '60-40': 0.4
        }

        test_size = ratio_map.get(ratio, 0.2)

        # SIMPAN KE SESSION
        session['test_size'] = test_size

    # ==========================================
    # VALIDASI DATASET
    # ==========================================

    total_data = len(texts)
    jumlah_kelas = len(set(labels))

    if total_data < 30:

        flash(
            'Dataset terlalu sedikit. '
            'Minimal 30 data diperlukan untuk melakukan split dataset dan klasifikasi.',
            'warning'
        )

        return redirect('/preprocessing')

    test_count = round(total_data * test_size)

    if test_count < jumlah_kelas:

        flash(
            f'Jumlah data testing hanya {test_count}, '
            f'sedangkan terdapat {jumlah_kelas} kelas sentimen. '
            f'Silakan tambahkan dataset atau gunakan rasio split yang lebih besar.',
            'warning'
        )

        return redirect('/preprocessing')

    # ==========================================
    # SPLIT DATA
    # ==========================================

    try:

        X_train, X_test, y_train, y_test = train_test_split(
            texts,
            labels,
            test_size=test_size,
            random_state=42,
            stratify=labels
        )

    except ValueError as e:

        flash(
            f'Gagal melakukan split data: {str(e)}',
            'danger'
        )

        return redirect('/preprocessing')

    train_data = list(zip(y_train, X_train))
    test_data = list(zip(y_test, X_test))

    training_ratio = int((1 - test_size) * 100)
    testing_ratio = int(test_size * 100)

    return render_template(
        'admin/preprocessing/split_dataset.html',
        train_data=train_data,
        test_data=test_data,
        training_ratio=training_ratio,
        testing_ratio=testing_ratio,

        positif_count=positif_count,
        negatif_count=negatif_count,
        netral_count=netral_count,

        total_dataset=total_dataset,
        total_used=total_used
    )
# =====================================================
# HASIL KLASIFIKASI
# =====================================================

# =========================================
# HELPER FUNCTION
# =========================================


def get_split_data():

    test_size = session.get('test_size', 0.2)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT stemming, label
        FROM preprocessing
        WHERE stemming IS NOT NULL
        AND stemming != ''
        AND label IN ('positif', 'negatif')
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    texts = [row[0] for row in data]
    labels = [row[1] for row in data]

    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=test_size,
        random_state=42,
        stratify=labels
    )

    return X_train, X_test, y_train, y_test


# =========================================
# TFIDF
# =========================================

# =========================================
# TF-IDF CONFIG
# =========================================

def get_vectorizer():

    return TfidfVectorizer(
        ngram_range=(1,2),
        min_df=2,
        max_df=0.9,
        max_features=5000,
        sublinear_tf=True
    )

# =========================================
# TRAIN MODEL NBC
# =========================================

def train_model():

    X_train, X_test, y_train, y_test = get_split_data()

    vectorizer = get_vectorizer()

    X_train_tfidf = vectorizer.fit_transform(
        X_train
    )

    model = MultinomialNB()

    model.fit(
        X_train_tfidf,
        y_train
    )

    return model, vectorizer


# =========================================
# PREDICT SENTIMENT
# =========================================

def predict(tokens):

    if not tokens:

        return {
            "label": "-",
            "scores": {}
        }

    model, vectorizer = train_model()

    text = " ".join(tokens)

    input_tfidf = vectorizer.transform(
        [text]
    )

    prediction = model.predict(
        input_tfidf
    )[0]

    probabilities = model.predict_proba(
        input_tfidf
    )[0]

    classes = model.classes_

    scores = {}

    for i, label in enumerate(classes):

        scores[label] = round(
            probabilities[i] * 100,
            2
        )

    return {
        "label": prediction,
        "scores": scores
    }



@app.route('/classification/tfidf')
@admin_required
def tfidf():

    X_train, X_test, y_train, y_test = get_split_data()

    vectorizer = get_vectorizer()

    # TRAINING
    X_train_tfidf = vectorizer.fit_transform(X_train)

    # TESTING
    X_test_tfidf = vectorizer.transform(X_test)

    feature_names = vectorizer.get_feature_names_out()

    # PREVIEW DATAFRAME
    tfidf_df = pd.DataFrame.sparse.from_spmatrix(
        X_train_tfidf,
        columns=feature_names
    )

    preview = tfidf_df.head(20)

    return render_template(
        'admin/classification/tfidf.html',
        tables=preview.values.tolist(),
        columns=preview.columns.tolist(),
        total_documents=len(X_train),
        total_terms=len(feature_names)
    )


@app.route('/classification/prediction')
@admin_required
def prediction():

    X_train, X_test, y_train, y_test = get_split_data()

    vectorizer = get_vectorizer()

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    model = MultinomialNB()

    model.fit(X_train_tfidf, y_train)

    predictions = model.predict(X_test_tfidf)

    results = []

    for i in range(len(X_test)):

        results.append({
            'text': X_test[i],
            'actual': y_test[i],
            'prediction': predictions[i]
        })

    return render_template(
        'admin/classification/prediction.html',
        results=results
    )


@app.route('/classification/evaluation')
@admin_required
def evaluation():

    # Dataset Split
    X_train, X_test, y_train, y_test = get_split_data()

    # Filter hanya Positif dan Negatif
    train_data = [
        (x, y)
        for x, y in zip(X_train, y_train)
        if y in ['positif', 'negatif']
    ]

    test_data = [
        (x, y)
        for x, y in zip(X_test, y_test)
        if y in ['positif', 'negatif']
    ]

    X_train = [x for x, y in train_data]
    y_train = [y for x, y in train_data]

    X_test = [x for x, y in test_data]
    y_test = [y for x, y in test_data]

    # TF-IDF
    vectorizer = get_vectorizer()

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # Training Model
    model = MultinomialNB()

    model.fit(
        X_train_tfidf,
        y_train
    )

    # Prediksi
    predictions = model.predict(X_test_tfidf)

    # Evaluation Metrics
    accuracy = round(
        accuracy_score(
            y_test,
            predictions
        ) * 100,
        2
    )

    precision = round(
        precision_score(
            y_test,
            predictions,
            average='weighted',
            zero_division=0
        ) * 100,
        2
    )

    recall = round(
        recall_score(
            y_test,
            predictions,
            average='weighted',
            zero_division=0
        ) * 100,
        2
    )

    f1_score_value = round(
        f1_score(
            y_test,
            predictions,
            average='weighted',
            zero_division=0
        ) * 100,
        2
    )

    # Confusion Matrix 2 Kelas
    labels = [
        'positif',
        'negatif'
    ]

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=labels
    )

    return render_template(
        'admin/classification/evaluation.html',
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score_value,
        cm=cm.tolist()
    )


if __name__ == "__main__":
    app.run(debug=True)