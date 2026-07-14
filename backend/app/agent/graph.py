import os
import re
from typing import Annotated, Sequence, TypedDict, Optional, List, Dict, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

from app.config import settings
from app import schemas
from app.agent.prompts import SYSTEM_PROMPT, GENERATOR_PROMPT
from app.agent.tools import (
    log_interaction_tool,
    edit_interaction_tool,
    get_hcp_context_tool,
    search_interactions_tool,
    suggest_follow_up_tool,
    manage_samples_and_materials_tool
)

# 1. Define Agent State Schema
class AgentState(TypedDict):
    messages: List[BaseMessage]
    current_interaction_id: Optional[int]
    hcp_context: Optional[Dict[str, Any]]
    form_data: Optional[Dict[str, Any]]
    tool_outputs: List[Dict[str, Any]]
    response: Optional[str]
    error: Optional[str]

# Bind tools
tools_list = [
    log_interaction_tool,
    edit_interaction_tool,
    get_hcp_context_tool,
    search_interactions_tool,
    suggest_follow_up_tool,
    manage_samples_and_materials_tool
]

tool_map = {t.name: t for t in tools_list}

# Initialize Groq LLM (Safe setup)
llm = None
if settings.GROQ_API_KEY:
    try:
        llm = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.0
        )
    except Exception as e:
        print(f"Warning: Failed to initialize ChatGroq: {e}")
        llm = None

# Helper to format contextual system prompt with local time
def get_system_prompt():
    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{SYSTEM_PROMPT}\n\nCurrent Local Time Context: {curr_time}\n"

# 2. Define Router Node
def router_node(state: AgentState) -> Dict[str, Any]:
    if not llm:
        # Fall back directly if LLM is not configured
        return {"error": "LLM not initialized"}
        
    messages = [SystemMessage(content=get_system_prompt())] + state["messages"]
    
    # Add active interaction context to prompt if available
    if state.get("current_interaction_id"):
        messages.append(SystemMessage(
            content=f"Context: The currently active interaction ID in the session is #{state['current_interaction_id']}."
        ))
        
    try:
        llm_with_tools = llm.bind_tools(tools_list)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    except Exception as e:
        print(f"Groq API Error in router: {e}")
        return {"error": str(e)}

# 3. Define Tool Executor Node
def tool_executor_node(state: AgentState) -> Dict[str, Any]:
    last_msg = state["messages"][-1]
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return {}
        
    new_messages = []
    tool_outputs = list(state.get("tool_outputs") or [])
    form_data = state.get("form_data")
    hcp_context = state.get("hcp_context")
    current_id = state.get("current_interaction_id")
    
    for tool_call in last_msg.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call.get("id")
        
        # Inject active interaction id to edit tool if missing from LLM args
        if tool_name == "edit_interaction" and "interaction_id" not in tool_args and current_id:
            tool_args["interaction_id"] = current_id
            
        print(f"Executing tool {tool_name} with arguments: {tool_args}")
        
        if tool_name in tool_map:
            try:
                # Invoke the tool
                res = tool_map[tool_name].invoke(tool_args)
                
                # Log execution output
                tool_outputs.append({
                    "name": tool_name,
                    "args": tool_args,
                    "status": res.get("status", "success"),
                    "result": res.get("message", "Executed successfully.")
                })
                
                # Check tool actions to update state
                if res.get("status") == "success":
                    if tool_name in ["log_interaction", "edit_interaction"]:
                        form_data = res.get("data")
                        current_id = res.get("interaction_id")
                    elif tool_name == "get_hcp_context":
                        hcp_context = res.get("data")
                
                # Create ToolMessage response
                t_msg = ToolMessage(
                    content=str(res),
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                new_messages.append(t_msg)
            except Exception as e:
                tool_outputs.append({
                    "name": tool_name,
                    "args": tool_args,
                    "status": "error",
                    "result": str(e)
                })
                new_messages.append(ToolMessage(
                    content=f"Error executing tool: {e}",
                    tool_call_id=tool_call_id,
                    name=tool_name
                ))
        else:
            new_messages.append(ToolMessage(
                content=f"Error: Tool '{tool_name}' not found.",
                tool_call_id=tool_call_id,
                name=tool_name
            ))
            
    return {
        "messages": new_messages,
        "tool_outputs": tool_outputs,
        "form_data": form_data,
        "hcp_context": hcp_context,
        "current_interaction_id": current_id
    }

# 4. Define Response Generator Node
def generator_node(state: AgentState) -> Dict[str, Any]:
    if state.get("error") or not llm:
        # If there was an error in router or LLM is missing, do rule-based summary
        return {}
        
    messages = [
        SystemMessage(content=GENERATOR_PROMPT),
        SystemMessage(content=f"Current active interaction context: ID #{state.get('current_interaction_id')}")
    ] + state["messages"]
    
    try:
        response = llm.invoke(messages)
        return {"response": response.content}
    except Exception as e:
        print(f"Groq API Error in generator: {e}")
        return {"error": str(e)}

# 5. Conditional Routing Logic
def route_after_router(state: AgentState):
    if state.get("error"):
        return "generator"
        
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "generator"

# 6. Build the Graph
workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("tools", tool_executor_node)
workflow.add_node("generator", generator_node)

workflow.set_entry_point("router")

workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "tools": "tools",
        "generator": "generator"
    }
)

