# =========================================
# STANDARD LIBRARY
# =========================================

import os
import re
import string
from typing import Counter

# =========================================
# THIRD PARTY LIBRARY
# =========================================

import nltk
import pandas as pd
import numpy as np
from flask import url_for
import scipy.sparse as sp

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
    confusion_matrix,
    classification_report
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
from flask import session, request, jsonify
from datetime import datetime

from Sastrawi.Stemmer.StemmerFactory import (
    StemmerFactory
)

# =========================================
# LOCAL MODULE
# =========================================

from imblearn.over_sampling import SMOTE

from ml.database import get_connection, init_password_reset_table, init_tfidf_table
from ml.mailer import send_reset_email

import secrets
from datetime import timedelta

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

# Pastikan tabel token reset password tersedia
try:
    init_password_reset_table()
except Exception as e:
    print(f"[WARN] Gagal init tabel password_resets: {e}")

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
            SELECT id, username, email, password, role, photo
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
        session["photo"] = user[5]

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

        email = request.form["email"].strip()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        # email tidak ditemukan
        if not user:
            cursor.close()
            conn.close()
            return render_template(
                "public/forgot_password.html",
                error="Email tidak ditemukan"
            )

        # Buat token acak & waktu kedaluwarsa (1 jam)
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now() + timedelta(hours=1)

        # Hapus token lama email ini, lalu simpan token baru
        cursor.execute(
            "DELETE FROM password_resets WHERE email=%s",
            (email,)
        )
        cursor.execute(
            """
            INSERT INTO password_resets (email, token, expires_at)
            VALUES (%s, %s, %s)
            """,
            (email, token, expires_at)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Kirim email berisi link reset
        reset_link = url_for(
            "reset_password",
            token=token,
            _external=True
        )

        sent, err = send_reset_email(email, reset_link)

        if not sent:
            return render_template(
                "public/forgot_password.html",
                error=f"Gagal mengirim email: {err}"
            )

        return render_template(
            "public/forgot_password.html",
            success="Link reset password telah dikirim ke email Anda. "
                    "Silakan cek inbox (atau folder spam)."
        )

    return render_template("public/forgot_password.html")


# =====================================================
# RESET PASSWORD
# =====================================================
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    conn = get_connection()
    cursor = conn.cursor()

    # Validasi token
    cursor.execute(
        """
        SELECT id, email, expires_at, used
        FROM password_resets
        WHERE token=%s
        """,
        (token,)
    )
    row = cursor.fetchone()

    # Token tidak valid / sudah dipakai / kedaluwarsa
    if (
        not row
        or row[3] == 1
        or row[2] < datetime.now()
    ):
        cursor.close()
        conn.close()
        return render_template(
            "public/reset_password.html",
            invalid=True,
            error="Link reset tidak valid atau sudah kedaluwarsa. "
                  "Silakan ajukan ulang."
        )

    reset_id = row[0]
    email = row[1]

    if request.method == "POST":

        new_password = request.form["new_password"].strip()
        confirm_password = request.form["confirm_password"].strip()

        if len(new_password) < 6:
            cursor.close()
            conn.close()
            return render_template(
                "public/reset_password.html",
                token=token,
                error="Password minimal 6 karakter."
            )

        if new_password != confirm_password:
            cursor.close()
            conn.close()
            return render_template(
                "public/reset_password.html",
                token=token,
                error="Konfirmasi password tidak cocok."
            )

        hashed_password = generate_password_hash(new_password)

        # Update password user
        cursor.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (hashed_password, email)
        )

        # Tandai token sudah dipakai
        cursor.execute(
            "UPDATE password_resets SET used=1 WHERE id=%s",
            (reset_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash(
            "Password berhasil direset. Silakan login dengan password baru.",
            "success"
        )
        return redirect(url_for("login"))

    cursor.close()
    conn.close()

    return render_template(
        "public/reset_password.html",
        token=token
    )

# =====================================================
# HALAMAN PROFILE PUBLIK
# =====================================================
# =====================================================
# HELPER UPLOAD FOTO PROFIL
# =====================================================

def load_session_photo():
    """
    Pastikan session['photo'] terisi dari database
    (untuk sesi lama yang login sebelum fitur foto ada).
    """

    if session.get('photo') is not None:
        return

    if 'user_id' not in session:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT photo FROM users WHERE id=%s",
        (session['user_id'],)
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row:
        session['photo'] = row[0]


def save_profile_photo():
    """
    Simpan foto profil yang diupload (field form 'photo').
    Mengembalikan nama file jika ada upload, atau None bila tidak.
    """

    photo = request.files.get("photo")

    if not photo or photo.filename == "":
        return None

    filename = secure_filename(photo.filename)

    upload_folder = os.path.join(
        app.root_path,
        "static/uploads/users"
    )

    os.makedirs(upload_folder, exist_ok=True)

    photo.save(
        os.path.join(upload_folder, filename)
    )

    return filename


@app.route('/user-profile')
def public_profile():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    load_session_photo()

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

    # upload foto baru (opsional)
    photo_name = save_profile_photo()

    if photo_name:

        cursor.execute("""
            UPDATE users
            SET username=%s,
                email=%s,
                photo=%s
            WHERE id=%s
        """, (
            username,
            email,
            photo_name,
            session['user_id']
        ))

    else:

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

    if photo_name:
        session['photo'] = photo_name

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
@app.before_request
def ensure_session_photo():
    """Isi session['photo'] sekali per sesi agar avatar tampil di semua halaman."""
    if session.get('user_id') and 'photo' not in session:
        try:
            load_session_photo()
        except Exception:
            pass


def get_landing_stats():
    """Statistik dataset & performa model dari database (bukan dummy)."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT label, COUNT(*)
        FROM preprocessing
        GROUP BY label
    """)
    counts = dict(cursor.fetchall())

    cursor.close()
    conn.close()

    total_positif = counts.get('positif', 0)
    total_negatif = counts.get('negatif', 0)
    total_netral = counts.get('netral', 0)
    total_dataset = total_positif + total_negatif + total_netral

    try:
        bundle = get_tfidf_model()
        metrics = evaluate_tfidf_model(bundle)
    except Exception:
        metrics = {'accuracy': 0, 'precision': 0, 'recall': 0, 'f1': 0}

    return {
        'total_dataset': total_dataset,
        'total_positif': total_positif,
        'total_negatif': total_negatif,
        'total_netral': total_netral,
        'accuracy': metrics['accuracy'],
        'precision': metrics['precision'],
        'recall': metrics['recall'],
        'f1_score': metrics['f1'],
    }

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    text = ""
    scores = {}

    positif_score = 0
    negatif_score = 0
    netral_score = 0
    not_ready = False

    if request.method == "POST":
        text = request.form.get("text", "").strip()

        if text:
            # BERSIHKAN BYPASS HARDCODE - SEKARANG MURNI LEWAT ML HYBRID
            tokens = preprocess_text(text)
            result_data = predict(tokens)
            result = result_data.get("label", "Netral")
            scores = result_data.get("scores", {})

            positif_score = scores.get("positif", 0)
            negatif_score = scores.get("negatif", 0)
            netral_score = scores.get("netral", 0)

            # =======================================================
            # CEK VALIDASI LABEL
            # =======================================================
            if str(result).lower() not in ("positif", "negatif", "netral"):
                not_ready = True
                result = None
                return render_template(
                    "public/index.html",
                    result=None,
                    text=text,
                    scores={},
                    positif_score=0,
                    negatif_score=0,
                    netral_score=0,
                    not_ready=True,
                    role=session.get("role")
                )

            if str(result).lower() == "positif":
                hasil_db = "Positif"
            elif str(result).lower() == "negatif":
                hasil_db = "Negatif"
            else:
                hasil_db = "Netral"

            # =======================================================
            # SIMPAN HISTORI KE DATABASE
            # =======================================================
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO hasil_analisis (user_id, teks, hasil)
                    VALUES (%s, %s, %s)
                """, (
                    session.get("user_id"),
                    text,
                    hasil_db
                ))
                conn.commit()
            except Exception as e:
                print(f"Error simpan histori: {e}")
            finally:
                if cursor: cursor.close()
                if conn: conn.close()

    return render_template(
        "public/index.html",
        result=result,
        text=text,
        scores=scores,
        positif_score=positif_score,
        negatif_score=negatif_score,
        netral_score=netral_score,
        not_ready=not_ready,
        stats=get_landing_stats(),
        role=session.get("role")
    )

# =====================================================
# CEK SENTIMEN
# =====================================================
# =====================================================
# HALAMAN FREE USER
# =====================================================
@app.route("/sentiment", methods=["GET", "POST"])
def sentiment():

    result = None
    text = ""
    scores = {}
    detail = None
    posterior = None

    positif_score = 0
    netral_score = 0
    negatif_score = 0

    not_ready = False

    if request.method == "POST":
        text = request.form.get("review", "").strip()

        if text:
            # 1. GUNAKAN SINGLE SOURCE OF TRUTH (Satu fungsi kalkulasi untuk semua)
            # Fungsi ini dipanggil di awal agar guest user pun mendapatkan data skor yang akurat
            posterior_data = build_posterior_detail(text)

            # Jika fungsi posterior gagal/model belum siap
            if not posterior_data or "predicted" not in posterior_data:
                return render_template(
                    "public/sentiment.html",
                    result=None,
                    text=text,
                    scores={},
                    positif_score=0,
                    netral_score=0,
                    negatif_score=0,
                    detail=None,
                    posterior=None,
                    not_ready=True,
                    role=session.get("role")
                )

            # 2. Ambil label prediksi langsung dari hasil perhitungan posterior mutakhir
            result = posterior_data["predicted"]  # Menghasilkan teks: 'Positif', 'Netral', atau 'Negatif'
            
            # 3. Ekstrak nilai persentase murni dari dictionary posteriors
            positif_score = round(posterior_data["posteriors"]["positif"]["persen"], 2)
            netral_score = round(posterior_data["posteriors"]["netral"]["persen"], 2)
            negatif_score = round(posterior_data["posteriors"]["negatif"]["persen"], 2)

            # Format ulang objek scores agar sinkron dengan template visualisasi bar Anda
            scores = {
                "positif": positif_score,
                "netral": netral_score,
                "negatif": negatif_score
            }

            # Detail preprocessing untuk visualisasi tabel token
            detail = get_analysis_detail(text)

            # Rincian perhitungan posterior matematika tabel bawah (Hanya dikirim utuh jika user login)
            if session.get('login'):
                posterior = posterior_data

            # ==================================================
            # SIMPAN HISTORI KE DATABASE
            # ==================================================
            if result.lower() in ("positif", "netral", "negatif"):
                
                # Menyeragamkan format teks capital case sebelum disimpan ke db
                hasil_db = result.capitalize()

                conn = None
                cursor = None

                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO hasil_analisis (user_id, teks, hasil)
                        VALUES (%s, %s, %s)
                    """, (
                        session.get("user_id"),  # Bernilai None jika guest/tidak login
                        text,
                        hasil_db
                    ))

                    conn.commit()
                    print("Histori publik berhasil disimpan")

                except Exception as e:
                    print(f"Error simpan histori publik: {e}")

                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()

    return render_template(
        "public/sentiment.html",
        result=result,
        text=text,
        scores=scores,
        positif_score=positif_score,
        netral_score=netral_score,    # Menjamin bar progress Netral sinkron 
        negatif_score=negatif_score,
        detail=detail,
        posterior=posterior,          # Bernilai data lengkap jika login, bernilai None jika guest
        not_ready=not_ready,
        role=session.get("role")
    )


