from ml.database import get_connection

def check_counts():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        print("--- Preprocessing Counts ---")
        cursor.execute("SELECT label, COUNT(*) FROM preprocessing GROUP BY label")
        for label, count in cursor.fetchall():
            print(f"Label: '{label}', Count: {count}")
            
        print("\n--- Hasil Analisis Counts ---")
        cursor.execute("SELECT hasil, COUNT(*) FROM hasil_analisis GROUP BY hasil")
        for hasil, count in cursor.fetchall():
            print(f"Hasil: '{hasil}', Count: {count}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_counts()