workflow.add_edge("tools", "generator")
workflow.add_edge("generator", END)

# Compile Graph
compiled_graph = workflow.compile()


# 7. Fallback Regex/Rule-Based Engine (Double-Defensive Programming)
def run_rule_based_fallback(message: str, current_id: Optional[int]) -> Dict[str, Any]:
    """
    Acts as a fully deterministic fallback agent in case the Groq API fails
    or the GROQ_API_KEY environment variable is empty.
    Calls the exact same database tools transactionally.
    """
    print("Falling back to rule-based parser engine...")
    msg_lower = message.lower()
    
    tool_outputs = []
    form_data = None
    hcp_context = None
    new_active_id = current_id
    conversational_response = ""
    
    # Check Intent 1: Get HCP Context
    # Matches queries like "Dr. Sharma", "Dr. Sarah Jenkins", "hcp profile Dr. Sharma"
    hcp_match = re.search(r"(dr\.\s+[a-zA-Z]+|dr\s+[a-zA-Z]+)", msg_lower)
    
    # 1. Log Interaction (Check first to prevent sample/brochure keywords from stealing the intent)
    if "met" in msg_lower or "log" in msg_lower or "visited" in msg_lower or "visit" in msg_lower or "discussed" in msg_lower:
        print("Fallback Match: log_interaction")
        # Extract HCP
        hcp_name = "Dr. Rajesh Sharma"  # Default
        if "jenkins" in msg_lower:
            hcp_name = "Dr. Sarah Jenkins"
        elif "patel" in msg_lower:
            hcp_name = "Dr. Amit Patel"
            
        # Extract Product
        products = ["CardioFlow 10mg"]
        if "oncoboost" in msg_lower:
            products = ["OncoBoost 50mg"]
        elif "glycastop" in msg_lower:
            products = ["GlycaStop 5mg"]
            
        # Extract Sentiment
        sentiment = "Positive"
        if "neutral" in msg_lower:
            sentiment = "Neutral"
        elif "negative" in msg_lower:
            sentiment = "Negative"
            
        # Extract Materials
        materials = []
        if "brochure" in msg_lower or "guide" in msg_lower or "cardiology" in msg_lower:
            materials.append("Cardiology Patient Guide")
        if "trial" in msg_lower or "oncoboost phase" in msg_lower:
            materials.append("OncoBoost Phase III Trial Report")
        if "prescribing" in msg_lower or "glycastop prescribing" in msg_lower:
            materials.append("GlycaStop Prescribing Information")
            
        # Extract Samples
        samples = []
        # Look for numbers near "sample"
        qty_match = re.search(r"(\d+)\s+sample", msg_lower)
        qty = 2 # default
        if qty_match:
            qty = int(qty_match.group(1))
            
        if "cardioflow" in msg_lower or "cardio" in msg_lower:
            samples.append({"name": "CardioFlow 10mg Sample Pack", "quantity": qty})
        elif "oncoboost" in msg_lower or "onco" in msg_lower:
            samples.append({"name": "OncoBoost 50mg Sample Pack", "quantity": qty})
        elif "glycastop" in msg_lower or "glyca" in msg_lower:
            samples.append({"name": "GlycaStop 5mg Starter Kit", "quantity": qty})
            
        args = {
            "hcp_name": hcp_name,
            "interaction_type": "Meeting",
            "topics_discussed": f"Discussed efficacy, benefits, and study report for {products[0]}.",
            "observed_sentiment": sentiment,
            "products": products,
            "materials": materials,
            "samples": samples,
            "follow_up_actions": "Schedule follow up task."
        }
        
        res = log_interaction_tool.invoke(args)
        tool_outputs.append({
            "name": "log_interaction",
            "args": args,
            "status": res["status"],
            "result": res["message"]
        })
        
        if res["status"] == "success":
            form_data = res["data"]
            new_active_id = res["interaction_id"]
            conversational_response = (
                f"I parsed your note offline! Logged a Meeting with {hcp_name}. "
                f"Discussed {products[0]}, sentiment set to {sentiment}, shared {materials[0] if materials else 'no materials'}, "
                f"distributed {qty} samples, and saved to database. The details are loaded in the form."
            )
        else:
            conversational_response = f"I tried logging the interaction, but the database returned an error: {res['message']}"

    # 2. Edit Interaction
    elif "change" in msg_lower or "edit" in msg_lower or "actually" in msg_lower or "update" in msg_lower:
        print("Fallback Match: edit_interaction")
        updates = {}
        if "neutral" in msg_lower:
            updates["observed_sentiment"] = "Neutral"
        elif "positive" in msg_lower:
            updates["observed_sentiment"] = "Positive"
        elif "negative" in msg_lower:
            updates["observed_sentiment"] = "Negative"
            
        if "topics" in msg_lower or "discuss" in msg_lower:
            updates["topics_discussed"] = "Updated discussion points."
            
        # Parse follow up change
        if "follow up" in msg_lower or "follow-up" in msg_lower:
            if "competitor" in msg_lower or "pricing" in msg_lower:
                updates["follow_up_actions"] = "Check competitor pricing"
            else:
                updates["follow_up_actions"] = "Follow up action updated conversationally."
            
        res = edit_interaction_tool.invoke({
            "interaction_id": current_id,
            "observed_sentiment": updates.get("observed_sentiment"),
            "topics_discussed": updates.get("topics_discussed"),
            "follow_up_actions": updates.get("follow_up_actions")
        })
        
        tool_outputs.append({
            "name": "edit_interaction",
            "args": {"interaction_id": current_id, **updates},
            "status": res["status"],
            "result": res["message"]
        })
        
        if res["status"] == "success":
            form_data = res["data"]
            new_active_id = res["interaction_id"]
            fields_str = ", ".join([f"{k} to '{v}'" for k, v in updates.items()])
            conversational_response = f"I've updated the active interaction #{new_active_id} by setting {fields_str}. The form is updated."
        else:
            conversational_response = f"Could not update interaction: {res['message']}"

    # 3. Profile context
    elif "profile" in msg_lower or "context" in msg_lower or ("sharma" in msg_lower and "met" not in msg_lower) or ("jenkins" in msg_lower and "met" not in msg_lower) or ("patel" in msg_lower and "met" not in msg_lower):
        print("Fallback Match: get_hcp_context")
        hcp_name = "Dr. Rajesh Sharma"
        if "jenkins" in msg_lower:
            hcp_name = "Dr. Sarah Jenkins"
        elif "patel" in msg_lower:
            hcp_name = "Dr. Amit Patel"
            
        res = get_hcp_context_tool.invoke({"hcp_name": hcp_name})
        tool_outputs.append({
            "name": "get_hcp_context",
            "args": {"hcp_name": hcp_name},
            "status": res["status"],
            "result": res["message"]
        })
        if res["status"] == "success":
            hcp_context = res["data"]
            conversational_response = f"I've loaded the context profile card for {hcp_name} ({hcp_context['specialty']}) from the database. They work at {hcp_context['clinic_name']}."
        else:
            conversational_response = f"Failed to retrieve HCP context: {res['message']}"

    # 4. Suggest Follow up
    elif "suggest" in msg_lower or "follow-up" in msg_lower or "recommend" in msg_lower:
        print("Fallback Match: suggest_follow_up")
        res = suggest_follow_up_tool.invoke({"interaction_id": current_id})
        tool_outputs.append({
            "name": "suggest_follow_up",
            "args": {"interaction_id": current_id},
            "status": res["status"],
            "result": res["message"]
        })
        if res["status"] == "success":
            conversational_response = "I have fetched follow-up suggestions for the current interaction. They are shown under the form on the left."
        else:
            conversational_response = f"Failed to get follow-up suggestions: {res['message']}"
            
    # 5. Inventory check
    elif "inventory" in msg_lower or "sample" in msg_lower or "brochure" in msg_lower or "stock" in msg_lower:
        print("Fallback Match: manage_samples_and_materials")
        action = "list_samples"
        if "brochure" in msg_lower or "material" in msg_lower:
            action = "list_materials"
            
        res = manage_samples_and_materials_tool.invoke({"action": action})
        tool_outputs.append({
            "name": "manage_samples_and_materials",
            "args": {"action": action},
            "status": res["status"],
            "result": res["message"]
        })
        if res["status"] == "success":
            items_str = ", ".join([f"{item.get('name')} (Stock: {item.get('stock_quantity', item.get('type'))})" for item in res["data"]])
            conversational_response = f"I retrieved the inventory list. Here are the items:\n{items_str}."
        else:
            conversational_response = f"Failed to get inventory: {res['message']}"
            
    else:
        # General conversational greeting
        conversational_response = (
            "Hello! I am your AI CRM assistant. You can speak to me naturally to log meetings, "
            "update records, search histories, or check stock. (Note: Running in offline backup mode)."
        )
        
    return {
        "response": conversational_response,
        "current_interaction_id": new_active_id,
        "form_data": form_data,
        "hcp_context": hcp_context,
        "tool_calls": tool_outputs
    }


