import psycopg

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}


class Database:
    def __init__(self):
        self.conn = psycopg.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

    def execute_and_fetch_all(self, query, vars=None, **kwargs):
        self.cur.execute(query, vars, **kwargs)
        return self.cur.fetchall()
    
    def close(self):
        self.cur.close()
        self.conn.close()

    
