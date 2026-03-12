import requests

class LLMService:
    def __init__(self):
        self.url = "http://localhost:11434/api/generate"
        self.model = "qwen2.5"
        self.chat_history = []

    def ask(self, system_prompt, user_message, timeout=120):

        self.chat_history = self.chat_history[-5:]
        self.chat_history.append({"role": "user", "content": user_message})

        # Build conversation text
        conversation = system_prompt + "\n\n"

        for msg in self.chat_history:
            role = msg["role"].capitalize()
            conversation += f"{role}: {msg['content']}\n"

        conversation += "Assistant:"

        response = requests.post(
            self.url,
            json={
                "model": self.model,
                "prompt": conversation,
                "stream": False,
            },
            timeout=timeout
        )

        result = response.json()["response"].strip()

        self.chat_history.append({"role": "assistant", "content": result})

        return result