# =====================================================
# ABOUT SYSTEM
# =====================================================
@app.route('/about')
def about():

    conn = get_connection()
    cursor = conn.cursor()

    # =====================================================
    # DATASET (Mengambil jumlah data riil dari database)
    # =====================================================
    cursor.execute("""
        SELECT label, COUNT(*) 
        FROM preprocessing 
        WHERE label IN ('positif', 'negatif', 'netral')
        GROUP BY label
    """)
    results = dict(cursor.fetchall())
    
    total_positif = results.get('positif', 0)
    total_negatif = results.get('negatif', 0)
    total_netral = results.get('netral', 0)
    
    # Total dataset dihitung dari penjumlahan aktual data
    total_dataset = total_positif + total_negatif + total_netral

    # ======================
    # TOTAL ANALISIS USER
    # ======================
    cursor.execute("""
        SELECT COUNT(*)
        FROM hasil_analisis
    """)
    total_analisis = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    # Mengembalikan data ke template tentang tanpa membawa variabel evaluasi
    return render_template(
        'public/about.html',
        total_dataset=total_dataset,
        total_positif=total_positif,
        total_negatif=total_negatif,
        total_netral=total_netral,
        total_analisis=total_analisis
    )

# =========================================
# PREPROCESSING UNTUK PREDIKSI USER
# =========================================
# =========================================
# PREPROCESSING UNTUK PREDIKSI PUBLIK
# =========================================

def preprocess_text(text):
    # 1. Case Folding & Cleaning (Biarkan kode asli Anda)
    text = text.lower()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # 2. Tokenizing
    tokens = word_tokenize(text)

    # 3. Normalisasi (Biarkan kamus singkatan/kata gaul asli Anda)
    normalization_dict = {
        "gk": "tidak", "ga": "tidak", "nggak": "tidak", "tdk": "tidak",
        "apk": "aplikasi", "bgt": "banget", "bgtt": "banget",
        "sy": "saya", "gw": "saya", "dgn": "dengan", "udh": "sudah", 
        "blm": "belum", "jg": "juga", "trs": "terus", "jls": "jelas"
    }
    normalized_words = [normalization_dict.get(word, word) for word in tokens]

    # 4. Stopword Removal (Pastikan kata negasi TIDAK dihapus)
    negasi = ['tidak', 'bukan', 'jangan', 'belum', 'kurang']
    custom_stopwords = [word for word in stop_words if word not in negasi]
    filtered_words = [word for word in normalized_words if word not in custom_stopwords]

    # ==========================================================
    # KUNCI PERBAIKAN UTAMA: GABUNGKAN KATA NEGASI (UNDERSCORE)
    # ==========================================================
    handled_negation_words = []
    skip_next = False
    
    for i in range(len(filtered_words)):
        if skip_next:
            skip_next = False
            continue
            
        # Jika bertemu kata negasi dan masih ada kata sifat di depannya
        if filtered_words[i] in negasi and (i + 1) < len(filtered_words):
            # Satukan menjadi satu token tunggal, contoh: "kurang_bagus"
            combined_word = f"{filtered_words[i]}_{filtered_words[i+1]}"
            handled_negation_words.append(combined_word)
            skip_next = True # Lewati kata berikutnya karena sudah digabung
        else:
            handled_negation_words.append(filtered_words[i])

    # 5. Stemming (Jangan lakukan stemming pada kata yang digabung '_')
    stemmed_words = []
    for word in handled_negation_words:
        if '_' in word:
            stemmed_words.append(word) # Biarkan utuh: 'kurang_bagus'
        else:
            stemmed_words.append(stemmer.stem(word))

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

# =========================================================
# PREDICT SENTIMENT (FIXED HYBRID OVERRIDE)
# =========================================================
def predict(tokens):
    # 1. Gabungkan token menjadi string utuh (mengandung underscore, misal: "kurang_bagus")
    text_string = " ".join(tokens) if isinstance(tokens, list) else tokens

    # 2. Ambil data latih yang sudah sinkron dari database.
    #    Gunakan rasio split yang dipilih user (jangan menimpanya),
    #    agar konsisten dengan halaman split-data & evaluasi.
    X_train, X_test, y_train, y_test = get_split_data()

    # 3. Lakukan fitting TF-IDF berdasarkan data training asli
    vectorizer = get_vectorizer()
    X_train_tfidf = vectorizer.fit_transform(X_train)

    # Transformasi teks input user
    user_tfidf = vectorizer.transform([text_string])

    # 4. Bangun model Naive Bayes dengan setelan Uniform Prior (fit_prior=False)
    #    Fitur murni TF-IDF (lexicon tidak lagi digunakan sebagai fitur model,
    #    hanya dipakai pada pelabelan awal).
    model = MultinomialNB(fit_prior=False)
    model.fit(X_train_tfidf, y_train)

    # 5. Ambil nilai probabilitas asli dari masing-masing kelas (predict_proba)
    probabilities = model.predict_proba(user_tfidf)[0]

    # Petakan hasil probabilitas ke dalam dictionary skor (skala 0 - 100)
    scores = {}
    for cl, prob in zip(model.classes_, probabilities):
        scores[cl.lower()] = prob * 100

    # 6. Tentukan label akhir berdasarkan nilai probabilitas tertinggi
    predicted_label = max(scores, key=scores.get).capitalize()

    # Bulatkan skor untuk kebutuhan visualisasi di frontend web Anda
    for key in scores:
        scores[key] = round(scores[key], 2)

    return {
        "label": predicted_label,
        "scores": scores
    }


def get_analysis_detail(text):

    original = text

    # CASE FOLDING
    casefolding = text.lower()

    # CLEANING
    cleaning = re.sub(r'http\S+', '', casefolding)
    cleaning = re.sub(r'@\w+', '', cleaning)
    cleaning = re.sub(r'#\w+', '', cleaning)
    cleaning = re.sub(r'\d+', '', cleaning)

    cleaning = re.sub(
        r'[^a-zA-Z\s]',
        ' ',
        cleaning
    )

    cleaning = re.sub(
        r'\s+',
        ' ',
        cleaning
    ).strip()

    # TOKENIZING
    tokens = word_tokenize(cleaning)

    # NORMALISASI
    normalization_dict = {

        "gk":"tidak",
        "ga":"tidak",
        "nggak":"tidak",
        "tdk":"tidak",

        "apk":"aplikasi",

        "bgt":"banget",
        "bgtt":"banget",

        "sy":"saya",
        "gw":"saya",

        "dgn":"dengan",

        "udh":"sudah",
        "blm":"belum",

        "jg":"juga",

        "trs":"terus",

        "jls":"jelas"
    }

    normalized_words = []

    for word in tokens:

        normalized_words.append(
            normalization_dict.get(
                word,
                word
            )
        )

    # STOPWORD
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

    # TFIDF
    tfidf_words = []

    try:
        model, vectorizer = train_model()

        final_text = " ".join(
            stemmed_words
        )

        tfidf_vector = vectorizer.transform(
            [final_text]
        )

        feature_names = vectorizer.get_feature_names_out()

        weights = tfidf_vector.toarray()[0]

        for i, score in enumerate(weights):

            if score > 0:

                tfidf_words.append({

                    'word':
                    feature_names[i],

                    'score':
                    round(
                        float(score),
                        4
                    )
                })

        tfidf_words = sorted(
            tfidf_words,
            key=lambda x: x['score'],
            reverse=True
        )[:10]

    except DataNotReadyError:
        # Model belum dilatih: tampilkan detail preprocessing tanpa TF-IDF
        tfidf_words = []

    return {

        'original': original,

        'casefolding': casefolding,

        'cleaning': cleaning,

        'tokenizing': tokens,

        'normalisasi': normalized_words,

        'stopword': filtered_words,

        'stemming': stemmed_words,

        'tfidf': tfidf_words
    }



