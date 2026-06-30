import os
import json
from groq import Groq

def _get_groq_client():
    api_key = os.getenv('GROQ_API_KEY')
    return Groq(api_key=api_key)

def llm_json_call(system_prompt: str, user_prompt: str) -> dict:
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"LLM JSON Error: {e}")
        return {}

def llm_text_call(system_prompt: str, user_prompt: str) -> str:
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM Text Error: {e}")
        return ""