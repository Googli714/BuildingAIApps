import numpy as np

def split_text_numpy(text, chunk_size=500, chunk_overlap=50):
    """
    Splits up text into smaller chunks with the specified chunk-size and overlap.

    Args:
        text (str):
            The text to be split.
        chunk_size (int):
            Size of each chunk.
        chunk_overlap (int):
            Amount of overlap between chunks to maintain context.

    Returns:
        An array containing chunks of the text.
    """
    text_length = len(text)
    starts = np.arange(0, text_length, chunk_size - chunk_overlap)

    chunks = [text[start:start + chunk_size] for start in starts if start < text_length]
    return chunks


