"""Register Agent Tool - Register agents with Guardian for policy evaluation.

Agents must be registered to get proper trust levels and permissions.
Unregistered agents are auto-registered with 'low' trust level.
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Handle imports for both server runtime and test contexts
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

try:
    from core.server import mcp
    from core.utils import (
        generate_id,
        get_timestamp,
        load_json_file,
        save_json_file,
        append_to_json_list,
    )
except ImportError:
    from src.core.server import mcp
    from src.core.utils import (
        generate_id,
        get_timestamp,
        load_json_file,
        save_json_file,
        append_to_json_list,
    )


@mcp.tool()
def register_agent(
    agent_id: str,
    name: str,
    description: str = "",
    trust_level: str = "medium",
    allowed_tools: str = "[]",
    denied_tools: str = "[]",
    metadata: str = "{}",
) -> str:
    """Register a new agent with Guardian for security policy evaluation.
    
    Registered agents get proper trust levels and can have custom tool
    permissions. Unregistered agents are treated as 'low' trust.
    
    Args:
        agent_id: Unique identifier for the agent (e.g., "prod-assistant-01")
        name: Human-readable name (e.g., "Production Assistant")
        description: Description of the agent's purpose
        trust_level: Trust level - "low", "medium", "high", or "admin"
        allowed_tools: JSON array of allowed tool patterns (e.g., '["read_*", "query_*"]')
        denied_tools: JSON array of denied tool patterns (e.g., '["delete_*", "drop_*"]')
        metadata: JSON object with additional agent metadata
    
    Returns:
        JSON string with registration result:
        - success: Whether registration succeeded
        - agent_id: The agent's ID
        - message: Status message
        - warnings: Any warnings about the registration
    
    Example:
        register_agent(
            agent_id="data-analyst-01",
            name="Data Analyst Bot",
            description="Runs analytical queries on warehouse",
            trust_level="medium",
            allowed_tools='["query_*", "read_*"]',
            denied_tools='["delete_*", "drop_*", "truncate_*"]'
        )
    """
    timestamp = get_timestamp()
    
    # Parse JSON inputs
    try:
        allowed_list = json.loads(allowed_tools) if allowed_tools else []
    except json.JSONDecodeError:
        allowed_list = []
        
    try:
        denied_list = json.loads(denied_tools) if denied_tools else []
    except json.JSONDecodeError:
        denied_list = []
        
    try:
        meta = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        meta = {}
    
    # Validate trust level
    valid_trust_levels = ["low", "medium", "high", "admin"]
    if trust_level not in valid_trust_levels:
        return json.dumps({
            "success": False,
            "agent_id": agent_id,
            "message": f"Invalid trust level '{trust_level}'. Must be one of: {valid_trust_levels}",
            "warnings": [],
        }, indent=2)
    
    # Load existing agents
    agents = load_json_file("agents.json", default={})
    
    # Check if agent already exists
    is_update = agent_id in agents
    
    # Create/update agent record
    agent_record = {
        "agent_id": agent_id,
        "name": name,
        "description": description,
        "trust_level": trust_level,
        "allowed_tools": allowed_list,
        "denied_tools": denied_list,
        "metadata": meta,
        "status": "active",
        "registered_at": agents.get(agent_id, {}).get("registered_at", timestamp),
        "updated_at": timestamp,
        "auto_registered": False,
    }
    
    # Save agent
    agents[agent_id] = agent_record
    save_json_file("agents.json", agents)
    
    # Log the registration
    audit_entry = {
        "entry_id": generate_id("aud"),
        "timestamp": timestamp,
        "agent_id": "guardian-system",
        "action": {
            "type": "agent_registration",
            "target": agent_id,
            "parameters": {
                "trust_level": trust_level,
                "is_update": is_update,
            },
        },
        "evaluation": {
            "allowed": True,
            "reason": "Agent registration completed",
        },
    }
    append_to_json_list("audit_log.json", audit_entry)
    
    # Build warnings
    warnings = []
    if trust_level == "admin":
        warnings.append("Agent registered with ADMIN trust level - has full access")
    if not allowed_list and not denied_list:
        warnings.append("No tool restrictions defined - agent can use any tool per policies")
    
    action = "updated" if is_update else "registered"
    return json.dumps({
        "success": True,
        "agent_id": agent_id,
        "message": f"Agent '{name}' ({agent_id}) {action} successfully with trust level '{trust_level}'",
        "warnings": warnings,
    }, indent=2)