@app.route('/simpan_hasil_analisis', methods=['POST'])
@login_required
def simpan_hasil_analisis():

    try:

        teks = request.form.get('teks', '').strip()

        if not teks:
            return jsonify({
                'success': False,
                'message': 'Teks tidak boleh kosong'
            }), 400

        # ==========================
        # PREPROCESSING
        # ==========================
        tokens = preprocess_text(teks)

        # ==========================
        # PREDIKSI SENTIMEN
        # ==========================
        result_data = predict(tokens)

        hasil = result_data['label']

        # Samakan dengan ENUM database
        hasil = hasil.capitalize()

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
            session.get("user_id"),
            teks,
            hasil
        ))

        conn.commit()

        return jsonify({
            'success': True,
            'hasil': hasil
        })

    except Exception as e:

        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    finally:

        try:
            cursor.close()
            conn.close()
        except:
            pass



@app.route('/detail_analisis', methods=['POST'])
@login_required
def detail_analisis():

    try:

        text = request.form.get(
            'text',
            ''
        ).strip()

        if not text:

            return jsonify({
                'success': False,
                'message': 'Teks kosong'
            })

        detail = get_analysis_detail(text)

        return jsonify({
            'success': True,
            'data': detail
        })

    except Exception as e:

        return jsonify({
            'success': False,
            'message': str(e)
        })
    


@app.route('/dashboard')
@admin_required
def dashboard():
    # 1. Ambil data ringkasan database (Tetap dipertahankan untuk statistik counter)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label IN ('positif', 'netral', 'negatif')
    """)
    total_dataset = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM preprocessing WHERE label = 'positif'")
    total_positif = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM preprocessing WHERE label = 'netral'")
    total_netral = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM preprocessing WHERE label = 'negatif'")
    total_negatif = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hasil_analisis")
    total_prediksi = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    try:
        # 2. Ambil Bundle Model Hybrid yang Sudah Terkalibrasi SMOTE + Leksikon dari Cache
        bundle = get_tfidf_model()
        
        model = bundle['model']
        vectorizer = bundle['vectorizer']
        X_test_combined = bundle['X_test_combined']
        y_test = bundle['y_test']
        y_train = bundle['y_train']

        # 3. Hitung Jumlah Data Train dan Test yang Nyata
        train_count = len(y_train)
        test_count = len(y_test)

        # 4. Ambil Rasio Pembagian Data dari Session
        test_size = session.get('test_size', 0.2)
        split_ratio_map = {0.1: '90 : 10', 0.2: '80 : 20', 0.3: '70 : 30', 0.4: '60 : 40', 0.5: '50 : 50'}
        split_ratio = split_ratio_map.get(test_size, '80 : 20')

        # 5. Lakukan Prediksi Menggunakan Matriks Gabungan (TF-IDF + Leksikon)
        predictions = model.predict(X_test_combined)

        # 6. Hitung Metrik Evaluasi Model Hybrid Nyata
        accuracy = round(accuracy_score(y_test, predictions) * 100, 2)
        precision = round(precision_score(y_test, predictions, average='macro', zero_division=0) * 100, 2)
        recall = round(recall_score(y_test, predictions, average='macro', zero_division=0) * 100, 2)
        f1_score_value = round(f1_score(y_test, predictions, average='macro', zero_division=0) * 100, 2)

        # 7. HITUNG TOTAL BOBOT MATRIKS GABUNGAN (TF-IDF + LEKSIKON) SECARA AKURAT
        # Menggunakan X_train_combined dari cache agar tidak terkena error 'list' / 'ndarray'
        X_train_combined = bundle.get('X_train_combined')
        
        # Fallback jika X_train_combined tidak tersimpan di cache, kita buat ulang dimensinya secara aman
        if X_train_combined is None:
            (X_train_raw, _, _, _) = get_split_data()
            if isinstance(X_train_raw, list):
                X_train_tfidf = vectorizer.transform(X_train_raw)
            else:
                X_train_tfidf = X_train_raw
            X_train_combined = sp.csr_matrix(X_train_tfidf)

        y_train_array = np.array(y_train)
        pos_idx = np.where(y_train_array == 'positif')[0]
        net_idx = np.where(y_train_array == 'netral')[0]
        neg_idx = np.where(y_train_array == 'negatif')[0]

        # Menghitung sum dari objek sparse matrix secara aman
        total_weight_pos = round(float(np.sum(X_train_combined[pos_idx])), 2) if len(pos_idx) > 0 else 0.0
        total_weight_net = round(float(np.sum(X_train_combined[net_idx])), 2) if len(net_idx) > 0 else 0.0
        total_weight_neg = round(float(np.sum(X_train_combined[neg_idx])), 2) if len(neg_idx) > 0 else 0.0

    except Exception as e:
        print(f"--- PILOT DASHBOARD ERROR LOG: {e} ---")
        train_count = 0
        test_count = 0
        accuracy = 0
        precision = 0
        recall = 0
        f1_score_value = 0
        split_ratio = '-'
        total_weight_pos = 0
        total_weight_net = 0
        total_weight_neg = 0

    return render_template(
        'admin/main/dashboard.html',
        total_dataset=total_dataset,
        total_positif=total_positif,
        total_netral=total_netral,
        total_negatif=total_negatif,
        total_prediksi=total_prediksi,
        train_count=train_count,
        test_count=test_count,
        split_ratio=split_ratio,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score_value,
        total_weight_pos=total_weight_pos,
        total_weight_net=total_weight_net,
        total_weight_neg=total_weight_neg
    )



@app.route('/profile')
@login_required
def profile():
    load_session_photo()
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

    # upload foto baru (opsional)
    photo_name = save_profile_photo()

    if photo_name:

        cursor.execute("""
            UPDATE users
            SET username=%s,
                email=%s,
                photo=%s
            WHERE id=%s
        """, (
            username,
            email,
            photo_name,
            session['user_id']
        ))

    else:

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

    if photo_name:
        session['photo'] = photo_name

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

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", user[3])
        password = request.form.get("password")

        # role admin tidak boleh diubah (select-nya disabled di form,
        # sehingga tidak ikut terkirim)
        if user[3] == "admin":
            role = "admin"

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

        # Baca Excel. Sebagian file .xlsx hasil export punya spesifikasi
        # workbook yang rusak sehingga openpyxl gagal ("0 worksheets found").
        # Pakai engine calamine yang lebih toleran sebagai fallback.
        try:
            df = pd.read_excel(filepath)
        except ValueError:
            df = pd.read_excel(filepath, engine='calamine')

    # NORMALISASI KOLOM
    df.columns = df.columns.str.strip().str.lower()

    # KOLOM CONTENT WAJIB
    if 'content' not in df.columns:
        flash('Kolom content tidak ditemukan pada file Excel')
        return redirect('/preprocessing')

    # PELABELAN AWAL TIDAK LAGI DARI RATING/SCORE.
    # Label ditentukan dari kamus lexicon InSet pada tahap preprocessing
    # (lihat process_preprocessing), sehingga kolom label/score pada file
    # import diabaikan. Saat import, label dibiarkan kosong dulu.
    conn = get_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():

        content = str(row['content']).strip()

        if not content or content.lower() == 'nan':
            continue

        cursor.execute(
            """
            INSERT INTO preprocessing(content)
            VALUES (%s)
            """,
            (content,)
        )

    conn.commit()
    cursor.close()
    conn.close()

    clear_model_cache()

    flash(
        'Dataset berhasil diimport. Jalankan Preprocessing untuk '
        'melabeli data dengan kamus lexicon.',
        'success'
    )

    return redirect('/preprocessing')



def handle_negation(words):

    negations = [
        'tidak',
        'bukan',
        'jangan',
        'belum',
        'kurang'
    ]

    result = []

    i = 0

    while i < len(words):

        if (
            words[i] in negations
            and i + 1 < len(words)
        ):

            result.append(
                words[i] + '_' + words[i + 1]
            )

            i += 2

        else:

            result.append(words[i])

            i += 1

    return result





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

    custom_stopwords = {
        word for word in stop_words
        if word not in negasi
    }

    # CACHE STEMMING: kata yang sama cukup di-stem sekali
    stem_cache = {}

    def stem_word(word):
        if word not in stem_cache:
            stem_cache[word] = stemmer.stem(word)
        return stem_cache[word]

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
            "gbs": "tidak bisa",
            "apk": "aplikasi",

            "bgt": "banget",
            "bgtt": "banget",
            "bsa": "bisa",

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

            normalized_word = normalization_dict.get(
                word,
                word
            )

            normalized_words.append(
                normalized_word
            )

        # =================================
        # NEGATION HANDLING
        # =================================

        normalized_words = handle_negation(
            normalized_words
        )

        print(
            "SETELAH NEGASI :",
            normalized_words
        )

        normalisasi = ', '.join(
            normalized_words
        )

        # =================================
        # 5. STOPWORD REMOVAL
        # =================================

        filtered_words = []

        for word in normalized_words:

            if word not in custom_stopwords:

                filtered_words.append(
                    word
                )

        stopword = ', '.join(
            filtered_words
        )

        print(
            "SEBELUM STEM :",
            filtered_words
        )

        # =================================
        # 6. STEMMING
        # =================================

        stemmed_words = []

        for word in filtered_words:

            if '_' in word:

                stemmed_words.append(
                    word
                )

            else:

                stemmed_word = stem_word(
                    word
                )

                stemmed_words.append(
                    stemmed_word
                )

        stemming = ' '.join(
            stemmed_words
        )

        # =================================
        # 7. PELABELAN AWAL (LEXICON INSET)
        # =================================
        # Menggantikan pelabelan berbasis rating. Skor dihitung dari
        # teks hasil stemming (negasi seperti tidak_baik sudah tertangani).
        # Aturan selisih murni:
        #   pos_score > neg_score -> positif
        #   neg_score > pos_score -> negatif
        #   sama (termasuk data kosong tanpa kata lexicon) -> netral
        # Catatan: data kosong (stemming kosong) TIDAK dihapus, tetap
        # ditampilkan. Baris seperti ini otomatis tidak ikut pelatihan
        # karena get_split_data memfilter stemming yang kosong.

        pos_score, neg_score = get_lexicon_features(stemming)

        if pos_score > neg_score:
            label = 'positif'
        elif neg_score > pos_score:
            label = 'negatif'
        else:
            label = 'netral'

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
                stemming=%s,
                label=%s
            WHERE id=%s
        """, (
            casefolding,
            cleaning,
            tokenizing,
            normalisasi,
            stopword,
            stemming,
            label,
            id_data
        ))

    # commit sekali saja
    conn.commit()

    cursor.close()
    conn.close()

    clear_model_cache()

    flash('Preprocessing NLP berhasil dilakukan', 'success')

    return redirect('/preprocessing')



