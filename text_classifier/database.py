class DatabaseManager:
    def __init__(self, db_path="classifier.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        
    def create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            main_category TEXT NOT NULL,
            sub_categories TEXT NOT NULL,
            confidence REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()
        
    def save_classification(self, text, result):
        self.conn.execute("""
        INSERT INTO classifications 
        (text, main_category, sub_categories, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """, (
            text,
            result["category"],
            json.dumps(result["sub_categories"]),
            result["confidence"],
            datetime.now()
        ))
        self.conn.commit()
        
    def get_classifications(self, limit=100):
        cursor = self.conn.execute("""
        SELECT * FROM classifications 
        ORDER BY timestamp DESC 
        LIMIT ?
        """, (limit,))
        return cursor.fetchall() 