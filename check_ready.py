from ml.database import get_connection

def check_ready_data():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT label, COUNT(*)
            FROM preprocessing
            WHERE stemming IS NOT NULL
            AND stemming != ''
            AND label IN ('positif', 'negatif')
            GROUP BY label
        """)
        results = cursor.fetchall()
        print("--- Ready for training (stemming not null & +/-) ---")
        for label, count in results:
            print(f"Label: {label}, Count: {count}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_ready_data()
