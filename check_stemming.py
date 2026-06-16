from ml.database import get_connection

def check_stemming():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM preprocessing WHERE stemming IS NOT NULL AND stemming != ''")
        count = cursor.fetchone()[0]
        print(f"Total processed (stemming not null): {count}")
        
        cursor.execute("SELECT COUNT(*) FROM preprocessing")
        total = cursor.fetchone()[0]
        print(f"Total rows in preprocessing: {total}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_stemming()
