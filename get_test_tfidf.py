
import sys
import os
import pandas as pd
import numpy as np
from app import app, get_vectorizer, get_split_data

def get_sentence_tfidf(sentence):
    with app.app_context():
        # Simulasi session jika diperlukan (tapi app context biasanya cukup jika session diakses)
        # Namun karena session.get butuh request context, kita hack sedikit get_split_data
        # atau kita panggil manual logic-nya. 
        # Untuk amannya, kita buatkan mock request context.
        with app.test_request_context():
            print(f"Memproses kalimat: '{sentence}'\n")
            
            # 1. Persiapkan data dan vectorizer
            X_train, X_test, y_train, y_test = get_split_data()
            vectorizer = get_vectorizer()
            
            # 2. Fit pada data latih (untuk membangun vocab dan IDF)
            X_train_tfidf = vectorizer.fit_transform(X_train)
            
            # 3. Transform kalimat uji
            test_vector = vectorizer.transform([sentence])
            
            # 4. Ambil fitur dan skor
            feature_names = vectorizer.get_feature_names_out()
            indices = test_vector.indices
            data = test_vector.data
            
            results = []
            for idx, score in zip(indices, data):
                results.append({
                    'term': feature_names[idx],
                    'tfidf': score
                })
            
            # Urutkan berdasarkan skor tertinggi
            results = sorted(results, key=lambda x: x['tfidf'], reverse=True)
            
            print(f"{'Term':<30} | {'Skor TF-IDF':<15}")
            print("-" * 50)
            for r in results:
                print(f"{r['term']:<30} | {r['tfidf']:.6f}")

if __name__ == "__main__":
    test_sentence = "scan barcode blur coba ubah ukur font scan barcode jernih sukses aplikasi bantu kuliah"
    get_sentence_tfidf(test_sentence)
