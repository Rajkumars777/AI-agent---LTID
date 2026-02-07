import dspy
import os
from openai import OpenAI

class OpenRouterAdapter(dspy.LM):
    def __init__(self, model, api_key, api_base="https://openrouter.ai/api/v1", **kwargs):
        super().__init__(model=model)
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        self.provider = "openai"
        self.history = []
        self.kwargs = {
            "temperature": 0.0,
            "max_tokens": 1000,
            **kwargs
        }

    def basic_request(self, prompt, **kwargs):
        params = {**self.kwargs, **kwargs}
        
        # Remove DSPy specific args that OpenAPI doesn't accept if any
        # For now, just simplistic implementation
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **params
            )
            content = response.choices[0].message.content
            
            # AGGRESSIVE CLEANING
            # DSPy's Pydantic adapter is strict. If the LLM wraps in markdown, it crashes.
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                 content = content.split("```")[1].split("```")[0].strip()
            
            # Logging for debug
            self.history.append({
                "prompt": prompt,
                "response": content,
                "kwargs": params
            })
            
            return [content]
        except Exception as e:
            print(f"OpenRouter Error: {e}")
            return [""]

    def __call__(self, prompt=None, messages=None, **kwargs):
        # DSPy might call with 'prompt' OR 'messages' depending on the Predictor type.
        # We handle both.
        if messages:
            # Reconstruct prompt from messages if needed, or send messages directly
            # For simplicity, we just use the last user message as prompt if prompt is void
            # But wait, our basic_request expects prompt.
            # Let's inspect what we get.
            pass
            
        p = prompt if prompt else (messages[-1]['content'] if messages else "")
        return self.basic_request(p, **kwargs)
