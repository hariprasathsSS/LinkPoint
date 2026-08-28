# app/service/prompt_service.py

class PromptService:

    PROMPT_VERSION = "v1"

    def build(self, query, results):

        context = "\n".join(r["result"]["text"] for r in results)

        return f"""
            You are an AI assistant.

            Provide detailed response based on the context.

            Answer ONLY from the provided context.

            If answer is not in context, respond with a unique message every time.

            Context:
            {context}

            Question:
            {query}

            Answer:
        """
