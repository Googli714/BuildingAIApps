import os

import numpy as np
from openai import OpenAI

from Midterm.Helpers.text import split_text_numpy
from Midterm.sqlite_DB import VectorDB

def store_txt_to_db(client: OpenAI, db: VectorDB, file_path: str):
    text = ""
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as file:
        text += file.read()

    chunks = split_text_numpy(text)
    to_insert_to_db = []

    for chunk in chunks:
        res = client.embeddings.create(input=chunk, model="text-embedding-3-large")
        embedding = res.data[0].embedding
        embedding = np.array(embedding)
        to_insert_to_db.append((embedding, filename, chunk))

    db.insert(to_insert_to_db)
    return