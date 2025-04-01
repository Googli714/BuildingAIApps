import os
import tkinter as tk
from tkinter import filedialog, ttk, font
from traceback import format_exc

from openai import OpenAI
from dotenv import load_dotenv
import customtkinter as ctk
from pathlib import Path
import PyPDF2
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

load_dotenv()

def _split_into_chunks(text, max_chunk_size=1000, overlap=100):
    """Split text into overlapping chunks of approximately max_chunk_size characters."""
    chunks = []

    if len(text) <= max_chunk_size:
        chunks.append(text)
    else:
        start = 0
        while start < len(text):
            end = start + max_chunk_size

            if end > len(text):
                end = len(text)
            else:
                # Try to find a period or newline to break at
                for i in range(min(overlap, end - start)):
                    if text[end - i - 1] in ['.', '\n']:
                        end = end - i
                        break

            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else end

    return chunks


class DocumentQAApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Document Q&A Assistant")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)

        # Use a modern theme
        ctk.set_appearance_mode("dark")  # Use system theme (dark/light)
        ctk.set_default_color_theme("dark-blue")

        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", font=('Segoe UI', 10))
        self.style.configure("TLabel", font=('Segoe UI', 11))

        # Create main container with padding
        self.main_frame = ttk.Frame(self.root, padding=(20, 20, 20, 20))
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create header with title
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 15))

        self.title_label = ttk.Label(self.header_frame, text="AI Document Question & Answer",
                                     font=('Segoe UI', 16, 'bold'))
        self.title_label.pack(side=tk.LEFT)

        # Answer section
        self.answer_frame = ttk.LabelFrame(self.main_frame, text="Answers", padding=(10, 5))
        self.answer_frame.pack(fill=tk.BOTH, expand=True)

        self.answer_text = ctk.CTkTextbox(
            self.answer_frame,
            wrap="word",
            font=("Segoe UI", 11)
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)

        # Question
        self.question_frame = ttk.LabelFrame(self.main_frame, text="Ask a Question", padding=(10, 5))
        self.question_frame.pack(fill=tk.X, pady=(0, 15))

        self.question_entry = ctk.CTkEntry(
            self.question_frame,
            placeholder_text="Type your question here...",
            height=35,
            width=620
        )
        self.question_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10), pady=10)

        self.ask_button = ctk.CTkButton(
            self.question_frame,
            text="Ask",
            command=self.answer_question,
        )
        self.ask_button.pack(side=tk.RIGHT, padx=(0, 5), pady=10)

        # Document section
        self.doc_frame = ttk.LabelFrame(self.main_frame, text="Document Selection", padding=(10, 5))
        self.doc_frame.pack(fill=tk.X, pady=(0, 15))

        self.upload_button = ctk.CTkButton(
            self.doc_frame,
            text="Upload Document",
            command=self.load_document,
        )
        self.upload_button.pack(side=tk.LEFT, padx=(5, 10), pady=10)

        self.file_label = ttk.Label(self.doc_frame, text="No document selected")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)


        self.vector_stores = []

        self.client = OpenAI()
        self.LLM = os.environ.get("OPEN_AI_MODEL")
        self.chat_history = [
            {"role": "system",
             "content": "You are an AI assistant that answers questions based on provided PDF documents or other types of documents. Always try to answer questions from the files and if it's not possible use your knowladge base. When answering from included PDF pages, include the page number that was used."}
        ]

        self.question_entry.bind("<Return>", lambda event: self.answer_question())

    def load_document(self):
        home = Path.home()
        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[("PDF Files", "*.pdf"), ("Text Files", "*.txt")],
            initialdir=home
        )
        with open(file_path, "rb") as file:
            uploaded_file = self.client.files.create(file=file, purpose="user_data")
            self.vector_stores.append(self.client.vector_stores.create(file_ids=[uploaded_file.id]).id)

        if file_path:
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"Selected: {filename}")

    def retrieve_relevant_contexts(self, query, top_k=0.3):
        """
        Retrieve the most relevant document chunks for a given query.

        Args:
            query (str): User query
            top_k (int): Number of relevant documents to retrieve

        Returns:
            list: Top-k most relevant document chunks
        """
        responses = []

        for vector_store in self.vector_stores:
            response = self.client.vector_stores.search(
                vector_store_id=vector_store,
                query=query,
            )
            responses.append(response)

        top_docs = []

        for response in responses:
            for data in response.data:
                if data.score >= top_k:
                    for content in data.content:
                        top_docs.append({
                            'content': content.text,
                            'source': data.filename
                        })

        return top_docs

    def generate_answer(self, query, relevant_docs):
        """
        Generate an answer using the OpenAI API and retrieved contexts.

        Args:
            query (str): User query
            relevant_docs (list): List of relevant document chunks

        Returns:
            str: Generated answer
        """
        # Prepare context from relevant documents
        context = "\n\n---\n\n".join([f"From {doc['source']}:\n{doc['content']}" for doc in relevant_docs])

        # Create prompt with context and query
        message = {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}

        self.chat_history.append(message)

        # Generate answer using OpenAI API
        response = self.client.chat.completions.create(
            model=self.LLM,
            messages=self.chat_history,
            temperature=0.3,
            max_tokens=500
        )

        answer = response.choices[0].message.content
        self.chat_history.append({"role": "assistant", "content": answer})

        return answer

    def answer_question(self):
        question = self.question_entry.get().strip()

        if not question:
            return

        try:
            self.answer_text.configure(state="normal")
            self.answer_text.insert("end", f"\n\nQ: {question}\nA: Thinking...\n")
            self.answer_text.see("end")
            self.root.update_idletasks()


            relevant_docs = self.retrieve_relevant_contexts(question)

            # Generate answer
            answer = self.generate_answer(question, relevant_docs)

            self.display_answer(question, answer)

            # Clear the question entry for the next question
            self.question_entry.delete(0, tk.END)
        except Exception as e:
            self.answer_text.configure(state="normal")
            self.answer_text.insert("end", f"\nError occurred: {str(e)}\n")
            self.answer_text.see("end")

    def display_answer(self, question, answer):
        # Clear the "thinking" message and display the real answer
        self.answer_text.configure(state="normal")
        self.answer_text.delete("end-2l", "end")
        self.answer_text.insert("end", f"\n\nA: {answer}\n\n")
        self.answer_text.insert("end", "-" * 60 + "\n")
        self.answer_text.see("end")
        self.answer_text.configure(state="disabled")

    def clear_history(self):
        # Clear the display and reset chat history
        self.answer_text.configure(state="normal")
        self.answer_text.delete("1.0", "end")
        self.answer_text.configure(state="disabled")

        # Reset chat history but keep the system message
        self.chat_history = [self.chat_history[0]]


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")

    root = ctk.CTk()
    app = DocumentQAApp(root)

    window_width = 800
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - window_width / 2)
    center_y = int(screen_height / 2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    root.mainloop()