# Semantic Document Search Engine

Advanced search across multiple uploaded documents.  
Just ask a question — get direct answers from the right parts of your documents!

---

## Task Description

The goal of this project was to build a **semantic document search engine**, 
which would be able to: 
- Take in multiple documents (PDF/TXT).
- Automatically split and process documents.
- Perform intelligent retrieval: find the most relevant sections when asked a question.
- Use OpenAI models to answer.

---

## How We Approached It

1. **Document Ingestion**:
   - Users can upload one or more PDF/TXT files.
   - PDFs are parsed page by page, text files are parsed by lines/paragraphs.
   - Each chunk of text is embedded using OpenAI's `text-embedding-3-large` model.

2. **Vector Storage**:
   - Embeddings are stored in a **local SQLite** database.
   - Each stored entry includes the chunk's content, its source (filename + page), and its vector.

3. **Semantic Search**:
   - When a user asks a question:
     - The question is embedded.
     - The system searches the vector database for the most relevant document chunks using similarity search.

4. **Answer Generation**:
   - Relevant document chunks are fed as "context" to OpenAI's chat model (`gpt-4o` or your selected model).
   - The system generates an answer based on document content, falling back to general knowledge if necessary.
   - Final answers include references to the document and page numbers when possible.

5. **Application GUI**:
   - Built with `CustomTkinter`.
   - Simple and intuitive.

---

# Getting started:

# First, clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

# Install libraries
```
pip install -r requirements.txt
```

# Setup .env
```
OPEN_AI_MODEL="gpt-4o"
OPENAI_API_KEY=
```
#
**After completing the set-up process, you can run the application and the user interface will be loaded
where you can upload documents of your choice and ask questions.**