import os

import numpy as np
from openai import OpenAI

from BuildingAIApps.Midterm.Helpers.text import split_text_numpy
from BuildingAIApps.Midterm.sqlite_DB import VectorDB

def store_txt_to_db(client: OpenAI, db: VectorDB, file_path: str):
    """
    Extracts contents from text file, splits it into chunks, generates embeddings for each chunk,
    and stores the embeddings, filename, and corresponding text chunks into a vector database.

    Args:
        client (OpenAI):
            An OpenAI client instance used to generate text embeddings.
        db (VectorDB):
            A vector database instance where the embeddings and associated data will be stored.
        file_path (str):
            The path to the PDF file to be processed.

    Returns:
        None
    """

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