@app.route('/preprocessing/delete-all')
@admin_required
def delete_all():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("DELETE FROM tfidf")
        cursor.execute("DELETE FROM preprocessing")
        cursor.execute("ALTER TABLE preprocessing AUTO_INCREMENT = 1")
        cursor.execute("ALTER TABLE tfidf AUTO_INCREMENT = 1")

        conn.commit()

        clear_model_cache()

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

    # ==========================================
    # DEFAULT SESSION
    # ==========================================
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
    netral_count = 0
    negatif_count = 0

    for label, total in label_stats:
        if label == 'positif':
            positif_count = total
        elif label == 'netral':
            netral_count = total
        elif label == 'negatif':
            negatif_count = total

    total_dataset = positif_count + netral_count + negatif_count

    # ==========================================
    # DATA KOSONG SETELAH PREPROCESSING
    # ==========================================
    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label IN ('positif', 'netral', 'negatif')
        AND (stemming IS NULL OR stemming = '')
    """)
    empty_count = cursor.fetchone()[0]

    # ==========================================
    # DATA VALID POSITIF / NETRAL / NEGATIF
    # ==========================================
    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label = 'positif' AND stemming IS NOT NULL AND stemming != ''
    """)
    positif_used = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label = 'netral' AND stemming IS NOT NULL AND stemming != ''
    """)
    netral_used = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM preprocessing
        WHERE label = 'negatif' AND stemming IS NOT NULL AND stemming != ''
    """)
    negatif_used = cursor.fetchone()[0]

    total_used = positif_used + netral_used + negatif_used

    # ==========================================
    # DATA YANG DIGUNAKAN MODEL
    # ==========================================
    cursor.execute("""
        SELECT stemming, label
        FROM preprocessing
        WHERE stemming IS NOT NULL
        AND stemming != ''
        AND label IN ('positif', 'netral', 'negatif')
    """)
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    if not data:
        flash('Data preprocessing kosong', 'warning')
        return redirect('/preprocessing')

    texts = [row[0] for row in data]
    labels = [row[1] for row in data]

    # ==========================================
    # AMBIL RASIO DARI SESSION & PROSES POST
    # ==========================================
    test_size = session.get('test_size', 0.2)

    if request.method == 'POST':
        ratio = request.form.get('ratio')
        ratio_map = {
            '90-10': 0.1,
            '80-20': 0.2,
            '70-30': 0.3,
            '60-40': 0.4,
            '50-50': 0.5
        }
        test_size = ratio_map.get(ratio, 0.2)
        session['test_size'] = test_size

        # === PERBAIKAN DI SINI: Hancurkan cache agar model dilatih ulang otomatis ===
        global _MODEL_BUNDLE_CACHE
        _MODEL_BUNDLE_CACHE = None

        flash(f'Rasio pembagian dataset berhasil diperbarui menjadi {ratio}!', 'success')
        return redirect(request.url) # === PERBAIKAN DI SINI: Redirect bersih ===

    # ==========================================
    # VALIDASI DATASET & SPLIT DATASET (GET)
    # ==========================================
    total_data = len(texts)
    jumlah_kelas = len(set(labels))

    if total_data < 30:
        flash('Dataset terlalu sedikit. Minimal 30 data diperlukan untuk klasifikasi.', 'warning')
        return redirect('/preprocessing')

    test_count = round(total_data * test_size)
    if test_count < jumlah_kelas:
        flash(f'Jumlah data testing hanya {test_count}, sedangkan terdapat {jumlah_kelas} kelas sentimen.', 'warning')
        return redirect('/preprocessing')

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels,
            test_size=test_size,
            random_state=42,
            stratify=labels
        )
    except ValueError as e:
        flash(f'Gagal melakukan split data: {str(e)}', 'danger')
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
        total_dataset=total_dataset,
        positif_count=positif_count,
        netral_count=netral_count,
        negatif_count=negatif_count,
        empty_count=empty_count,
        total_used=total_used,
        positif_used=positif_used,
        netral_used=netral_used,
        negatif_used=negatif_used
    )

# =====================================================
# HASIL KLASIFIKASI
# =====================================================

# =========================================
# HELPER FUNCTION
# =========================================


class DataNotReadyError(Exception):
    """Data preprocessing belum siap untuk klasifikasi."""
    pass

def get_split_data():

    # Default 20% data testing
    test_size = session.get('test_size', 0.2)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT stemming, label
        FROM preprocessing
        WHERE stemming IS NOT NULL
        AND stemming != ''
        AND label IN ('positif', 'netral', 'negatif')
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    if not data:
        raise DataNotReadyError(
            'Data preprocessing tidak ditemukan.'
        )

    texts = []
    labels = []

    negasi = [
        'tidak',
        'bukan',
        'jangan',
        'belum',
        'kurang'
    ]

    for text, label in data:

        words = text.split()

        handled_words = []
        skip_next = False

        for i in range(len(words)):

            if skip_next:
                skip_next = False
                continue

            if (
                words[i] in negasi and
                (i + 1) < len(words)
            ):

                handled_words.append(
                    f"{words[i]}_{words[i+1]}"
                )

                skip_next = True

            else:

                handled_words.append(
                    words[i]
                )

        clean_text = " ".join(
            handled_words
        )

        texts.append(
            clean_text
        )

        labels.append(
            label
        )

    from collections import Counter

    label_counts = Counter(labels)

    print("\n=== DISTRIBUSI LABEL ===")
    print(label_counts)

    # Validasi minimal data tiap kelas
    if (
        label_counts['positif'] < 2 or
        label_counts['netral'] < 2 or
        label_counts['negatif'] < 2
    ):
        raise DataNotReadyError(
            'Jumlah data tiap kelas belum mencukupi.'
        )

    (
        X_train,
        X_test,
        y_train,
        y_test

    ) = train_test_split(

        texts,
        labels,

        test_size=test_size,
        random_state=42,
        stratify=labels

    )

    print("\n=== SPLIT DATASET ===")
    print("Train :", len(X_train))
    print("Test  :", len(X_test))

    return (

        X_train,
        X_test,

        y_train,
        y_test

    )


def get_split_data_with_ids():
    """Versi get_split_data yang mengembalikan ID preprocessing untuk sinkronisasi DB."""
    test_size = session.get('test_size', 0.2)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, stemming, label
        FROM preprocessing
        WHERE stemming IS NOT NULL
        AND stemming != ''
        AND label IN ('positif', 'negatif', 'netral')
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()

    ids = [row[0] for row in data]
    texts = [row[1] for row in data]
    labels = [row[2] for row in data]

    if len(texts) < 3 or len(set(labels)) < 3:
        raise DataNotReadyError('Data belum siap. Pastikan kelas Positif, Negatif, dan Netral tersedia.')

    (
        X_train_ids, X_test_ids,
        X_train, X_test,
        y_train, y_test
    ) = train_test_split(
        ids, texts, labels,
        test_size=test_size,
        random_state=42,
        stratify=labels
    )

    return (
        X_train_ids, X_test_ids,
        X_train, X_test,
        y_train, y_test
    )


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

    X_train_tfidf = vectorizer.fit_transform(X_train)

    model = MultinomialNB()

    model.fit(
        X_train_tfidf,
        y_train
    )


    return model, vectorizer


# =========================================================
# PREDICT SENTIMENT (SINKRONISASI TOTAL HYBRID & LEKSIKON)
# =========================================================
def predict(tokens):
    if not tokens:
        return {
            "label": "-",
            "scores": {}
        }

    # 1. Gabungkan tokens menjadi string tunggal
    text_string = " ".join(tokens) if isinstance(tokens, list) else tokens
    text_lower = text_string.lower()

    try:
        # 2. Ambil seluruh data latih. Gunakan rasio split pilihan user
        #    (jangan menimpanya) agar konsisten dengan halaman split-data.
        X_train, X_test, y_train, y_test = get_split_data()

        # 3. Bangun kembali vectorizer TF-IDF murni dari data latih
        vectorizer = get_vectorizer()
        X_train_tfidf = vectorizer.fit_transform(X_train)

        # Transformasi teks input user ke TF-IDF
        user_tfidf = vectorizer.transform([text_string])

    except Exception as e:
        print("Error get_split_data / TF-IDF:", str(e))
        return {
            "label": "Model belum siap",
            "scores": {}
        }

    # 4. Bangun model Naive Bayes dengan setelan Uniform Prior (fit_prior=False)
    #    Fitur murni TF-IDF. Kamus lexicon hanya dipakai pada pelabelan awal,
    #    bukan lagi sebagai fitur tambahan pada klasifikasi.
    model = MultinomialNB(fit_prior=False)
    model.fit(X_train_tfidf, y_train)

    # 5. Ekstrak Prediksi Akhir dan Probabilitas Dasar
    probabilities = model.predict_proba(user_tfidf)[0]

    # 6. Petakan skor berdasarkan urutan alfabet kelas model secara aman
    classes = model.classes_
    scores = {}
    for i, label in enumerate(classes):
        scores[label.lower()] = probabilities[i] * 100

    # 7. Ambil keputusan label akhir dari dictionary skor
    predicted_label = max(scores, key=scores.get).capitalize()

    # Pembulatan desimal akhir untuk keperluan render chart/bar di halaman web
    for key in scores:
        scores[key] = round(scores[key], 2)

    return {
        "label": predicted_label,
        "scores": scores
    }



