import sys
sys.path.insert(0, '/app')
from auth.password import hash_password
import psycopg2, os

h = hash_password('admin123')
c = psycopg2.connect(os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("UPDATE users SET password_hash = %s WHERE username = 'admin'", (h,))
c.commit()
print('Done:', h)
c.close()
