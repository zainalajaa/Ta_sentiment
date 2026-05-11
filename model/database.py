import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # isi sesuai Laragon kamu
        database="ta_sentiment"
    )
    return conn