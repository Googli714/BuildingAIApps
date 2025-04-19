import io
import sqlite3
from typing import List, Tuple, Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def adapt_array(arr):
    """
    http://stackoverflow.com/a/31312102/190597
    """
    out = io.BytesIO()
    np.save(out, arr)  # noqa
    out.seek(0)
    return sqlite3.Binary(out.read())

def convert_array(text):
    """
    https://stackoverflow.com/a/18622264
    """
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)  # noqa

sqlite3.register_adapter(np.ndarray, adapt_array)

sqlite3.register_converter("array", convert_array)


class SQLiteDB:
    def __init__(self, database: str = ":memory:"):
        self.conn = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cur = self.conn.cursor()

    def _create_table(self, table_name: str):
        sql = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            arr array NOT NULL,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            text_content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

        self.cur.execute(sql)
        self.conn.commit()

    def _insert_data(self, table_name: str, data: List[Tuple[np.array, str, str]]):
        self.cur.executemany(f"INSERT INTO {table_name} (arr, filename, text_content) VALUES (?, ?, ?)", data)
        self.conn.commit()

    def _query_data(self, table_name: str, condition: str = None) -> List[Tuple]:
        sql = f"SELECT * FROM {table_name}"
        if condition:
            sql += f" WHERE {condition}"
        self.cur.execute(sql)
        return self.cur.fetchall()

    def _close(self):
        self.conn.close()


class VectorDB(SQLiteDB):
    def __init__(self, db: str, collection_name: str):
        super().__init__(database=db)
        self.collection_name = collection_name
        self.create()

    def create(self):

        sql = f'''SELECT name FROM sqlite_master WHERE type='table' AND name='{self.collection_name}' '''
        self.cur.execute(sql)
        res = self.cur.fetchall()
        if len(res) == 0:
            self._create_table(self.collection_name)

    def insert(self, data: List[Tuple[np.array, str, str]]):
        self._insert_data(self.collection_name, data)

    def search(self, query: np.array, top_k: int = 3):
        rows = self._query_data(self.collection_name)

        similarities = []
        for row in rows:
            similarity = cosine_similarity(
                [query],
                [row[0]]
            )[0][0]
            similarities.append(similarity)

        top_indices = np.argsort(similarities)[-top_k:][::-1]

        top_docs = []
        for idx in top_indices:
            top_docs.append(rows[idx])

        return top_docs
