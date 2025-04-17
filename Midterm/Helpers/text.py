import numpy as np

def split_text_numpy(text, chunk_size=500, chunk_overlap=50):
    text_length = len(text)
    starts = np.arange(0, text_length, chunk_size - chunk_overlap)

    chunks = [text[start:start + chunk_size] for start in starts if start < text_length]
    return chunks