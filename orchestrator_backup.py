"""
orchestrator.py
================
Unified controller for all multi-step and adaptive tasks.
Eliminates redundancy by combining Planning (multistep_planner), 
Execution (multistep_executor), and Adaptive Fallbacks (ScreenAgent).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.execution.multistep_planner import plan_multistep
from src.core.execution.multistep_executor import execute_multistep_plan
from src.services.desktop.screen_agent import run_screen_task

logger = logging.getLogger(__name__)

class UnifiedOrchestrator:
    """
    Single point of entry for any task requiring more than a single tool call.
    """
    
    async def execute(self, query: str, task_id: str, emit_event: Any) -> Dict[str, Any]:
        """
        Executes a task by choosing the best path:
        0. Data Retrieval Task  -> handle_action('DYNAMIC_CODE') (Fast data path)
        1. Screen Pattern Match -> ScreenAgent (Fast Adaptive Path)
        2. Complex Multi-step   -> Planner -> Executor (Deterministic Path)
        3. Recovery             -> Adaptive Loop
        """
        logger.info(f"Orchestrating task: {query}")
        
        # 0. Data Retrieval Fast Path (stock data, market data + Excel creation)
        import re, os
        lower_query = query.lower()
        data_keywords = [
            "stock", "closing", "opening", "price", "retrieve", "fetch",
            "nikkei", "sensex", "nifty", "s&p", "dow", "nasdaq",
            "exchange rate", "currency rate", "gold price", "silver price",
            "crypto", "bitcoin", "market data", "share price",
            "stock average", "closing value", "opening value",
            "calculate", "standard deviation", "variance", "average", "total",
            "create a new excel", "create a pptx", "presentation", "powerpoint",
            "generate script", "excel", "xlsx", "csv", "cell", "column", 
            "row", "spreadsheet", "worksheet", "color", "format"
        ]

        import re
        is_data_task = any(re.search(r'\b' + re.escape(kw) + r'\b', lower_query) for kw in data_keywords)
        
        if is_data_task:
            logger.info("📊 Data retrieval task detected → routing to DYNAMIC_CODE handler")
            
            # Extract target filename from query
            file_match = re.search(r'\b(\w+\.(xlsx|xls|csv))\b', lower_query)
            target_file = file_match.group(1) if file_match else "stock_data.xlsx"
            
            # Resolve folder path
            user_home = os.path.expanduser("~")
            if "download" in lower_query:
                target_file = os.path.join(user_home, "Downloads", target_file)
            elif "desktop" in lower_query:
                target_file = os.path.join(user_home, "Desktop", target_file)
            elif "document" in lower_query:
                target_file = os.path.join(user_home, "Documents", target_file)
            else:
                target_file = os.path.join(user_home, "Downloads", target_file)
            
            if emit_event:
                await emit_event(task_id, "AgentStep", {"desc": f"📊 Retrieving data and creating {os.path.basename(target_file)}..."})
            
            from src.core.execution.handlers import handle_action
            result_pkg = await handle_action(
                action     = "DYNAMIC_CODE",
                target     = target_file,
                context    = query,  # Full query as task description
                user_input = query,
                task_id    = task_id,
            )
            
            content = result_pkg.get("result", "")
            if isinstance(content, dict):
                content = str(content)
                
            return {
                "success": "✅" in content or "Success" in content or "executed" in content.lower() or "Output" in content,
                "summary": content,
                "intermediate_steps": [{
                    "step_id": 1,
                    "action": "DYNAMIC_CODE",
                    "target": target_file,
                    "result": content,
                    "success": "❌" not in content,
                    "timestamp": datetime.now().isoformat()
                }]
            }

        # 0b. Web Task Fast Path (browse, search web, navigate to URL)
        web_keywords = [
            "http", "https", "www", ".com", ".org", ".net", ".io",
            "browser", "chrome", "edge", "brave", "firefox",
            "website", "webpage", "gmail", "youtube", "google",
            "search web", "search the web", "web search",
            "go to ", "navigate to", "visit ", "browse to",
            "wikipedia", "amazon", "facebook", "twitter", "reddit",
        ]
        has_url = bool(re.search(r'\b\w+\.(com|org|net|io|dev|edu|gov|co)\b', lower_query))
        is_web_task = has_url or any(re.search(r'\b' + re.escape(kw) + r'\b', lower_query) for kw in web_keywords)
        
        if is_web_task:
            logger.info("🌐 Web task detected → routing to fast WEB_CONTROL handler")
            
            if emit_event:
                await emit_event(task_id, "AgentStep", {"desc": f"🌐 Opening browser: {query}"})
            
            from src.core.execution.handlers import handle_action
            result_pkg = await handle_action(
                action     = "WEB_CONTROL",
                target     = query,
                context    = None,
                user_input = query,
                task_id    = task_id,
            )
            
            content = result_pkg.get("result", "")
            if isinstance(content, dict):
                content = str(content)
                
            return {
                "success": "✅" in content,
                "summary": content,
                "intermediate_steps": [{
                    "type":      "Action",
                    "content":   content,
                    "timestamp": datetime.now().strftime("%I:%M:%S %p"),
                    "tool":      result_pkg.get("tool_used", "Fast Browser Control"),
                    "success":   "❌" not in content,
                }]
            }

        # 1. Deterministic Planning (for non-data, non-web tasks)
        plan = await asyncio.to_thread(plan_multistep, query)
        
        if plan and len(plan.steps) > 1:
            logger.info(f"Executing deterministic plan with {len(plan.steps)} steps")
            results = await execute_multistep_plan(plan, task_id, emit_event)
            
            # Check for critical failures in the plan
            success_count = sum(1 for r in results if r.get("success"))
            if success_count < len(plan.steps):
                logger.warning("Deterministic plan partially failed. Falling back to ScreenAgent for recovery...")
                # Optional: Hand off remaining context to ScreenAgent
                
            return {
                "success": success_count == len(plan.steps),
                "summary": f"Completed {success_count}/{len(plan.steps)} steps",
                "intermediate_steps": results
            }
            
        # 2. Adaptive Fallback (or if single step is best handled visually)
        logger.info("No multi-step plan needed or plan too simple. Using ScreenAgent.")
        result_text = await run_screen_task(query, task_id, emit_event)
        
        return {
            "success": "✅" in result_text,
            "summary": result_text,
            "intermediate_steps": []
        }

orchestrator = UnifiedOrchestrator()
