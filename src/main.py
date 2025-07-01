import os
from openai import OpenAI
from dotenv import load_dotenv

# Load .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Create OpenAI client
client = OpenAI(api_key=api_key)

def ask_gpt(question):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    user_question = input("Ask ChatGPT: ")
    answer = ask_gpt(user_question)
    print("\nChatGPT says:\n", answer)
