import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="ya123"  # ЗАМЕНИТЕ
    )
    print("Подключение успешно!")
    conn.close()
except Exception as e:
    print(f"Ошибка: {e}")