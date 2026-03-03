import re

with open("src/core/intelligence/code_generator.py", "r", encoding="utf-8") as f:
    text = f.read()

fallback_func = """def _call_llm_fallback_chain(prompt: str) -> str:
    import os
    from dotenv import load_dotenv
    import dspy
    
    load_dotenv() # Ensure env vars are loaded
    code = ""
    
    # --- ATTEMPT 1: Gemini (Direct API) ---
    gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_err_msg = ""
    if gemini_key:
        print("DEBUG CodeGen: [Attempt 1] Trying Gemini API directly...", flush=True)
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=gemini_key,
            )
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            code = response.choices[0].message.content
            print(f"DEBUG CodeGen: Gemini generated code length={len(code) if code else 0}", flush=True)
        except Exception as g_err:
            gemini_err_msg = str(g_err)
            print(f"DEBUG CodeGen: Gemini direct call failed: {g_err}", flush=True)

    # --- ATTEMPT 2: OpenRouter (Direct API Fallback) ---
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_err_msg = ""
    if not code or len(code.strip()) < 10:
        print("DEBUG CodeGen: Gemini failed. [Attempt 2] Trying OpenRouter API...", flush=True)
        if openrouter_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
                response = client.chat.completions.create(
                    model="google/gemini-2.0-flash-001",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                code = response.choices[0].message.content
                print(f"DEBUG CodeGen: OpenRouter generated code length={len(code) if code else 0}", flush=True)
            except Exception as or_err:
                openrouter_err_msg = str(or_err)
                print(f"DEBUG CodeGen: OpenRouter direct call failed: {or_err}", flush=True)
        else:
            openrouter_err_msg = "OPENROUTER_API_KEY not found in environment."
    
    # --- ATTEMPT 3: Groq (Direct API Fallback 2) ---
    groq_err_msg = ""
    if not code or len(code.strip()) < 10:
        print("DEBUG CodeGen: OpenRouter failed. [Attempt 3] Trying Groq API...", flush=True)
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                code = response.choices[0].message.content
                print(f"DEBUG CodeGen: Groq generated code length={len(code) if code else 0}", flush=True)
            except Exception as groq_err:
                groq_err_msg = str(groq_err)
                print(f"DEBUG CodeGen: Groq API call failed: {groq_err}", flush=True)
        else:
            groq_err_msg = "GROQ_API_KEY not found in environment."

    # --- ATTEMPT 4: DSPy Default LM ---
    dspy_err_msg = ""
    if not code or len(code.strip()) < 10:
        print("DEBUG CodeGen: Groq failed. [Attempt 4] Trying DSPy LM instance...", flush=True)
        try:
            resp = dspy.settings.lm(prompt)
            if isinstance(resp, list):
                code = resp[0] if resp else ""
            else:
                code = str(resp)
            print(f"DEBUG CodeGen: DSPy LM generated code length={len(code) if code else 0}", flush=True)
        except Exception as lm_err:
            dspy_err_msg = str(lm_err)
            print(f"DEBUG CodeGen: DSPy LM failed: {lm_err}", flush=True)
    
    # --- FINAL CHECK ---
    if not code or len(code.strip()) < 10:
        return f"Error: ALL LLM fallback APIs failed to generate code.\\nOpenRouter Error: {openrouter_err_msg}\\nGroq Error: {groq_err_msg}\\nDSPy Error: {dspy_err_msg}"
        
    return code

def generate_and_run_script"""

text = text.replace("def generate_and_run_script", fallback_func)

old_fallback_block = text[text.find("            from dotenv import load_dotenv"):text.find("        # Clean Markdown if present")]
new_fallback_block = """            code = _call_llm_fallback_chain(direct_prompt)
            
            # --- FINAL CHECK ---
            if code.startswith("Error:"):
                return code\n\n"""

text = text.replace(old_fallback_block, new_fallback_block)

old_heal = """                prediction2 = generator(task=heal_task, file_path=file_path)
                code2 = prediction2.python_code"""

new_heal = """                try:
                    prediction2 = generator(task=heal_task, file_path=file_path)
                    code2 = prediction2.python_code
                except Exception as e:
                    code2 = ""
                    
                if not code2 or len(code2.strip()) < 10:
                    heal_prompt = f"Write a complete Python script to fix this error:\\n\\nTASK: {heal_task}\\n\\nFILE PATH: {file_path}\\n\\nRULES:\\n- Output ONLY valid Python code, no markdown, no explanation\\n- Include all imports\\n- ❗ CRITICAL: Explicitly open modified files at the end using `os.startfile('{file_path}')`.\\n\\nPython code:"
                    code2 = _call_llm_fallback_chain(heal_prompt)"""

text = text.replace(old_heal, new_heal)

with open("src/core/intelligence/code_generator.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Patch applied to code_generator.py")
