import requests

def generate(text, model='gemma3:4b'):
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={'model': model, 'prompt': text, 'stream': False}
    )
    response.raise_for_status()
    data = response.json()
    return data

