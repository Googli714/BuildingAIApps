import os
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.constants import DISABLED, NORMAL

import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import customtkinter as ctk
from pathlib import Path

from sqlite_DB import VectorDB
from Helpers.pdf import store_pdf_to_db
from Helpers.txt import store_txt_to_db

load_dotenv()

class DocumentQAApp:
    def __init__(self, root):
        self.root = root
        self.db = VectorDB(db="midterm.db", collection_name="vectors")
        self.root.title("Semantic document search engine")
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
             "content": "You are a semantic document search engine that answers questions based on provided PDF documents or other types of documents. Always try to answer questions from the files and if it's not possible use your knowledge base. When answering from provided documents, include the name of the document and the page number that was used at the end of the answer."}
        ]

        self.question_entry.bind("<Return>", lambda event: self.answer_question())

    def load_document(self):
        """
        Allows user to pick a document and load it,
        Extracts the text and stores the document chunks in the
        database. Accepts only PDF or TXT files.

        :return:
        """
        home = Path.home()
        file_paths = filedialog.askopenfilenames(
            title="Select Document(s)",
            filetypes=[("PDF Files", "*.pdf"), ("Text Files", "*.txt")],
            initialdir=home
        )

        self.file_label.config(text="Uploading files")
        self.ask_button.configure(state=DISABLED)
        self.question_entry.configure(state=DISABLED)

        if len(file_paths) == 0:
            self.file_label.config(text=f"No document(s) selected")
            self.ask_button.configure(state=NORMAL)
            self.question_entry.configure(state=NORMAL)

            return

        selected_files = ""

        for file_path in file_paths:
            extension = os.path.splitext(file_path)[1]
            if extension == '.pdf':
                store_pdf_to_db(self.client, self.db, file_path)
            elif extension == '.txt':
                store_txt_to_db(self.client, self.db, file_path)
            else:
                print("no extension for you")

            filename = os.path.basename(file_path)
            selected_files += f"{filename}, "

        self.file_label.config(text=f"Selected: {selected_files}")

        self.ask_button.configure(state=NORMAL)
        self.question_entry.configure(state=NORMAL)

    def retrieve_relevant_contexts(self, query, top_k= 3):
        """
        Retrieves the most relevant chunks from the database

        :param query: Input question from the user
        :param top_k:
        :return: A list of relevant document chunks, each containing:
            - 'content' (str): The text content of the chunk.
            - 'source' (str): The filename and page number.
        """
        res = self.client.embeddings.create(input=query, model="text-embedding-3-large")
        embedding = res.data[0].embedding
        embedding = np.array(embedding)

        relevant_docs = self.db.search(embedding, top_k)

        top_docs = []

        for doc in relevant_docs:
            top_docs.append({
                'content': doc[3],
                'source': doc[2]
            })

        return top_docs

    def generate_answer(self, query, relevant_docs):
        """
         Generates an answer to the user's question using the provided document context.

        :param query: The user's question.
        :param relevant_docs:  List of relevant document chunks retrieved from the database
        :return: The generated answer from the language model.
        """
        context = "\n\n---\n\n".join([f"From {doc['source']}:\n{doc['content']}" for doc in relevant_docs])
        message = {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}

        self.chat_history.append(message)

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
        """
        Encapsulates the flow of what the app does when a user asks a question.
        :return:
        """
        question = self.question_entry.get().strip()

        if not question:
            return

        try:
            self.answer_text.configure(state="normal")
            self.answer_text.insert("end", f"\n\nQ: {question}\nA: Thinking...\n")
            self.answer_text.see("end")
            self.root.update_idletasks()

            relevant_docs = self.retrieve_relevant_contexts(question)

            answer = self.generate_answer(question, relevant_docs)

            self.display_answer(question, answer)
            self.question_entry.delete(0, tk.END)
        except Exception as e:
            self.answer_text.configure(state="normal")
            self.answer_text.insert("end", f"\nError occurred: {str(e)}\n")
            self.answer_text.see("end")

    def display_answer(self, question, answer):
        """
        Updates interface to display the answer for the inputted question
        :param question: User question.
        :param answer: Answer by AI model
        :return:
        """
        self.answer_text.configure(state="normal")
        self.answer_text.delete("end-2l", "end")
        self.answer_text.insert("end", f"\n\nA: {answer}\n\n")
        self.answer_text.insert("end", "-" * 60 + "\n")
        self.answer_text.see("end")
        self.answer_text.configure(state="disabled")

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