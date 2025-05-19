import os
import tkinter as tk
from tkinter import filedialog, ttk
import json
import math
import random
import requests


from openai import OpenAI
from dotenv import load_dotenv
import customtkinter as ctk
from pathlib import Path

load_dotenv()


class FunctionCallingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Function calling app")
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

        self.title_label = ttk.Label(self.header_frame, text="AI Function calling app",
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

        self.client = OpenAI()
        self.LLM = os.environ.get("OPEN_AI_MODEL")

        # Define the function calling tools
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate_mortgage",
                    "description": "Calculate monthly mortgage payment based on principal, interest rate, and loan term",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "principal": {
                                "type": "number",
                                "description": "The loan amount in dollars"
                            },
                            "rate": {
                                "type": "number",
                                "description": "Annual interest rate as a percentage (e.g., 5.5 for 5.5%)"
                            },
                            "years": {
                                "type": "number",
                                "description": "Loan term in years"
                            }
                        },
                        "required": ["principal", "rate", "years"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_product_database",
                    "description": "Search a product database for items matching the query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for finding products"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return"
                            }
                        },
                        "required": ["query", "max_results"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]

        # Function implementations
        self.available_functions = {
            "calculate_mortgage": self.calculate_mortgage,
            "search_product_database": self.search_product_database,
            "get_weather": self.get_weather
        }

        # Create simulated product database
        self.product_database = self.create_simulated_product_database()

        self.chat_history = [
            {"role": "system",
             "content": "You are an AI assistant that answers questions. You can also perform calculations and data lookups using available tools."}
        ]

        self.question_entry.bind("<Return>", lambda event: self.answer_question())

    def calculate_mortgage(self, principal, rate, years):
        """Calculate monthly mortgage payment"""
        # Convert annual rate to monthly rate and percentage to decimal
        monthly_rate = rate / 100 / 12
        # Convert years to months
        months = years * 12

        # Calculate monthly payment using mortgage formula
        if monthly_rate == 0:
            # If rate is 0, it's just the principal divided by months
            monthly_payment = principal / months
        else:
            # Standard mortgage formula: P * (r(1+r)^n) / ((1+r)^n - 1)
            monthly_payment = principal * (monthly_rate * math.pow(1 + monthly_rate, months)) / (
                        math.pow(1 + monthly_rate, months) - 1)

        # Calculate total payment and interest
        total_payment = monthly_payment * months
        total_interest = total_payment - principal

        return {
            "monthly_payment": round(monthly_payment, 2),
            "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2)
        }

    def create_simulated_product_database(self):
        """Create a simulated product database for demonstration purposes"""
        categories = ["Electronics", "Home & Kitchen", "Books", "Clothing", "Toys"]
        products = []

        # Generate 100 simulated products
        for i in range(1, 101):
            category = random.choice(categories)
            if category == "Electronics":
                names = ["Smartphone", "Laptop", "Headphones", "Tablet", "Camera", "Smart Watch", "TV"]
                brands = ["Apple", "Samsung", "Sony", "LG", "Dell", "HP", "Bose"]
                name = f"{random.choice(brands)} {random.choice(names)}"
                price = round(random.uniform(99.99, 1999.99), 2)
            elif category == "Home & Kitchen":
                items = ["Blender", "Coffee Maker", "Toaster", "Vacuum", "Cookware Set", "Knife Set"]
                brands = ["Cuisinart", "KitchenAid", "Breville", "Dyson", "Calphalon", "OXO"]
                name = f"{random.choice(brands)} {random.choice(items)}"
                price = round(random.uniform(29.99, 399.99), 2)
            elif category == "Books":
                genres = ["Fiction", "Non-fiction", "Self-help", "Cooking", "History", "Science"]
                titles = ["Guide to", "Introduction to", "Mastering", "Complete", "Essential"]
                name = f"{random.choice(titles)} {random.choice(genres)}"
                price = round(random.uniform(9.99, 49.99), 2)
            elif category == "Clothing":
                types = ["T-shirt", "Jeans", "Sweater", "Jacket", "Dress", "Shoes"]
                brands = ["Nike", "Adidas", "Levi's", "H&M", "Zara", "Gap"]
                name = f"{random.choice(brands)} {random.choice(types)}"
                price = round(random.uniform(19.99, 149.99), 2)
            else:  # Toys
                toys = ["Action Figure", "Board Game", "Puzzle", "LEGO Set", "Doll", "Remote Control Car"]
                brands = ["Hasbro", "Mattel", "LEGO", "Fisher-Price", "Melissa & Doug"]
                name = f"{random.choice(brands)} {random.choice(toys)}"
                price = round(random.uniform(14.99, 99.99), 2)

            rating = round(random.uniform(1.0, 5.0), 1)
            in_stock = random.choice([True, True, True, False])  # 75% chance to be in stock

            products.append({
                "id": i,
                "name": name,
                "category": category,
                "price": price,
                "rating": rating,
                "in_stock": in_stock
            })

        return products

    def search_product_database(self, query, max_results=5):
        """Search the product database for products matching the query"""
        query = query.lower()
        results = []

        # Simple search implementation
        for product in self.product_database:
            if query in product["name"].lower() or query in product["category"].lower():
                results.append(product)

        # Sort by relevance (simple implementation: just sort by whether name contains query first)
        results.sort(key=lambda p: query in p["name"].lower(), reverse=True)

        # Limit results
        if max_results and isinstance(max_results, int):
            results = results[:max_results]

        return {
            "query": query,
            "num_results": len(results),
            "results": results
        }

    def get_weather(self, location: str):
        url = f'https://goweather.xyz/weather/{location}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                # Extract relevant weather information
                temperature = data["temperature"]
                wind = data["wind"]
                description = data["description"]

                # Return the weather data
                return {
                    "temperature": temperature,
                    "wind": wind,
                    "description": description
                }
            else:
                return {}
        except requests.exceptions.RequestException as e:
            print("Error occurred during API request:", e)

    def generate_answer(self, query):
        message = {"role": "user", "content": f"{query}"}

        self.chat_history.append(message)

        # First, create a completion that might include a function call
        response = self.client.chat.completions.create(
            model=self.LLM,
            messages=self.chat_history,
            tools=self.tools,
            temperature=0.3,
            max_tokens=500
        )

        response_message = response.choices[0].message
        self.chat_history.append(response_message)

        # Check if the model wants to call a function
        if response_message.tool_calls:
            # Process each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Call the function and get the result
                function_to_call = self.available_functions[function_name]
                function_response = function_to_call(**function_args)

                # Add the function result to the chat history
                self.chat_history.append({
                    "role": "tool",
                    "content": json.dumps(function_response),
                    "tool_call_id": tool_call.id
                })

            # Send the updated chat history back to the model to get the final response
            second_response = self.client.chat.completions.create(
                model=self.LLM,
                messages=self.chat_history,
                temperature=0.3,
                max_tokens=500
            )

            answer = second_response.choices[0].message.content
            self.chat_history.append({"role": "assistant", "content": answer})
        else:
            answer = response_message.content

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

            answer = self.generate_answer(question)

            self.display_answer(question, answer)
            self.question_entry.delete(0, tk.END)
        except Exception as e:
            self.answer_text.configure(state="normal")
            self.answer_text.delete("end-2l", "end")
            self.answer_text.insert("end", f"\nError occurred: {str(e)}\n")
            self.answer_text.see("end")

    def display_answer(self, question, answer):
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
    app = FunctionCallingApp(root)

    window_width = 800
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - window_width / 2)
    center_y = int(screen_height / 2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    root.mainloop()