"""
Agent LLM System
================
Specialized LLM prompts and signatures for autonomous agent reasoning.
Handles task planning, element discovery, data extraction, and decision making.
"""

import dspy
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Models for Structured Outputs
# ============================================================================

class AgentStep(BaseModel):
    """A single step in a task plan"""
    step_number: int
    action: str  # navigate, search, click, extract, filter, compare, etc.
    target: str  # URL, element description, or data field
    parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str
    required_data: List[str] = Field(default_factory=list)  # Data needed from previous steps
    
    
class ConditionalBranch(BaseModel):
    """A conditional execution branch"""
    condition: str  # e.g., "price < 50000"
    condition_field: str  # e.g., "price"
    operator: str  # <, >, ==, !=, contains
    value: Any
    action_if_true: List[str]
    action_if_false: List[str]


class TaskPlan(BaseModel):
    """Complete execution plan for a task"""
    goal: str
    task_type: str  # simple, multi_step, conditional, comparison
    steps: List[AgentStep]
    conditionals: List[ConditionalBranch] = Field(default_factory=list)
    extraction_targets: List[str] = Field(default_factory=list)
    estimated_complexity: int  # 1-10
    

# ============================================================================
# DSPy Signatures for Agent Reasoning
# ============================================================================

class TaskPlanner(dspy.Signature):
    """
    Plan a web automation task by decomposing it into executable steps.
    
    Examples:
    - "Go to Amazon and search iPhone 15" → [Navigate(amazon.in), Search("iPhone 15")]
    - "Find cheapest laptop under 50k" → [Navigate, Search, Filter(price<50k), Sort(low-to-high), Extract(price)]
    - "Compare iPhone price on Amazon vs Flipkart" → [Navigate(Amazon), Search, Extract(price), Navigate(Flipkart), Search, Extract(price), Compare]
    - "Click the 'Submit' button on the screen" → [ClickText("Submit")]
    - "Type 'Hello' into the active window" → [TypeDesktop("Hello")]
    - "Read the text from the screen" → [ReadScreen]
    """
    goal: str = dspy.InputField(desc="User's natural language goal")
    current_context: str = dspy.InputField(desc="Current state: URL, extracted data, etc.")
    
    task_type: str = dspy.OutputField(desc="Type: simple, multi_step, conditional, comparison")
    steps: str = dspy.OutputField(desc="JSON list of steps with action, target, parameters")
    reasoning: str = dspy.OutputField(desc="Why this plan will achieve the goal")


class ElementLocator(dspy.Signature):
    """
    Analyze page structure and find the best CSS selector for a target element.
    
    Given simplified HTML structure, identify the element and provide a robust selector.
    Prefer selectors that are: semantic, stable (not auto-generated), and specific.
    """
    page_structure: str = dspy.InputField(desc="Simplified HTML with key elements, IDs, classes")
    element_description: str = dspy.InputField(desc="What to find: 'search button', 'price', 'first product'")
    
    selector: str = dspy.OutputField(desc="CSS selector (e.g., '#search-btn', '.product-price')")
    selector_type: str = dspy.OutputField(desc="Type: id, class, attribute, text, semantic")
    confidence: str = dspy.OutputField(desc="High, Medium, Low")
    reasoning: str = dspy.OutputField(desc="Why this selector is best")


class DataExtractor(dspy.Signature):
    """
    Extract specific information from HTML/text content.
    
    Handle various data types: prices, ratings, text, dates, numbers.
    Return clean, normalized values.
    """
    content: str = dspy.InputField(desc="HTML snippet or text containing the data")
    query: str = dspy.InputField(desc="What to extract: 'price of first product', 'rating', 'title'")
    
    extracted_value: str = dspy.OutputField(desc="The extracted value, cleaned and normalized")
    data_type: str = dspy.OutputField(desc="price, rating, text, number, date")
    confidence: str = dspy.OutputField(desc="High, Medium, Low")


class ConditionEvaluator(dspy.Signature):
    """
    Evaluate a condition based on extracted data.
    
    Example: "price < 50000" with price="₹45,000" → True
    """
    condition: str = dspy.InputField(desc="Condition to evaluate: 'price < 50000', 'rating > 4'")
    context: str = dspy.InputField(desc="Available data as JSON: {'price': 45000, 'rating': 4.5}")
    
    result: str = dspy.OutputField(desc="true or false")
    extracted_value: str = dspy.OutputField(desc="The value used in evaluation")
    reasoning: str = dspy.OutputField(desc="How the condition was evaluated")


class ActionVerifier(dspy.Signature):
    """
    Verify if an action succeeded by analyzing the result.
    
    Can use page title, visible text, URL changes, or screenshot descriptions.
    """
    action_attempted: str = dspy.InputField(desc="What action was attempted: 'search iPhone', 'click first product'")
    current_state: str = dspy.InputField(desc="Current page: URL, title, key visible text")
    expected_outcome: str = dspy.InputField(desc="What should happen: 'search results shown', 'product page opened'")
    
    success: str = dspy.OutputField(desc="yes or no")
    confidence: str = dspy.OutputField(desc="High, Medium, Low")
    reasoning: str = dspy.OutputField(desc="Evidence for success/failure")


class ErrorRecoveryPlanner(dspy.Signature):
    """
    Generate alternative approaches when an action fails.
    
    Suggest fallback strategies based on error type and context.
    """
    original_action: str = dspy.InputField(desc="The action that failed")
    error: str = dspy.InputField(desc="Error message or failure description")
    page_state: str = dspy.InputField(desc="Current page state")
    
    recovery_strategy: str = dspy.OutputField(desc="What to try next")
    alternative_selectors: str = dspy.OutputField(desc="JSON list of alternative element selectors to try")
    should_retry: str = dspy.OutputField(desc="yes or no - whether to retry or give up")


