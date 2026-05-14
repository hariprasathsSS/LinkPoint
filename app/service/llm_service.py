from groq import Groq
from app.config import Settings


class LLMService:

    def __init__(self):
        self.client = Groq(
            api_key=Settings.GROQ_API_KEY
        )

    def generate(self, prompt: str):

        response = self.client.chat.completions.create(
            model=Settings.GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        return response.choices[0].message.content
