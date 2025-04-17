import os.path

import numpy as np
from openai import OpenAI
import PyPDF2

from Midterm.Helpers.text import split_text_numpy
from Midterm.sqlite_DB import VectorDB


def store_pdf_to_db(client: OpenAI, db: VectorDB, file_path: str):
    text = ""
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"

    chunks = split_text_numpy(text)
    to_insert_to_db = []

    for chunk in chunks:
        res = client.embeddings.create(input=chunk, model="text-embedding-ada-002")
        embedding = res.data[0].embedding
        embedding = np.array(embedding)
        to_insert_to_db.append((embedding, filename, chunk))

    db.insert(to_insert_to_db)

    return