@app.route('/classification/tfidf')
@admin_required
def tfidf():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Cek apakah ada data di tabel tfidf
    cursor.execute("SELECT COUNT(*) FROM tfidf")
    count = cursor.fetchone()[0]
    
    if count > 0:
        # Ambil seluruh term secara alfabetis (tanpa limit)
        cursor.execute("SELECT DISTINCT term FROM tfidf ORDER BY term")
        columns = [row[0] for row in cursor.fetchall()]
        
        
        cursor.execute("""
            SELECT DISTINCT
                t.preprocessing_id,
                p.label,
                p.stemming
            FROM tfidf t
            JOIN preprocessing p
                ON t.preprocessing_id = p.id
            ORDER BY t.preprocessing_id ASC
        """)
        docs = cursor.fetchall()
        
        doc_ids = [d[0] for d in docs]
        
        if doc_ids:
            format_ids = ','.join(['%s'] * len(doc_ids))
            format_terms = ','.join(['%s'] * len(columns))
            cursor.execute(f"""
                SELECT preprocessing_id, term, tfidf_value 
                FROM tfidf 
                WHERE preprocessing_id IN ({format_ids})
                AND term IN ({format_terms})
            """, doc_ids + columns)
            
            val_map = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
        else:
            val_map = {}

        tables = []
        for doc_id, label, text in docs:

            row_data = [

                doc_id,

                label.capitalize(),

                text[:30] + '...' if text else ''

            ]
            
            for term in columns:
                row_data.append(val_map.get((doc_id, term), 0.0))
            tables.append(row_data)
        
        # Hitung DF (Document Frequency) untuk tiap term dari database
        cursor.execute("""
            SELECT term, COUNT(preprocessing_id) 
            FROM tfidf 
            GROUP BY term
        """)
        df_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(DISTINCT preprocessing_id) FROM tfidf")
        total_docs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT term) FROM tfidf")
        total_terms = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return render_template(
            'admin/classification/tfidf.html',
            tables=tables,
            columns=['ID', 'Ulasan'] + columns,
            total_documents=total_docs,
            total_terms=total_terms,
            from_db=True,
            df_values=df_map
        )

    # Fallback jika database kosong
    cursor.close()
    conn.close()
    
    try:
        X_train_ids, X_test_ids, X_train, X_test, y_train, y_test = get_split_data_with_ids()
    except DataNotReadyError as e:
        flash(str(e), 'warning')
        return redirect('/preprocessing')

    vectorizer = get_vectorizer()
    X_train_tfidf = vectorizer.fit_transform(X_train)
    feature_names = vectorizer.get_feature_names_out()

    # Hitung DF dari matriks X_train_tfidf
    # DF = jumlah dokumen yang memiliki nilai > 0 untuk term tersebut
    import numpy as np
    df_counts = (X_train_tfidf > 0).sum(axis=0).A1
    df_map = {term: int(count) for term, count in zip(feature_names, df_counts)}
    
    # Urutkan berdasarkan ID agar konsisten dengan tampilan DB
    combined = sorted(zip(X_train_ids,y_train,X_train),key=lambda x: x[0])
    preview_data = combined[:20]
    
    preview_ids = [x[0] for x in preview_data]
    preview_labels = [x[1] for x in preview_data]
    preview_texts = [x[2] for x in preview_data]
    
    preview_tfidf = vectorizer.transform(preview_texts).toarray()
    # Tampilkan seluruh kolom feature
    preview_cols = feature_names.tolist()
    
    tables = []
    for i in range(len(preview_ids)):
        row_data = [preview_ids[i], preview_labels[i].capitalize(), preview_texts[i][:30] + '...' if preview_texts[i] else '']
        for j in range(len(preview_cols)):
            row_data.append(float(preview_tfidf[i][j]))
        tables.append(row_data)

    return render_template('admin/classification/tfidf.html',
        tables=tables,
        columns=[
            'ID',
            'Label',
            'Ulasan'
        ] + preview_cols,
        total_documents=len(X_train),
        total_terms=len(feature_names),
        from_db=False,
        df_values=df_map
    )


@app.route('/classification/tfidf/sync')
@admin_required
def tfidf_sync():
    """Menghitung TF-IDF dan menyimpannya ke database (tabel tfidf)."""
    try:
        X_train_ids, X_test_ids, X_train, X_test, y_train, y_test = get_split_data_with_ids()
    except DataNotReadyError as e:
        flash(str(e), 'warning')
        return redirect('/preprocessing')

    vectorizer = get_vectorizer()
    X_train_tfidf = vectorizer.fit_transform(X_train)
    feature_names = vectorizer.get_feature_names_out()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Hapus data lama
        cursor.execute("DELETE FROM tfidf")
        
        batch_data = []
        for i, doc_id in enumerate(X_train_ids):
            doc_vector = X_train_tfidf[i]
            for term_idx, weight in zip(doc_vector.indices, doc_vector.data):
                batch_data.append((
                    int(doc_id),
                    str(feature_names[term_idx]),
                    float(weight)
                ))
                
                # Insert per 5000 baris agar tidak overload
                if len(batch_data) >= 5000:
                    cursor.executemany("""
                        INSERT INTO tfidf (preprocessing_id, term, tfidf_value)
                        VALUES (%s, %s, %s)
                    """, batch_data)
                    batch_data = []

        # Sisa batch
        if batch_data:
            cursor.executemany("""
                INSERT INTO tfidf (preprocessing_id, term, tfidf_value)
                VALUES (%s, %s, %s)
            """, batch_data)
        
        conn.commit()
        flash('Data TF-IDF berhasil disinkronkan ke database.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Gagal sinkronisasi TF-IDF: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect('/classification/tfidf')


# =========================================
# NAIVE BAYES MANUAL (PRIOR, LIKELIHOOD, POSTERIOR)
# DISELARASKAN DENGAN MODEL TF-IDF + MultinomialNB
# agar hasil manual == hasil menu Evaluation.
#
# Menggunakan internal sklearn MultinomialNB yang sudah dilatih
# pada data latih (train split) dengan fitur TF-IDF:
#   Prior      : P(H)        = exp(model.class_log_prior_)
#   Likelihood : P(fitur|H)  = exp(model.feature_log_prob_)
#   Posterior  : P(H|X)      = model.predict_proba(tfidf(X))
# =========================================



# =========================================================================
# DEKLARASI VARIABEL GLOBAL (Wajib diletakkan di luar fungsi)
# =========================================================================
_MODEL_BUNDLE_CACHE = None

def clear_model_cache():
    global _MODEL_BUNDLE_CACHE
    _MODEL_BUNDLE_CACHE = None


def get_tfidf_model(force_retrain=False):
    """
    Mengambil model hybrid yang sudah dilatih dari cache memori.
    Solusi Inteligen: Membongkar tuple dari get_split_data() secara dinamis
    berdasarkan tipe objek asli untuk menghindari error urutan return (unboxing error).
    """
    global _MODEL_BUNDLE_CACHE
    
    if _MODEL_BUNDLE_CACHE is not None and not force_retrain:
        return _MODEL_BUNDLE_CACHE

    # 1. Ambil seluruh output dari get_split_data() sebagai satu tuple utuh
    returned_values = get_split_data()
    
    X_train_raw = None
    X_test_raw = None
    y_train = None
    y_test = None
    vectorizer = None

    # 2. Deteksi otomatis mana yang merupakan objek TfidfVectorizer asli
    from sklearn.feature_extraction.text import TfidfVectorizer as SklearnVectorizer
    
    # Cari vectorizer terlebih dahulu di dalam tuple
    for val in returned_values:
        if isinstance(val, SklearnVectorizer) or hasattr(val, 'fit_transform'):
            vectorizer = val
            break
            
    # Jika karena suatu alasan vectorizer tidak ditemukan/rusak, kita buat baru sebagai fallback
    if vectorizer is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer()

    # 3. Petakan sisa variabel berdasarkan urutan standar (asumsi 4 pertama adalah split data)
    # Kita ambil data train dan test teks/matriks secara aman
    X_train_raw = returned_values[0]
    X_test_raw = returned_values[1]
    y_train = returned_values[2]
    y_test = returned_values[3]

    # 4. Ambil informasi jumlah baris (sampel) secara akurat dari X_train_raw
    if hasattr(X_train_raw, 'shape'):
        num_samples_train = X_train_raw.shape[0]
    elif isinstance(X_train_raw, list):
        num_samples_train = len(X_train_raw)
    else:
        num_samples_train = len(list(X_train_raw))

    if hasattr(X_test_raw, 'shape'):
        num_samples_test = X_test_raw.shape[0]
    elif isinstance(X_test_raw, list):
        num_samples_test = len(X_test_raw)
    else:
        num_samples_test = len(list(X_test_raw))

    # 5. Lakukan Vektorisasi jika X_train_raw ternyata masih berupa list teks mentah
    if isinstance(X_train_raw, list) or (hasattr(X_train_raw, 'ndim') and X_train_raw.ndim == 1):
        X_train_tfidf = vectorizer.fit_transform(X_train_raw)
        X_test_tfidf = vectorizer.transform(X_test_raw)
    else:
        # Jika X_train_raw sudah berupa matriks angka (CSR Sparse), gunakan langsung
        X_train_tfidf = X_train_raw
        X_test_tfidf = X_test_raw

    # 6. Fitur murni TF-IDF (lexicon tidak lagi digabungkan sebagai fitur model;
    #    kamus lexicon hanya dipakai pada pelabelan awal).
    X_train_combined = sp.csr_matrix(X_train_tfidf)
    X_test_combined = sp.csr_matrix(X_test_tfidf)

    # ==========================================
    # PROSES OVERSAMPLING SMOTE & TRAINING MODEL
    # ==========================================
    from imblearn.over_sampling import SMOTE
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_combined, y_train)

    model = MultinomialNB()
    model.fit(X_train_resampled, y_train_resampled)

    print("\n========== FEATURE COUNT PER KELAS ==========")

    # feature_names masih berupa list
    if hasattr(vectorizer, "get_feature_names_out"):
        feature_names = vectorizer.get_feature_names_out().tolist()
    else:
        feature_names = []

    kata_dicari = ["aplikasi", "bantu", "proses", "kuliah"]

    for idx_kelas, kelas in enumerate(model.classes_):

        print(f"\nKELAS : {kelas}")

        for kata in kata_dicari:

            if kata in feature_names:

                idx = feature_names.index(kata)

                print(
                    f"{kata:10s} = {model.feature_count_[idx_kelas][idx]:.6f}"
                )

            else:

                print(f"{kata:10s} = TIDAK ADA")

    # ==========================================
    # TOTAL BOBOT FITUR SETIAP KELAS
    # ==========================================

    vocab_size = X_train_combined.shape[1]

    class_totals = {}

    for i, kelas in enumerate(model.classes_):
        total = float(model.feature_count_[i].sum())

        class_totals[kelas] = {
            'sum_tc': total,
            'vocab': vocab_size,
            'denominator': total + vocab_size
        }

    print("\n========== TOTAL BOBOT FITUR PER KELAS ==========")

    vocab_size = X_train_combined.shape[1]

    print("Jumlah fitur (|V|):", vocab_size)

    for i, kelas in enumerate(model.classes_):
        total_bobot = model.feature_count_[i].sum()

        print(f"\nKelas : {kelas}")
        print(f"ΣTc                = {total_bobot:.4f}")
        print(f"ΣTc + |V|          = {total_bobot + vocab_size:.4f}")

    class_index = {label: idx for idx, label in enumerate(model.classes_)}

    classes, counts = np.unique(y_train_resampled, return_counts=True)
    total_counts = counts.sum()
    priors = {cls: counts[idx] / total_counts for idx, cls in enumerate(classes)}

    # Ambil daftar nama fitur kosakata ulasan publik Anda
    if hasattr(vectorizer, 'get_feature_names_out'):
        feature_names = vectorizer.get_feature_names_out().tolist()
    else:
        feature_names = [f"feature_{i}" for i in range(X_train_combined.shape[1])]

    _MODEL_BUNDLE_CACHE = {
        'model': model,
        'vectorizer': vectorizer,
        'classes': model.classes_,
        'feature_names': feature_names,
        'class_index': class_index,
        'class_totals': class_totals,
        'priors': priors,
        'X_train_combined': X_train_combined, # Untuk kebutuhan hitung rumus manual backend
        'X_test_combined': X_test_combined,
        'y_train': y_train,                    # Menyelesaikan KeyError: 'y_train'
        'y_test': y_test
    }

    print("=== MODEL HYBRID BERHASIL DI-PATCH DENGAN SMART AUTO-DETECTION ===")
    return _MODEL_BUNDLE_CACHE

