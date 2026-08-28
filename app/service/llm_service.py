from groq import Groq
from app.config import Settings
import httpx

class LLMService:

    GENERATION_PARAMS = {"temperature": 0.2}

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
            **self.GENERATION_PARAMS
        )

        return response.choices[0].message.content


    async def generate_local(self, prompt: str):

        BASE_URL = f"http://{Settings.OLLAMA_HOST}:{Settings.OLLAMA_PORT}/api/generate"
        model = Settings.OLLAMA_MODEL
        payload = {
            "model":model,
            "prompt":prompt,
            "stream":False
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(BASE_URL, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("response")
                else:
                    return f"Error: {response.status_code} - {response.text}"

        except httpx.ConnectError:
            return "Connection Error: Is Ollama running? (Run 'ollama serve')"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
