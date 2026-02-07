import dspy
import google.generativeai as genai
import os

class GeminiAdapter(dspy.LM):
    def __init__(self, model_name="gemini-2.0-flash", api_key=None, **kwargs):
        super().__init__(model=model_name)
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        
        genai.configure(api_key=api_key)
        self.genai_model = genai.GenerativeModel(model_name)
        self.kwargs = kwargs

    def basic_request(self, prompt, **kwargs):
        # Merge kwargs with default
        config = self.kwargs.copy()
        config.update(kwargs)
        
        # Extract known parameters
        temperature = config.pop('temperature', 0.0)
        max_tokens = config.pop('max_tokens', 4000)
        
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens
        )
        
        try:
            # DSPy prompts are often chat-like strings.
            # We just send it as text.
            response = self.genai_model.generate_content(prompt, generation_config=generation_config)
            
            # DSPy expects a list of completions
            if response.text:
                return [response.text]
            else:
                return [""]
        except Exception as e:
            print(f"Gemini Adapter Error: {e}")
            # Try to print feedback if blocked
            if hasattr(e, 'feedback'):
                print(f"Feedback: {e.feedback}")
            return [""]

    def __call__(self, prompt, only_completed=True, return_sorted=False, **kwargs):
        # DSPy calls this
        completions = self.basic_request(prompt, **kwargs)
        return completions
