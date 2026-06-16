
import sys
import os
import pandas as pd
import numpy as np
from app import app, get_vectorizer, get_split_data

def get_terms_df(sentence):
    with app.app_context():
        with app.test_request_context():
            print(f"Mencari nilai DF untuk terms dalam kalimat: '{sentence}'\n")
            
            # 1. Persiapkan data dan vectorizer
            X_train, X_test, y_train, y_test = get_split_data()
            vectorizer = get_vectorizer()
            
            # 2. Fit pada data latih
            X_train_tfidf = vectorizer.fit_transform(X_train)
            feature_names = vectorizer.get_feature_names_out()
            
            # 3. Hitung DF secara manual dari matriks (lebih akurat daripada reverse rumus IDF)
            # DF = jumlah baris (dokumen) yang memiliki nilai > 0 untuk term tersebut
            df_counts = (X_train_tfidf > 0).sum(axis=0).A1
            
            # Buat mapping term -> DF
            df_map = {term: count for term, count in zip(feature_names, df_counts)}
            
            # 4. Ambil terms dari kalimat input (termasuk bigram)
            # Kita gunakan transform untuk tahu term mana saja yang masuk ke vocabulary
            test_vector = vectorizer.transform([sentence])
            test_indices = test_vector.indices
            
            results = []
            for idx in test_indices:
                term = feature_names[idx]
                results.append({
                    'term': term,
                    'df': int(df_map[term])
                })
            
            # Urutkan berdasarkan DF (opsional)
            results = sorted(results, key=lambda x: x['df'], reverse=True)
            
            print(f"Total Dokumen (N): {len(X_train)}")
            print("-" * 50)
            print(f"{'Term':<30} | {'DF (Jumlah Dokumen)':<20}")
            print("-" * 50)
            for r in results:
                print(f"{r['term']:<30} | {r['df']:<20}")
            
            print("\n*DF (Document Frequency) adalah jumlah dokumen dalam data latih yang mengandung kata tersebut.")

if __name__ == "__main__":
    test_sentence = "scan barcode blur coba ubah ukur font scan barcode jernih sukses aplikasi bantu kuliah"
    get_terms_df(test_sentence)
