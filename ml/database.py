import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # isi sesuai Laragon kamu
        database="ta_sentiment"
    )
    return conn


def init_password_reset_table():
    """Buat tabel password_resets bila belum ada."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) NOT NULL,
            token VARCHAR(255) NOT NULL,
            expires_at DATETIME NOT NULL,
            used TINYINT(1) NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_token (token)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)
    conn.commit()
    cursor.close()
    conn.close()


def init_tfidf_table():
    """Buat tabel tfidf bila belum ada."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tfidf (
            id INT AUTO_INCREMENT PRIMARY KEY,
            preprocessing_id INT NOT NULL,
            term VARCHAR(255) NOT NULL,
            tfidf_value DOUBLE NOT NULL,
            FOREIGN KEY (preprocessing_id) REFERENCES preprocessing(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
    """)
    conn.commit()
    cursor.close()
    conn.close()