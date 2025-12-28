# app/utils.py
import requests
import json
from app.config import OLLAMA_BASE_URL

def ollama_generate(model, prompt, system=None, context=None):
    """
    Calls the Ollama API to generate a response.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt
    }
    if system:
        payload["system"] = system
    if context:
        payload["context"] = context

    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()

        full_response = ""
        final_context = None

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                full_response += data.get("response", "")
                if data.get("done"):
                    final_context = data.get("context")

        return {
            "response": full_response,
            "context": final_context
        }

    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return {
            "error": str(e),
            "response": "Sorry, I am having trouble connecting to the language model."
        }