def model_classes(model):
    return model.classes_


def evaluate_tfidf_model(bundle):
    model = bundle['model']
    y_test = bundle['y_test']
    
    # Gunakan data uji gabungan (TF-IDF + Leksikon) yang sudah disiapkan di bundle
    X_test_combined = bundle['X_test_combined']
    
    # Lakukan prediksi langsung menggunakan fitur lengkap
    predictions = model.predict(X_test_combined)

    labels = ['positif', 'netral', 'negatif']

    return {
        'accuracy': round(accuracy_score(y_test, predictions) * 100, 2),
        'precision': round(precision_score(y_test, predictions, average='macro', zero_division=0) * 100, 2),
        'recall': round(recall_score(y_test, predictions, average='macro', zero_division=0) * 100, 2),
        'f1': round(f1_score(y_test, predictions, average='macro', zero_division=0) * 100, 2),
        'total': len(y_test),
        'cm': confusion_matrix(y_test, predictions, labels=labels).tolist(),
        'labels': labels,
    }

# =====================================================
# PERBAIKAN FUNGSI RINCIAN POSTERIOR (SINKRON & DINAMIS 1/2 DIMENSI)
# =====================================================
def build_posterior_detail(text):
    if not text:
        return None

    try:
        bundle = get_tfidf_model()
    except DataNotReadyError:
        return None

    model = bundle['model']
    vectorizer = bundle['vectorizer']
    feature_names = bundle['feature_names']
    ci = bundle['class_index']

    lh_pos_all = np.exp(model.feature_log_prob_[ci['positif']])
    lh_net_all = np.exp(model.feature_log_prob_[ci['netral']])
    lh_neg_all = np.exp(model.feature_log_prob_[ci['negatif']])

    # 1. Jalankan preprocessing teks input tunggal
    tokens = preprocess_text(text)
    joined = " ".join(tokens)

    # 2. Ambil bobot TF-IDF awal dalam bentuk sparse
    vec_tfidf_raw = vectorizer.transform([joined])

    # === JUMLAH FITUR MODEL (MURNI TF-IDF) ===
    total_features_expected = model.feature_log_prob_.shape[1]
    total_tfidf_features = len(feature_names)

    # Buat array NumPy biasa berukuran TEPAT sama dengan yang diminta model
    dense_input = np.zeros((1, total_features_expected))

    # Masukkan bobot kata TF-IDF hasil transform ke dalam array dense
    for idx, weight in zip(vec_tfidf_raw.indices, vec_tfidf_raw.data):
        if idx < total_tfidf_features:
            dense_input[0, idx] = weight

    detail_rows = []

    # Masukkan bobot kata ke detail_rows
    for idx in range(total_tfidf_features):
        weight = dense_input[0, idx]
        if weight > 0 or (text and feature_names[idx] in tokens):
            detail_rows.append({
                'word': feature_names[idx],
                'weight': float(weight),
                'lh_pos': float(lh_pos_all[idx]),
                'lh_net': float(lh_net_all[idx]),
                'lh_neg': float(lh_neg_all[idx])
            })

    # 3. Ubah menjadi format CSR Sparse & Klasifikasikan
    vec_combined = sp.csr_matrix(dense_input)
    proba = model.predict_proba(vec_combined)[0]
    pred = model.predict(vec_combined)[0]
    jll = model._joint_log_likelihood(vec_combined)[0]

    detail_rows.sort(key=lambda r: r['weight'], reverse=True)

    return {
        'tokens': tokens,
        'priors': bundle['priors'],
        'detail_rows': detail_rows,
        'posteriors': {
            'positif': {
                'raw': float(jll[ci['positif']]),
                'persen': float(proba[ci['positif']] * 100)
            },
            'netral': {
                'raw': float(jll[ci['netral']]),
                'persen': float(proba[ci['netral']] * 100)
            },
            'negatif': {
                'raw': float(jll[ci['negatif']]),
                'persen': float(proba[ci['negatif']] * 100)
            }
        },
        'predicted': (pred.capitalize() if pred and pred != '-' else pred)
    }


@app.route('/classification/prior')
@admin_required
def prior():

    from collections import Counter

    try:

        bundle = get_tfidf_model()

    except DataNotReadyError as e:

        flash(str(e), 'warning')

        return redirect('/preprocessing')

    # =====================================
    # Hitung prior dari data training
    # =====================================

    counts = Counter(
        bundle['y_train']
    )

    total = len(
        bundle['y_train']
    )

    rows = []

    for kelas in (
        'positif',
        'netral',
        'negatif'
    ):

        rows.append({

            'kelas': kelas.capitalize(),

            'jumlah': counts.get(
                kelas,
                0
            ),

            'total': total,

            'prior': bundle['priors'].get(
                kelas,
                0
            )

        })

    return render_template(

        'admin/classification/prior.html',

        rows=rows,

        total_docs=total

    )


@app.route('/classification/likelihood')
@admin_required
def likelihood_view():

    try:
        bundle = get_tfidf_model()
        class_totals = bundle['class_totals']

    except DataNotReadyError as e:

        flash(str(e), 'warning')

        return redirect('/preprocessing')

    model = bundle['model']
    vectorizer = bundle['vectorizer']
    feature_names = bundle['feature_names']
    ci = bundle['class_index']

    # =====================================
    # P(Fitur|Kelas)
    # =====================================

    lh_pos_all = np.exp(
        model.feature_log_prob_[ci['positif']]
    )

    lh_net_all = np.exp(
        model.feature_log_prob_[ci['netral']]
    )

    lh_neg_all = np.exp(
        model.feature_log_prob_[ci['negatif']]
    )

    text = request.args.get(
        'text',
        ''
    ).strip()

    category = request.args.get(
        'category',
        'all'
    ).lower()

    rows = []

    if text:

        joined = " ".join(
            preprocess_text(text)
        )

        vec = vectorizer.transform(
            [joined]
        )

        for idx, weight in zip(
            vec.indices,
            vec.data
        ):

            values = {
                'Positif': float(lh_pos_all[idx]),
                'Netral': float(lh_net_all[idx]),
                'Negatif': float(lh_neg_all[idx])
            }

            dominan = max(
                values,
                key=values.get
            )

            row = {
                'word': feature_names[idx],
                'weight': float(weight),

                'lh_pos': values['Positif'],
                'lh_net': values['Netral'],
                'lh_neg': values['Negatif'],

                'dominan': dominan
            }

            if (
                category == 'all'
                or dominan.lower() == category
            ):
                rows.append(row)

        rows.sort(
            key=lambda r: r['weight'],
            reverse=True
        )

    else:

        for idx in range(
            len(feature_names)
        ):

            values = {
                'Positif': float(lh_pos_all[idx]),
                'Netral': float(lh_net_all[idx]),
                'Negatif': float(lh_neg_all[idx])
            }

            dominan = max(
                values,
                key=values.get
            )

            row = {
                'word': feature_names[idx],
                'weight': None,

                'lh_pos': values['Positif'],
                'lh_net': values['Netral'],
                'lh_neg': values['Negatif'],

                'dominan': dominan
            }

            if (
                category == 'all'
                or dominan.lower() == category
            ):
                rows.append(row)

        if category == 'positif':

            rows.sort(
                key=lambda r: r['lh_pos'],
                reverse=True
            )

        elif category == 'netral':

            rows.sort(
                key=lambda r: r['lh_net'],
                reverse=True
            )

        elif category == 'negatif':

            rows.sort(
                key=lambda r: r['lh_neg'],
                reverse=True
            )

        else:

            rows.sort(
                key=lambda r: max(
                    r['lh_pos'],
                    r['lh_net'],
                    r['lh_neg']
                ),
                reverse=True
            )

    return render_template(
        'admin/classification/likelihood.html',
        class_totals=class_totals,

        rows=rows,

        text=text,

        category=category,

        n_features=len(feature_names)
    )


