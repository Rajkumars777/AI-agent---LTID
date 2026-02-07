from temporalio import workflow
from temporalio import activity
import asyncio

# Define an activity
@activity.defn
async def run_agent_activity(input_text: str) -> str:
    # In a real app, this would call the logic in agent.py
    # For now, we return a mock response
    print(f"Activity running for input: {input_text}")
    return f"Processed: {input_text}"

# Define the workflow
@workflow.defn
class AgentWorkflow:
    @workflow.run
    async def run(self, input_text: str) -> str:
        workflow.logger.info(f"Workflow execution started for: {input_text}")
        
        # Activity Options
        result = await workflow.execute_activity(
            run_agent_activity,
            input_text,
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        return result

from datetime import timedelta