class SemanticPageAnalyzer(dspy.Signature):
    """
    Analyze a page to understand its structure and content semantically.
    
    Identify key areas: search, filters, results, product details, forms, etc.
    """
    page_html: str = dspy.InputField(desc="Simplified HTML structure of the page")
    goal: str = dspy.InputField(desc="What the user wants to accomplish")
    
    page_type: str = dspy.OutputField(desc="search_results, product_page, form, listing, other")
    key_elements: str = dspy.OutputField(desc="JSON dict of important elements: {'search_box': '...', 'results': '...'}")
    suggestions: str = dspy.OutputField(desc="Suggested next actions based on goal")


# ============================================================================
# Predictor Instances
# ============================================================================

task_planner = dspy.Predict(TaskPlanner)
element_locator = dspy.Predict(ElementLocator)
data_extractor = dspy.Predict(DataExtractor)
condition_evaluator = dspy.Predict(ConditionEvaluator)
action_verifier = dspy.Predict(ActionVerifier)
error_recovery_planner = dspy.Predict(ErrorRecoveryPlanner)
semantic_page_analyzer = dspy.Predict(SemanticPageAnalyzer)


# ============================================================================
# Helper Functions
# ============================================================================

def plan_task(goal: str, context: str = "") -> TaskPlan:
    """
    Plan a web automation task using LLM reasoning.
    
    Args:
        goal: User's natural language goal
        context: Current state (URL, extracted data, etc.)
    
    Returns:
        TaskPlan with structured steps
    """
    import json
    
    try:
        prediction = task_planner(goal=goal, current_context=context or "Starting fresh")
        
        # Parse steps
        steps_data = []
        try:
            steps_raw = prediction.steps
            # Handle markdown code blocks
            if "```" in steps_raw:
                steps_raw = steps_raw.split("```")[1].strip()
                if steps_raw.startswith("json"):
                    steps_raw = steps_raw[4:].strip()
            
            steps_list = json.loads(steps_raw)
            for i, step_dict in enumerate(steps_list):
                steps_data.append(AgentStep(
                    step_number=i + 1,
                    action=step_dict.get("action", "unknown"),
                    target=step_dict.get("target", ""),
                    parameters=step_dict.get("parameters", {}),
                    expected_outcome=step_dict.get("expected_outcome", ""),
                    required_data=step_dict.get("required_data", [])
                ))
        except Exception as e:
            print(f"[AgentLLM] Error parsing steps: {e}")
            # Fallback: simple single-step plan
            steps_data = [AgentStep(
                step_number=1,
                action="execute",
                target=goal,
                parameters={},
                expected_outcome="Task completed"
            )]
        
        plan = TaskPlan(
            goal=goal,
            task_type=prediction.task_type or "simple",
            steps=steps_data,
            extraction_targets=[],
            estimated_complexity=len(steps_data)
        )
        
        print(f"[AgentLLM] Planned {len(plan.steps)} steps for: {goal}")
        return plan
        
    except Exception as e:
        print(f"[AgentLLM] Task planning failed: {e}")
        # Return minimal plan
        return TaskPlan(
            goal=goal,
            task_type="simple",
            steps=[AgentStep(
                step_number=1,
                action="execute",
                target=goal,
                parameters={},
                expected_outcome="Complete the goal"
            )],
            extraction_targets=[],
            estimated_complexity=1
        )


def find_element(page_html: str, element_description: str) -> Optional[str]:
    """
    Find element selector using LLM analysis.
    
    Args:
        page_html: Simplified page structure
        element_description: What to find
    
    Returns:
        CSS selector or None
    """
    try:
        # Simplify HTML to reduce token usage
        simplified = _simplify_html(page_html)
        
        prediction = element_locator(
            page_structure=simplified,
            element_description=element_description
        )
        
        if prediction.confidence.lower() in ["high", "medium"]:
            print(f"[AgentLLM] Found element: {prediction.selector} ({prediction.confidence} confidence)")
            return prediction.selector
        else:
            print(f"[AgentLLM] Low confidence for element: {element_description}")
            return None
            
    except Exception as e:
        print(f"[AgentLLM] Element location failed: {e}")
        return None


def extract_data_from_content(content: str, query: str) -> Optional[str]:
    """
    Extract specific data from HTML/text using LLM.
    
    Args:
        content: HTML or text content
        query: What to extract
    
    Returns:
        Extracted value or None
    """
    try:
        prediction = data_extractor(content=content[:2000], query=query)  # Limit content size
        
        if prediction.confidence.lower() in ["high", "medium"]:
            print(f"[AgentLLM] Extracted: {prediction.extracted_value} ({prediction.data_type})")
            return prediction.extracted_value
        else:
            return None
            
    except Exception as e:
        print(f"[AgentLLM] Data extraction failed: {e}")
        return None


def verify_action(action: str, page_state: str, expected: str) -> bool:
    """
    Verify if an action succeeded.
    
    Args:
        action: Action attempted
        page_state: Current page state
        expected: Expected outcome
    
    Returns:
        True if successful
    """
    try:
        prediction = action_verifier(
            action_attempted=action,
            current_state=page_state,
            expected_outcome=expected
        )
        
        success = prediction.success.lower() in ["yes", "true"]
        print(f"[AgentLLM] Action verification: {success} ({prediction.reasoning})")
        return success
        
    except Exception as e:
        print(f"[AgentLLM] Verification failed: {e}")
        return False


def _simplify_html(html: str, max_length: int = 3000) -> str:
    """Simplify HTML to reduce token usage while preserving structure"""
    # Remove scripts, styles, comments
    import re
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    
    # Trim to max length
    if len(html) > max_length:
        html = html[:max_length] + "... [truncated]"
    
    return html
