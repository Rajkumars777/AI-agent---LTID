import dspy

class ContentGeneration(dspy.Signature):
    """
    Generate high-quality text content based on a prompt.
    The content should be ready to be typed directly into an application (no markdown wrapping unless requested).
    """
    prompt = dspy.InputField(desc="The description of content to generate (e.g., 'about Japan', 'a python script for fibonacci')")
    content = dspy.OutputField(desc="The generated content string")

# Initialize Predictor
generator = dspy.Predict(ContentGeneration)

def generate_text_content(prompt: str) -> str:
    """
    Generates text content using the configured LM.
    """
    print(f"DEBUG: Generating content for prompt: '{prompt}'")
    try:
        # Refine prompt slightly for better direct output
        final_prompt = prompt
        if "about" in prompt.lower() and not "write" in prompt.lower():
             final_prompt = f"Write a short text {prompt}"
        
        prediction = generator(prompt=final_prompt)
        content = prediction.content
        
        # Clean up common artifacts
        if "Here is the" in content and ":" in content:
             # Heuristic: remove "Here is the text:" prefix if present
             parts = content.split(":", 1)
             if len(parts) > 1 and len(parts[0]) < 50:
                  content = parts[1].strip()
        
        # Remove Markdown code blocks if it's code but we want to type it
        if "```" in content:
            # If it's a code block, we usually want the code inside.
            import re
            match = re.search(r"```(?:\w+)?\n(.*?)```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()
                
        return content
    except Exception as e:
        print(f"Error generating content: {e}")
        return prompt # Fallback to literal