def execute_agent(message: str, current_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Entry point to run the agent. Tries to run the LangGraph workflow with ChatGroq.
    If the API call fails or key is missing, it runs the rule-based backup parser.
    """
    # 1. Check if LLM is available and key is configured
    if not llm:
        return run_rule_based_fallback(message, current_id)
        
    # 2. Run LangGraph
    try:
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "current_interaction_id": current_id,
            "hcp_context": None,
            "form_data": None,
            "tool_outputs": [],
            "response": None,
            "error": None
        }
        
        # Execute graph
        final_state = compiled_graph.invoke(initial_state)
        
        # Check if router node had an error (like Groq authentication failure)
        if final_state.get("error"):
            # Try to fall back to rule-based engine
            return run_rule_based_fallback(message, current_id)
            
        # Standard schema response
        mapped_calls = []
        for call in final_state.get("tool_outputs", []):
            mapped_calls.append(schemas.ToolCallRecord(
                name=call["name"],
                args=call["args"],
                status=call["status"],
                result=call["result"]
            ))
            
        return {
            "response": final_state.get("response") or "Processed successfully.",
            "current_interaction_id": final_state.get("current_interaction_id"),
            "form_data": final_state.get("form_data"),
            "hcp_context": final_state.get("hcp_context"),
            "tool_calls": mapped_calls
        }
    except Exception as e:
        print(f"Error in LangGraph execution: {e}. Falling back...")
        return run_rule_based_fallback(message, current_id)
