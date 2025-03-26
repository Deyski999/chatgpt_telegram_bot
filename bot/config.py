import os

telegram_token = os.getenv("TELEGRAM_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Dialog timeout (in seconds)
new_dialog_timeout = 600

# Supported chat modes
chat_modes = {
    "assistant": {
        "name": "💬 Assistant",
        "welcome_message": "How can I help you today?",
        "parse_mode": "html"
    },
    "artist": {
        "name": "👩‍🎨 Artist",
        "welcome_message": "Send me a prompt and I will draw something!",
        "parse_mode": "html"
    },
}

n_chat_modes_per_page = 5

# Supported models
models = {
    "available_text_models": ["gpt-3.5-turbo", "gpt-4-vision-preview", "gpt-4o"],
    "info": {
        "gpt-3.5-turbo": {
            "name": "GPT-3.5",
            "description": "Fast and cost-effective. Best for general tasks.",
            "price_per_1000_input_tokens": 0.0015,
            "price_per_1000_output_tokens": 0.002,
            "scores": {"Speed": 5, "Logic": 3, "Creativity": 3}
        },
        "gpt-4-vision-preview": {
            "name": "GPT-4 Vision",
            "description": "Advanced reasoning and image understanding.",
            "price_per_1000_input_tokens": 0.01,
            "price_per_1000_output_tokens": 0.03,
            "scores": {"Speed": 3, "Logic": 5, "Creativity": 5}
        },
        "gpt-4o": {
            "name": "GPT-4 Omni",
            "description": "Faster and cheaper GPT-4 with image support.",
            "price_per_1000_input_tokens": 0.005,
            "price_per_1000_output_tokens": 0.015,
            "scores": {"Speed": 4, "Logic": 5, "Creativity": 5}
        },
        "dalle-2": {
            "price_per_1_image": 0.02
        },
        "whisper": {
            "price_per_1_min": 0.006
        },
    }
}

# Default image generation settings
image_size = "1024x1024"
return_n_generated_images = 1

# Access control
allowed_telegram_usernames = []  # leave empty to allow everyone

enable_message_streaming = False

# Static content path
help_group_chat_video_path = "static/help_group_chat.mp4"
