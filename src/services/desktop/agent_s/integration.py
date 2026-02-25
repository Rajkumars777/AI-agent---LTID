"""
src/services/desktop/agent_s/integration.py
==========================================
Integration layer for Agent-S (gui-agents) framework.
Version: OpenAI-Free (Groq + OpenRouter)
Adapted for gui-agents v0.1.3
"""

import os
import time
import asyncio
import pyautogui
import logging
import json
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Setup Logging
logger = logging.getLogger("AgentS-Integration")

# ============================================================
#  MONKEY-PATCHING: OpenAI-Free Workarounds
# ============================================================

def apply_openai_free_patches():
    """
    Patches gui-agents to remove hard dependencies on OpenAI API.
    """
    try:
        from gui_agents.mllm.MultimodalEngine import OpenAIEmbeddingEngine, LMMEnginevLLM, LMMEngineOpenAI
        from gui_agents.mllm.MultimodalAgent import LMMAgent
        import gui_agents.mllm.MultimodalEngine as m_engine
        import gui_agents.utils.common_utils as common_utils
        from openai import OpenAI
        import re

        # 1. Patch Embedding Engine (No OpenAI Key needed)
        def patched_embedding_init(self, api_key=None, rate_limit=-1, display_cost=True):
            self.model = "mock-embedding"
            self.api_key = "mock-key"
            self.display_cost = False
            self.cost_per_thousand_tokens = 0
            self.request_interval = 0
            logger.info("[Agent-S] Mocked OpenAIEmbeddingEngine initialized.")

        def patched_get_embeddings(self, text: str) -> np.ndarray:
            return np.zeros((1, 1536))

        OpenAIEmbeddingEngine.__init__ = patched_embedding_init
        OpenAIEmbeddingEngine.get_embeddings = patched_get_embeddings

        # 2. Patch LMMEngineOpenAI to avoid Key Error on init
        def patched_openai_engine_init(self, api_key=None, model=None, rate_limit=-1, **kwargs):
            self.api_key = api_key or "mock-key"
            self.model = model or "gpt-4"
            logger.debug(f"[Agent-S] LMMEngineOpenAI shimmed for model {self.model}")

        LMMEngineOpenAI.__init__ = patched_openai_engine_init

        # 3. Patch LMMAgent to force 'vllm' type if it's 'openai'
        # This ensures internal knowledge base agents use our smart router
        original_lmm_agent_init = LMMAgent.__init__
        def patched_lmm_agent_init(self, engine_params=None, system_prompt=None, engine=None):
            if engine is None and engine_params is not None:
                etype = engine_params.get("engine_type")
                if etype == "openai" or etype is None:
                    # Upgrade to vllm to hit our smart generator
                    engine_params["engine_type"] = "vllm"
                    engine_params["base_url"] = "http://smart-router"
            original_lmm_agent_init(self, engine_params, system_prompt, engine)

        LMMAgent.__init__ = patched_lmm_agent_init

        # 4. Patch parse_dag to be more robust
        def patched_parse_dag(text):
            if not text: return None
            # Try to find content between <json> tags
            pattern = r"<json>(.*?)</json>"
            match = re.search(pattern, text, re.DOTALL)
            json_str = match.group(1) if match else text
            
            # Clean up markdown code blocks
            json_str = re.sub(r"```json\s*", "", json_str)
            json_str = re.sub(r"```\s*", "", json_str)
            json_str = json_str.strip()
            
            def repair_json(s):
                # Basic repairs for common LLM mistakes
                s = s.replace('\n', ' ')
                s = re.sub(r',\s*([\]}])', r'\1', s) # Remove trailing commas
                # Ensure all keys are quoted if they are not
                s = re.sub(r'(\w+):', r'"\1":', s) 
                return s

            try:
                # First try direct parse
                json_data = json.loads(json_str)
            except Exception:
                try:
                    # Second try with repair
                    json_data = json.loads(repair_json(json_str))
                except Exception as e:
                    print(f"[Agent-S] JSON Parse Error: {e}")
                    print(f"[Agent-S] Attempted to parse: {json_str[:200]}...")
                    return None
            
            try:
                # If it's just the nodes/edges without 'dag', wrap it
                if "nodes" in json_data and "edges" in json_data and "dag" not in json_data:
                    json_data = {"dag": json_data}
                
                from gui_agents.utils.common_utils import Dag
                return Dag(**json_data["dag"])
            except Exception as e:
                print(f"[Agent-S] Dag Validation Error: {e}")
                return None

        m_engine.parse_dag = patched_parse_dag
        common_utils.parse_dag = patched_parse_dag

        # 5. The Smart Router (Central Routing Point)
        def patched_smart_generate(self, messages, temperature=0.0, top_p=0.8, repetition_penalty=1.05, max_new_tokens=512, **kwargs):
            groq_key = os.getenv("GROQ_API_KEY")
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            
            has_image = False
            cleaned_messages = []
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", [])
                new_content = []
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "image_url":
                                has_image = True
                                new_content.append(item)
                            elif item.get("type") == "text":
                                new_content.append(item)
                elif isinstance(content, str):
                    new_content = content
                cleaned_messages.append({"role": role, "content": new_content})

            if has_image:
                try:
                    client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
                    model = os.getenv("VISION_MODEL", "qwen/qwen2.5-vl-7b-instruct:free")
                    logger.info(f"[Agent-S] Routing Vision to OpenRouter: {model}")
                    completion = client.chat.completions.create(
                        model=model, messages=messages, temperature=temperature, top_p=top_p,
                        max_tokens=max_new_tokens if max_new_tokens else 4096
                    )
                    return completion.choices[0].message.content
                except Exception as e:
                    logger.warning(f"[Agent-S] OpenRouter failed, trying local Ollama: {e}")
                    try:
                        client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
                        completion = client.chat.completions.create(
                            model="qwen2.5-vl", 
                            messages=messages, temperature=temperature,
                            max_tokens=max_new_tokens if max_new_tokens else 4096
                        )
                        return completion.choices[0].message.content
                    except Exception as e2:
                        logger.error(f"[Agent-S] All vision fallbacks failed.")
                        raise e
            else:
                # Reasoning via Groq with OpenRouter and Local Fallback
                try:
                    client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
                    model = os.getenv("PLANNING_MODEL", "llama-3.3-70b-versatile")
                    logger.info(f"[Agent-S] Routing Reasoning to Groq: {model}")
                    
                    target_messages = []
                    for msg in cleaned_messages:
                        content = msg["content"]
                        if isinstance(content, list):
                            text_parts = [item.get("text", "") for item in content if item.get("type") == "text"]
                            simplified_content = "\n".join(text_parts).strip()
                            if not simplified_content: simplified_content = "Please continue."
                        else:
                            simplified_content = content
                        target_messages.append({"role": msg["role"], "content": simplified_content})

                    completion = client.chat.completions.create(
                        model=model, messages=target_messages, temperature=temperature, top_p=top_p,
                        max_tokens=max_new_tokens if max_new_tokens else 4096
                    )
                    return completion.choices[0].message.content
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e) or "401" in str(e):
                        print(f"[Agent-S] Groq/Auth Error ({e}). Trying OpenRouter Fallback...")
                        try:
                            client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
                            model = os.getenv("PLANNING_MODEL", "llama-3.3-70b-versatile")
                            completion = client.chat.completions.create(
                                model=f"meta-llama/{model}" if "/" not in model else model,
                                messages=target_messages, temperature=temperature,
                                max_tokens=max_new_tokens if max_new_tokens else 4096
                            )
                            return completion.choices[0].message.content
                        except Exception as e2:
                            print(f"[Agent-S] OpenRouter failed ({e2}), trying local Ollama for Reasoning...")
                            try:
                                # Fallback to local Ollama
                                client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
                                completion = client.chat.completions.create(
                                    model="qwen2.5-vl", 
                                    messages=target_messages, temperature=temperature,
                                    max_tokens=max_new_tokens if max_new_tokens else 4096
                                )
                                print(f"[Agent-S] Using local Ollama successfully.")
                                return completion.choices[0].message.content
                            except Exception as e3:
                                print(f"[Agent-S] All reasoning fallbacks failed: {e3}")
                                raise e
                    raise e

        LMMEnginevLLM.generate = patched_smart_generate
        logger.info("[Agent-S] Full OpenAI-Free Monkey-Patch Applied.")

    except Exception as e:
        logger.error(f"[Agent-S] Critical patching failure: {e}")

