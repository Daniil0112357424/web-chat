import sqlite3
import requests

conn = sqlite3.connect('gallery.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS gallery (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE)')
conn.commit()

cursor.execute('SELECT id, url FROM gallery')
rows = cursor.fetchall()

for row in rows:
    img_id, url = row
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True)
        # Удалять если не 200 (даже если 401, 403, 404 и т.д.)
        if resp.status_code != 200:
            print(f"Удаляю битую ссылку: {url} (код {resp.status_code})")
            cursor.execute('DELETE FROM gallery WHERE id=?', (img_id,))
    except Exception as e:
        print(f"Ошибка при проверке {url}: {e}")
        cursor.execute('DELETE FROM gallery WHERE id=?', (img_id,))

conn.commit()
conn.close()
print("Очистка завершена.")