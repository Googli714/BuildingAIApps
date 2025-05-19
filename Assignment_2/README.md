# AI Function calling app

A modern desktop application that uses OpenAI's function calling capabilities to provide intelligent responses to user questions, perform calculations, search a product database, and fetch weather information.

## Features

- **Intelligent Q&A**: Ask questions and get AI-powered responses
- **Function Calling**: Leverages OpenAI's function calling to perform actions like:
  - Mortgage calculations
  - Product database searches
  - Weather information retrieval
- **Modern UI**: Clean, responsive interface built with customtkinter
- **Dark Mode**: Sleek, eye-friendly dark theme

## Prerequisites

Before running this application, you'll need:

1. Python 3.7 or higher
2. OpenAI API key
3. Required Python packages

## Installation

1. Clone this repository:
   ```
   git clone <repo_url>
   cd <repo>
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   OPEN_AI_MODEL=gpt-3.5-turbo-1106  # or another model that supports function calling
   ```

## How to Run

1. Make sure you have all prerequisites installed and your `.env` file is set up.

2. Run the application:
   ```
   python app.py
   ```

3. Use the application:
   - Type your question in the input field at the bottom
   - Click "Ask" or press Enter
   - View the response in the main text area

