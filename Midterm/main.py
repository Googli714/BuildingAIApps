import os
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QLineEdit, QTextEdit, QFileDialog, 
                            QGroupBox, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QAction
from pathlib import Path

from sqlite_DB import VectorDB
from Helpers.pdf import store_pdf_to_db
from Helpers.txt import store_txt_to_db

load_dotenv()

class DocumentQAApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize database
        self.db = VectorDB(db="midterm.db", collection_name="vectors")
        
        # Setup OpenAI client ( DO NOT FORGET TO PUT IN YOUR API KEY AND MODEL)
        self.client = OpenAI(api_key="YOUR_KEY_HERE")
        self.LLM = os.environ.get("OPEN_AI_MODEL") # "gpt-3.5-turbo" # example
        self.chat_history = [
            {"role": "system",
             "content": "You are a semantic document search engine that answers questions based on provided PDF documents or other types of documents. Always try to answer questions from the files and if it's not possible use your knowledge base. When answering from provided documents, include the name of the document and the page number that was used at the end of the answer."}
        ]
        
        # Initialize UI
        self.setWindowTitle("Semantic document search engine")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.setup_header()
        self.setup_answer_area()
        self.setup_question_area()
        self.setup_document_area()
        self.apply_styles()
        
    def setup_header(self):
        header_layout = QHBoxLayout()
        title_label = QLabel("AI Document Question & Answer")
        title_font = QFont("Segoe UI", 16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)
        
    def setup_answer_area(self):
        answer_group = QGroupBox("Answers")
        answer_layout = QVBoxLayout(answer_group)
        
        self.answer_text = QTextEdit()
        self.answer_text.setReadOnly(True)
        self.answer_text.setFont(QFont("Segoe UI", 11))
        answer_layout.addWidget(self.answer_text)
        
        self.main_layout.addWidget(answer_group)
        
    def setup_question_area(self):
        question_group = QGroupBox("Ask a Question")
        question_layout = QHBoxLayout(question_group)
        
        self.question_entry = QLineEdit()
        self.question_entry.setPlaceholderText("Type your question here...")
        self.question_entry.setMinimumHeight(35)
        question_layout.addWidget(self.question_entry)
        
        self.ask_button = QPushButton("Ask")
        self.ask_button.clicked.connect(self.answer_question)
        question_layout.addWidget(self.ask_button)
        
        self.main_layout.addWidget(question_group)
        
        # Connect enter key press
        self.question_entry.returnPressed.connect(self.answer_question)
        
    def setup_document_area(self):
        doc_group = QGroupBox("Document Selection")
        doc_layout = QHBoxLayout(doc_group)
        
        self.upload_button = QPushButton("Upload Document")
        self.upload_button.clicked.connect(self.load_document)
        doc_layout.addWidget(self.upload_button)
        
        self.file_label = QLabel("No document selected")
        self.file_label.setFont(QFont("Segoe UI", 10))
        doc_layout.addWidget(self.file_label)
        doc_layout.addStretch()
        
        self.main_layout.addWidget(doc_group)
        
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2d2d2d;
                color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QTextEdit, QLineEdit {
                background-color: #3d3d3d;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
            QLabel {
                color: #f0f0f0;
            }
        """)
    
    def load_document(self):
        home = Path.home()
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Document(s)",
            str(home),
            "Documents (*.pdf *.txt)"
        )
        
        self.file_label.setText("Uploading files")
        self.ask_button.setEnabled(False)
        self.question_entry.setEnabled(False)
        
        if len(file_paths) == 0:
            self.file_label.setText("No document(s) selected")
            self.ask_button.setEnabled(True)
            self.question_entry.setEnabled(True)
            return
        
        selected_files = ""
        
        for file_path in file_paths:
            extension = os.path.splitext(file_path)[1]
            if extension == '.pdf':
                store_pdf_to_db(self.client, self.db, file_path)
            elif extension == '.txt':
                store_txt_to_db(self.client, self.db, file_path)
            else:
                print("No extension for you")
                
            filename = os.path.basename(file_path)
            selected_files += f"{filename}, "
        
        self.file_label.setText(f"Selected: {selected_files}")
        
        self.ask_button.setEnabled(True)
        self.question_entry.setEnabled(True)
    
    def retrieve_relevant_contexts(self, query, top_k=0.3):
        res = self.client.embeddings.create(input=query, model="text-embedding-3-large")
        embedding = res.data[0].embedding
        embedding = np.array(embedding)
        
        relevant_docs = self.db.search(embedding, 3)
        
        top_docs = []
        
        for doc in relevant_docs:
            top_docs.append({
                'content': doc[3],
                'source': doc[2]
            })
        
        return top_docs
    
    def generate_answer(self, query, relevant_docs):
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
        question = self.question_entry.text().strip()
        
        if not question:
            return
        
        try:
            self.answer_text.append(f"\n\nQ: {question}\nA: Thinking...\n")
            self.answer_text.ensureCursorVisible()
            QApplication.processEvents()
            
            relevant_docs = self.retrieve_relevant_contexts(question)
            
            answer = self.generate_answer(question, relevant_docs)
            
            self.display_answer(question, answer)
            self.question_entry.clear()
        except Exception as e:
            self.answer_text.append(f"\nError occurred: {str(e)}\n")
            self.answer_text.ensureCursorVisible()
    
    def display_answer(self, question, answer):
        current_text = self.answer_text.toPlainText()
        if current_text.endswith("Thinking...\n"):
            text_lines = current_text.split('\n')
            if len(text_lines) >= 2:
                text_lines.pop(-2)  # Remove the "Thinking..." line
                self.answer_text.clear()
                self.answer_text.setPlainText('\n'.join(text_lines))
        
        self.answer_text.append(f"A: {answer}\n\n")
        self.answer_text.append("-" * 60 + "\n")
        self.answer_text.ensureCursorVisible()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentQAApp()
    
    # Center the window
    window_width = 800
    window_height = 600
    screen_size = app.primaryScreen().size()
    x = (screen_size.width() - window_width) // 2
    y = (screen_size.height() - window_height) // 2
    window.setGeometry(x, y, window_width, window_height)
    
    window.show()
    sys.exit(app.exec())