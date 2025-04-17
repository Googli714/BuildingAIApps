import io
import sqlite3
from typing import List, Tuple, Any

import numpy as np

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

def euclidean_distance(point1, point2):
    if point1.shape != point2.shape:
        raise ValueError("Input points must have the same shape.")

    # Calculate the Euclidean distance
    distance = np.linalg.norm(point1 - point2)

    return distance

def get_nearest_neighbor(train, test_row, num_neighbors: int = 1):
    distances = []

    for train_row in train:
        dist = euclidean_distance(test_row, train_row)
        distances.append((train_row, dist))

    distances.sort(key=lambda tup: tup[1])
    neighbors = []

    for i in range(num_neighbors):
        neighbors.append(distances[i][0])

    return neighbors


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

    def _insert_data(self, table_name: str, data: List[Tuple[np.array, str, str, str]]):
        self.cur.executemany(f"INSERT INTO {table_name} (arr, filename, text_content) VALUES (?, ?, ?, ?)", data)
        # Commit changes
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
    def __init__(self, collection_name: str):
        super().__init__()
        self.collection_name = collection_name

    def create(self):
        self._create_table(self.collection_name)

    def insert(self, data: List[Tuple[np.array, str, str, str]]):
        self._insert_data(self.collection_name, data)

    def search(self, query: np.array, num_results: int):
        vectors = self._query_data(self.collection_name)
        vectors = [vector[0] for vector in vectors]
        return get_nearest_neighbor(vectors, query, num_results)
