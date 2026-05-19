import requests

class LLMService:
    def __init__(self):
        self.url = "http://DESKTOP-TE4J5GB:11434/api/generate"
        self.model = "gemma4:26b"
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

        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": conversation,
                    "stream": False,
                },
                timeout=timeout
            )
        except requests.exceptions.ConnectTimeout:
            raise ConnectionError(
                f"Cannot reach Ollama server at {self.url.split('/api')[0]}. "
                "Make sure DESKTOP-TE4J5GB is on, Ollama is running, "
                "and you are on the same network."
            )
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama server at {self.url.split('/api')[0]}. "
                "Make sure DESKTOP-TE4J5GB is on and Ollama is running."
            )

        result = response.json()["response"].strip()

        self.chat_history.append({"role": "assistant", "content": result})

        return result