@app.route('/classification/posterior')
@admin_required
def posterior_view():
    try:
        bundle = get_tfidf_model()
        metrics = evaluate_tfidf_model(bundle)
    except DataNotReadyError as e:
        flash(str(e), 'warning')
        return redirect('/preprocessing')

    model = bundle['model']
    vectorizer = bundle['vectorizer']
    feature_names = bundle['feature_names']
    ci = bundle['class_index']
    priors = bundle['priors']

    # Ambil seluruh Likelihood dari model (Ukurannya pasti 1757 fitur)
    lh_pos_all = np.exp(model.feature_log_prob_[ci['positif']])
    lh_net_all = np.exp(model.feature_log_prob_[ci['netral']])
    lh_neg_all = np.exp(model.feature_log_prob_[ci['negatif']])

    text = request.args.get('text', '').strip()

    detail_rows = []
    posteriors = {}
    predicted = None
    tokens = []

    if text:
        tokens = preprocess_text(text)
        joined = " ".join(tokens)

        # 1. Transformasi teks menjadi fitur TF-IDF (murni)
        vec_tfidf = vectorizer.transform([joined])

        # 2. Prediksi probabilitas langsung dari fitur TF-IDF
        proba = model.predict_proba(vec_tfidf)[0]
        pred = model.predict(vec_tfidf)[0]
        jll = model._joint_log_likelihood(vec_tfidf)[0]

        predicted = pred

        # Loop untuk memetakan kata dasar bawaan TF-IDF ke tabel visual
        for idx, weight in zip(vec_tfidf.indices, vec_tfidf.data):
            detail_rows.append({
                'word': feature_names[idx],
                'weight': float(weight),
                'lh_pos': float(lh_pos_all[idx]),
                'lh_net': float(lh_net_all[idx]),
                'lh_neg': float(lh_neg_all[idx])
            })

        detail_rows.sort(key=lambda r: r['weight'], reverse=True)

        posteriors = {
            'positif': {
                'raw': float(jll[ci['positif']]),
                'persen': float(proba[ci['positif']] * 100)
            },
            'netral': {
                'raw': float(jll[ci['netral']]),
                'persen': float(proba[ci['netral']] * 100)
            },
            'negatif': {
                'raw': float(jll[ci['negatif']]),
                'persen': float(proba[ci['negatif']] * 100)
            }
        }

    return render_template(
        'admin/classification/posterior.html',
        text=text,
        tokens=tokens,
        priors=priors,
        detail_rows=detail_rows,
        posteriors=posteriors,
        predicted=(
            predicted.capitalize()
            if predicted and predicted != '-'
            else predicted
        ),
        metrics=metrics
    )


@app.route('/classification/prediction')
@admin_required
def prediction():

    try:

        (
            X_train,
            X_test,
            y_train,
            y_test
        ) = get_split_data()

    except DataNotReadyError as e:

        flash(str(e), 'warning')

        return redirect('/preprocessing')

    # =====================================
    # TF-IDF
    # =====================================

    vectorizer = get_vectorizer()

    X_train_tfidf = vectorizer.fit_transform(
        X_train
    )

    X_test_tfidf = vectorizer.transform(
        X_test
    )

    # =====================================
    # FITUR MURNI TF-IDF
    # =====================================
    # Fitur TF-IDF digunakan untuk merepresentasikan
    # bobot kata pada ulasan. Kamus Lexicon InSet tidak
    # lagi digabungkan sebagai fitur model; lexicon hanya
    # dipakai pada tahap pelabelan awal.

    X_train_combined = X_train_tfidf
    X_test_combined = X_test_tfidf

    # =====================================
    # SMOTE (Synthetic Minority Oversampling Technique)
    # =====================================
    # SMOTE digunakan untuk menyeimbangkan jumlah data
    # pada setiap kelas sentimen dengan membuat data
    # sintetis pada kelas minoritas. Proses ini dilakukan
    # hanya pada data training untuk mengurangi bias
    # model terhadap kelas mayoritas.

    smote = SMOTE(random_state=42)

    X_train_smote, y_train_smote = smote.fit_resample(
        X_train_combined,
        y_train
    )
    # =====================================
    # PELATIHAN MODEL MULTINOMIAL NAÏVE BAYES
    # =====================================
    # Model dilatih menggunakan data training yang
    # telah melalui proses TF-IDF dan penyeimbangan
    # kelas menggunakan SMOTE.

    model = MultinomialNB()

    model.fit(
        X_train_smote,
        y_train_smote
    )

    # =====================================
    # PREDIKSI DATA TESTING
    # =====================================
    # Model melakukan prediksi terhadap data testing
    # yang telah direpresentasikan menggunakan fitur TF-IDF.

    predictions = model.predict(
        X_test_combined
    )

    # =====================================
    # DETAIL HASIL PREDIKSI
    # =====================================

    results = []

    for text, actual, prediction in zip(
        X_test,
        y_test,
        predictions
    ):

        results.append({

            'text': text,

            'actual': actual,

            'prediction': prediction,

            'is_correct': (
                actual == prediction
            )

        })

    # =====================================
    # STATISTIK
    # =====================================

    total_positif = sum(
        1 for p in predictions
        if p == 'positif'
    )

    total_netral = sum(
        1 for p in predictions
        if p == 'netral'
    )

    total_negatif = sum(
        1 for p in predictions
        if p == 'negatif'
    )

    return render_template(

        'admin/classification/prediction.html',

        results=results,

        total_positif=total_positif,

        total_netral=total_netral,

        total_negatif=total_negatif,

        total_data=len(results)

    )

@app.route('/classification/evaluation')  # Sesuaikan dengan nama route asli Anda
@admin_required
def evaluation_view():
    try:
        # 1. Ambil bundle model hybrid terpadu dari cache memori
        bundle = get_tfidf_model()
    except Exception as e:
        flash(f"Gagal memuat model evaluasi: {e}", 'warning')
        return redirect('/dashboard')

    model = bundle['model']
    X_test_combined = bundle['X_test_combined']
    y_test = bundle['y_test']

    # 2. Lakukan prediksi menggunakan matriks gabungan (TF-IDF + Leksikon) yang sudah di-SMOTE
    y_pred = model.predict(X_test_combined)

    # 3. Hitung Confusion Matrix asli dari scikit-learn menggunakan urutan label yang pas
    from sklearn.metrics import confusion_matrix, classification_report
    classes_order = ['positif', 'netral', 'negatif']
    
    # Variabel 'cm' ini yang dicari oleh file HTML Anda
    cm = confusion_matrix(y_test, y_pred, labels=classes_order)

    # 4. Hitung Metrik Evaluasi Akhir
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)
    precision = round(precision_score(y_test, y_pred, average='macro', zero_division=0) * 100, 2)
    recall = round(recall_score(y_test, y_pred, average='macro', zero_division=0) * 100, 2)
    f1_score_value = round(f1_score(y_test, y_pred, average='macro', zero_division=0) * 100, 2)

    # Hitung classification report untuk tabel evaluasi bagian bawah jika dibutuhkan
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    # 5. Kirimkan variabel 'cm' murni agar langsung dibaca oleh template HTML bawaan Anda
    return render_template(
        'admin/classification/evaluation.html', # Sesuaikan nama file template Anda
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score_value,
        
        # Kirim variabel cm dengan nama 'cm' agar error Jinja2 hilang
        cm=cm, 
        
        report=report
    )

# =====================================================
# PERHITUNGAN MANUAL PUBLIK (SINKRON & HYBRID)
# =====================================================

@app.route('/perhitungan/tfidf')
@login_required
def public_tfidf():
    try:
        bundle = get_tfidf_model()
    except Exception:
        return render_template('public/classification/tfidf.html', not_ready=True)

    vectorizer = bundle['vectorizer']
    X_train_raw, _, _, _ = get_split_data()
    X_train_tfidf = vectorizer.transform(X_train_raw)
    feature_names = bundle['feature_names']

    df_counts = (X_train_tfidf > 0).sum(axis=0).A1
    df_map = {term: int(count) for term, count in zip(feature_names, df_counts)}

    tfidf_df = pd.DataFrame.sparse.from_spmatrix(
        X_train_tfidf,
        columns=feature_names
    )
    preview = tfidf_df.head(20)

    return render_template(
        'public/classification/tfidf.html',
        not_ready=False,
        tables=preview.values.tolist(),
        columns=preview.columns.tolist(),
        total_documents=len(X_train_raw),
        total_terms=len(feature_names),
        df_values=df_map
    )


