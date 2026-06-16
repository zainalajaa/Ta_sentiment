
import sys
import os

# Menambahkan path project agar bisa import modul ml
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml.database import get_connection
from app import get_split_data_with_ids, get_vectorizer
import numpy as np

def verify_tfidf():
    print("--- Verifikasi Data TF-IDF ---")
    
    try:
        X_train_ids, X_test_ids, X_train, X_test, y_train, y_test = get_split_data_with_ids()
    except Exception as e:
        print(f"Error: {e}")
        return

    # 1. Hitung ulang TF-IDF secara live
    vectorizer = get_vectorizer()
    X_train_tfidf = vectorizer.fit_transform(X_train)
    feature_names = vectorizer.get_feature_names_out()
    
    # 2. Ambil data dari Database
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Mengambil data dari database...")
    cursor.execute("SELECT preprocessing_id, term, tfidf_value FROM tfidf")
    db_data = cursor.fetchall()
    
    if not db_data:
        print("Tabel tfidf kosong di database!")
        return

    # Map database data for easy lookup: (preprocessing_id, term) -> value
    db_map = {(row[0], row[1]): round(row[2], 6) for row in db_data}
    
    print(f"Total baris di DB: {len(db_data)}")
    
    # 3. Bandingkan
    mismatch_count = 0
    total_checked = 0
    
    print("Membandingkan hasil perhitungan dengan database...")
    # Kita cek sampel saja (misal 5 dokumen pertama) agar cepat
    sample_size = min(5, len(X_train_ids))
    
    for i in range(sample_size):
        doc_id = X_train_ids[i]
        doc_vector = X_train_tfidf[i]
        
        # Ambil term yang memiliki nilai > 0 di vector
        indices = doc_vector.indices
        data = doc_vector.data
        
        for idx, val in zip(indices, data):
            term = feature_names[idx]
            expected_val = round(float(val), 6)
            db_val = db_map.get((int(doc_id), term), None)
            
            total_checked += 1
            if db_val is None or abs(db_val - expected_val) > 1e-5:
                print(f"MISMATCH pada Doc ID {doc_id}, Term '{term}': DB={db_val}, Expected={expected_val}")
                mismatch_count += 1
                if mismatch_count > 10:
                    print("Terlalu banyak mismatch, berhenti mengecek...")
                    break
        if mismatch_count > 10: break

    if mismatch_count == 0:
        print(f"VERIFIKASI BERHASIL: {total_checked} sampel data di database cocok dengan perhitungan sistem.")
    else:
        print(f"VERIFIKASI GAGAL: Ditemukan {mismatch_count} ketidakcocokan.")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    verify_tfidf()