# Apply patches immediately
apply_openai_free_patches()

# Apply patches immediately
apply_openai_free_patches()

# ============================================================
#  Agent-S Loop Implementation
# ============================================================

class AgentSLoop:
    def __init__(self, emit_event: Optional[Callable] = None):
        self.emit = emit_event
        self.agent = None
        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return True
        
        try:
            from gui_agents.core.AgentS import GraphSearchAgent
            from gui_agents.aci.WindowsOSACI import WindowsACI

            # Dummy engine params to satisfy constructor
            # The actual logic is handled by our smart_generate patch
            engine_params = {
                "engine_type": "vllm", 
                "model": "router-active",
                "api_key": "patched-out",
                "base_url": "patched-out"
            }

            # Windows grounding agent
            grounding_agent = WindowsACI(top_app_only=True, ocr=False)

            self.agent = GraphSearchAgent(
                engine_params=engine_params,
                grounding_agent=grounding_agent,
                platform="windows",
                action_space="pyatuogui", # Note: intentional typo in 0.1.3 source
                observation_type="mixed",
                search_engine="LLM"
            )
            
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"[Agent-S] Initialization failure: {e}")
            return False

    async def run(self, task: str, emit: Optional[Callable] = None, max_steps: int = 15) -> str:
        if not self._initialized:
            if not self._initialize():
                return "❌ Agent-S failed to initialize (check API keys or dependencies)"

        if emit:
            self.emit = emit

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 1.0

        logger.info(f"Starting Task: {task}")
        
        for step in range(1, max_steps + 1):
            if self.emit:
                await self.emit("AgentStep", {"step": step, "desc": f"Agent-S thinking (Step {step})..."})
            
            print(f"[Agent-S] Step {step} thinking...")

            try:
                # Capture screen for observation
                screenshot = pyautogui.screenshot()
                import io
                buffered = io.BytesIO()
                screenshot.save(buffered, format="PNG")
                screenshot_bytes = buffered.getvalue()

                obs = {
                    "screenshot": screenshot_bytes,
                    "accessibility_tree": "" # Populated by WindowsACI internal logic
                }

                # Run prediction in executor to avoid blocking async loop
                loop = asyncio.get_event_loop()
                info, actions = await loop.run_in_executor(
                    None, 
                    lambda: self.agent.predict(instruction=task, observation=obs)
                )

                if "DONE" in actions:
                    logger.info("Task status: DONE")
                    return f"✅ Task completed successfully in {step} steps."
                
                if "FAIL" in actions:
                    logger.warning("Task status: FAIL")
                    return f"❌ Agent failed to complete the task at step {step}."

                for action_code in actions:
                    if action_code and action_code not in ["WAIT", "DONE", "FAIL"]:
                        print(f"[Agent-S] Executing: {action_code}")
                        if self.emit:
                            await self.emit("AgentStepDone", {"step": step, "action": action_code})
                        
                        # Execute the generated PyAutoGUI code
                        exec(action_code)
                
                await asyncio.sleep(1.0) # Stability delay

            except KeyboardInterrupt:
                return "⛔ Task stopped by user."
            except Exception as e:
                logger.error(f"[Agent-S] Error at step {step}: {e}")
                if "failsafe" in str(e).lower():
                    return "⛔ Agent-S stopped by failsafe (mouse moved to corner)"
                continue

        return f"⚠️ Agent-S reached max steps ({max_steps}). Task may be incomplete."
