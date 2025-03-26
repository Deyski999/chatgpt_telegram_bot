import openai
import config
import base64
from io import BytesIO

class ChatGPT:
    def __init__(self, model="gpt-3.5-turbo"):
        self.model = model

    async def send_message(self, message, dialog_messages=None, chat_mode="assistant"):
        messages = []
        if dialog_messages:
            for msg in dialog_messages:
                if "text" in msg["user"][0]:
                    messages.append({"role": "user", "content": msg["user"][0]["text"]})
                    messages.append({"role": "assistant", "content": msg["bot"]})
        messages.append({"role": "user", "content": message})

        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
        )
        answer = response.choices[0].message.content.strip()
        return answer, (response.usage.prompt_tokens, response.usage.completion_tokens), 0

    async def send_vision_message(self, message, dialog_messages=None, image_buffer=None, chat_mode="assistant"):
        base64_image = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
        image_input = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            },
        }
        messages = []
        if dialog_messages:
            for msg in dialog_messages:
                if "text" in msg["user"][0]:
                    messages.append({"role": "user", "content": msg["user"]})
                    messages.append({"role": "assistant", "content": msg["bot"]})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": message},
                image_input
            ]
        })

        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages
        )

        answer = response.choices[0].message.content.strip()
        return answer, (response.usage.prompt_tokens, response.usage.completion_tokens), 0


async def transcribe_audio(file):
    audio_file = BytesIO(file.read())
    audio_file.name = "voice.ogg"
    file.seek(0)
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]


async def generate_images(prompt, n_images=1, size="1024x1024"):
    response = openai.Image.create(
        prompt=prompt,
        n=n_images,
        size=size
    )
    return [data["url"] for data in response["data"]]
