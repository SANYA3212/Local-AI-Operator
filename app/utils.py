# app/utils.py
import requests
import json
from app.config import OLLAMA_BASE_URL

def ollama_stream_generate(model, prompt, system=None, context=None, image_data=None):
    """
    Calls the Ollama API to generate a response, supporting multimodal inputs.
    Yields each part of the response as it is received.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }
    if system:
        payload["system"] = system
    if context:
        payload["context"] = context
    if image_data:
        # Remove the 'data:image/...;base64,' prefix
        image_data_cleaned = image_data.split(',')[-1]
        payload["images"] = [image_data_cleaned]

    try:
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    yield data

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        yield {
            "error": str(e),
            "response": "Sorry, I am having trouble connecting to the language model."
        }