@app.route('/perhitungan/prior')
@login_required
def public_prior():
    from collections import Counter

    try:
        bundle = get_tfidf_model()
    except Exception:
        return render_template(
            'public/classification/prior.html',
            not_ready=True
        )

    X_train_raw, _, y_train, _ = get_split_data()

    counts = Counter(y_train)
    total = len(y_train)

    rows = []

    for kelas in ['positif', 'netral', 'negatif']:
        rows.append({
            'kelas': kelas.capitalize(),
            'jumlah': counts.get(kelas, 0),
            'total': total,
            'prior': bundle['priors'].get(kelas, 0)
        })

    return render_template(
        'public/classification/prior.html',
        not_ready=False,
        rows=rows,
        total_docs=total,
    )


@app.route('/perhitungan/likelihood')
@login_required
def public_likelihood():
    try:
        bundle = get_tfidf_model()
    except Exception:
        return render_template('public/classification/likelihood.html', not_ready=True)

    model = bundle['model']
    vectorizer = bundle['vectorizer']
    feature_names = bundle['feature_names']
    ci = bundle['class_index']

    lh_pos_all = np.exp(model.feature_log_prob_[ci['positif']])
    lh_net_all = np.exp(model.feature_log_prob_[ci['netral']])
    lh_neg_all = np.exp(model.feature_log_prob_[ci['negatif']])

    text = request.args.get('text', '').strip()
    category = request.args.get('category', 'all').lower()

    rows = []
    num_tfidf_features = len(vectorizer.get_feature_names_out())

    if text:
        joined = " ".join(preprocess_text(text))
        vec = vectorizer.transform([joined])
        for idx, weight in zip(vec.indices, vec.data):
            if idx >= num_tfidf_features:
                continue
            
            probs = {'Positif': lh_pos_all[idx], 'Netral': lh_net_all[idx], 'Negatif': lh_neg_all[idx]}
            dominan = max(probs, key=probs.get)

            row = {
                'word': feature_names[idx],
                'weight': float(weight),
                'lh_pos': float(lh_pos_all[idx]),
                'lh_net': float(lh_net_all[idx]),
                'lh_neg': float(lh_neg_all[idx]),
                'dominan': dominan
            }
            if category == 'all' or row['dominan'].lower() == category:
                rows.append(row)

        rows.sort(key=lambda r: r['weight'], reverse=True)
    else:
        for idx in range(num_tfidf_features):
            probs = {'Positif': lh_pos_all[idx], 'Netral': lh_net_all[idx], 'Negatif': lh_neg_all[idx]}
            dominan = max(probs, key=probs.get)

            row = {
                'word': feature_names[idx],
                'weight': None,
                'lh_pos': float(lh_pos_all[idx]),
                'lh_net': float(lh_net_all[idx]),
                'lh_neg': float(lh_neg_all[idx]),
                'dominan': dominan
            }
            if category == 'all' or row['dominan'].lower() == category:
                rows.append(row)

        if category == 'positif':
            rows.sort(key=lambda r: r['lh_pos'], reverse=True)
        elif category == 'netral':
            rows.sort(key=lambda r: r['lh_net'], reverse=True)
        elif category == 'negatif':
            rows.sort(key=lambda r: r['lh_neg'], reverse=True)
        else:
            rows.sort(key=lambda r: r['lh_pos'], reverse=True)
        
        rows = rows[:100]

    return render_template(
        'public/classification/likelihood.html',
        not_ready=False,
        rows=rows,
        text=text,
        category=category,
        n_features=num_tfidf_features,
    )


@app.route('/perhitungan/prediction')
@login_required
def public_prediction():
    try:
        bundle = get_tfidf_model()
    except Exception:
        return render_template('public/classification/prediction.html', not_ready=True)

    model = bundle['model']
    X_test_combined = bundle['X_test_combined']
    y_test = bundle['y_test']
    
    _, X_test_raw, _, _ = get_split_data()
    predictions = model.predict(X_test_combined)

    results = []
    for i in range(len(y_test)):
        results.append({
            'text': X_test_raw[i],
            'actual': y_test[i],
            'prediction': predictions[i]
        })

    return render_template(
        'public/classification/prediction.html',
        not_ready=False,
        results=results
    )


@app.route('/perhitungan/evaluation')
@login_required
def public_evaluation():
    try:
        bundle = get_tfidf_model()
        
        X_test_combined = bundle['X_test_combined']
        y_test = bundle['y_test']
        model = bundle['model']
        
        y_pred = model.predict(X_test_combined)
        classes_order = ['positif', 'netral', 'negatif']
        
        accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)
        precision = round(precision_score(y_test, y_pred, average='macro', zero_division=0) * 100, 2)
        recall = round(recall_score(y_test, y_pred, average='macro', zero_division=0) * 100, 2)
        f1_value = round(f1_score(y_test, y_pred, average='macro', zero_division=0) * 100, 2)
        cm = confusion_matrix(y_test, y_pred, labels=classes_order)
        
    except Exception:
        return render_template('public/classification/evaluation.html', not_ready=True)

    return render_template(
        'public/classification/evaluation.html',
        not_ready=False,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_value,
        cm=cm
    )

## =========================================
# Kamus lexicon
# =========================================
# =======================================================
# 1. PERBAIKAN KAMUS (DIPISAH SUPAYA TIDAK SALING TERTUKAR)
# =======================================================
def load_lexicon():
    # Menggunakan kamus bersarang terpisah
    lexicon = {"positive": {}, "negative": {}}
    
    pos_path = 'lexicon/positive.tsv'
    neg_path = 'lexicon/negative.tsv'
    
    # Load Kamus Positif
    if os.path.exists(pos_path):
        with open(pos_path, 'r', encoding='utf-8') as f:
            next(f)  # skip header
            for line in f:
                row = line.strip().split('\t')
                if len(row) >= 2:
                    word = row[0].strip().lower()
                    # Ambil nilai absolut untuk mengukur murni kekuatan katanya
                    lexicon["positive"][word] = abs(int(row[1]))
                    
    # Load Kamus Negatif
    if os.path.exists(neg_path):
        with open(neg_path, 'r', encoding='utf-8') as f:
            next(f)  # skip header
            for line in f:
                row = line.strip().split('\t')
                if len(row) >= 2:
                    word = row[0].strip().lower()
                    # Ambil nilai absolutnya juga agar masuk ke laci bobot negatif dengan benar
                    lexicon["negative"][word] = abs(int(row[1]))
                    
    return lexicon

# Muat secara global
LEXICON = load_lexicon()
# =======================================================
# 2. EKSTRAKSI FITUR (PEMISAHAN SKOR SECARA TEGAS)
# =======================================================
def get_lexicon_features(text):
    pos_score = 0
    neg_score = 0

    if not text:
        return [0, 0]

    # Pecah kalimat menjadi kata tunggal
    for word in text.split():
        is_negated = False
        target_word = word.lower()

        # 1. Deteksi kata negasi terikat (Bigram/Underscore)
        if '_' in word:
            parts = word.split('_', 1)
            if len(parts) == 2:
                target_word = parts[1].lower()
                is_negated = True

        # 2. PROSES STEMMING ALAMI (Mengubah bodohnya/membodohi -> bodoh)
        # Sastrawi otomatis memotong imbuhan tanpa merusak struktur kode asli Anda
        target_word = stemmer.stem(target_word)

        # 3. Ambil bobot skor dari kamus bersarang LEXICON Anda
        # Cari di kamus positif
        if target_word in LEXICON.get("positive", {}):
            score = LEXICON["positive"][target_word]
            if is_negated:
                neg_score += abs(score)  # Contoh: tidak_baik -> cenderung negatif
            else:
                pos_score += abs(score)

        # Cari di kamus negatif (Kata "bodoh" akan tertangkap di sini!)
        elif target_word in LEXICON.get("negative", {}):
            score = LEXICON["negative"][target_word]
            if is_negated:
                pos_score += abs(score)  # Contoh: tidak_bodoh -> cenderung positif
            else:
                neg_score += abs(score)  #
    
    
    return [pos_score, neg_score]

# @app.route("/debug_lexicon")
# def debug_lexicon():

#     text = "bug nya banget bikin risih"

#     print("\n========== DEBUG LEKSIKON ==========")
#     print("Kalimat :", text)

#     pos_score = 0
#     neg_score = 0

#     for word in text.split():

#         target = stemmer.stem(word.lower())

#         print("\nToken :", word)
#         print("Stem  :", target)

#         if target in LEXICON["positive"]:

#             score = LEXICON["positive"][target]

#             print("Kamus : POSITIVE")
#             print("Bobot :", score)

#             pos_score += score

#         elif target in LEXICON["negative"]:

#             score = LEXICON["negative"][target]

#             print("Kamus : NEGATIVE")
#             print("Bobot :", score)

#             neg_score += score

#         else:

#             print("Kamus : TIDAK DITEMUKAN")
#             print("Bobot : 0")

#     print("\nHASIL")
#     print("Positif :", pos_score)
#     print("Negatif :", neg_score)

#     return str([pos_score, neg_score])

# @app.route("/debug_vocab")
# def debug_vocab():

#     bundle = get_tfidf_model()
#     vectorizer = bundle["vectorizer"]

#     print("="*50)
#     print("Jumlah vocabulary :", len(vectorizer.vocabulary_))
#     print("Apakah 'risih' ada?", "risih" in vectorizer.vocabulary_)

#     return "Selesai, cek terminal."

for rule in app.url_map.iter_rules():
    print(rule)

if __name__ == "__main__":
    # Port 5001 dipakai untuk menghindari bentrok dengan macOS AirPlay
    # Receiver yang menempati port 5000 (mengembalikan 403).
    app.run(debug=True, port=5001)