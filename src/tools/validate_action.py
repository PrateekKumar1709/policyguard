"""Validate Action Tool - Core security gate for Guardian Agent.

This is the primary tool that agents should call BEFORE performing any action.
It evaluates the requested action against security policies and returns
whether the action is allowed, denied, or requires approval.
"""

import re
import sys
from pathlib import Path
from typing import Any

# Handle imports for both server runtime and test contexts
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

try:
    from core.server import mcp
    from core.utils import (
        append_to_json_list,
        generate_id,
        get_timestamp,
        load_json_file,
        save_json_file,
    )
except ImportError:
    from src.core.server import mcp
    from src.core.utils import (
        append_to_json_list,
        generate_id,
        get_timestamp,
        load_json_file,
        save_json_file,
    )


def _load_policies() -> list[dict[str, Any]]:
    """Load active policies from storage."""
    return load_json_file("policies.json", default=[])


def _load_agents() -> dict[str, Any]:
    """Load registered agents from storage."""
    return load_json_file("agents.json", default={})


def _match_pattern(pattern: str, value: str) -> bool:
    """Match a pattern against a value (supports * wildcard).
    
    Args:
        pattern: Pattern with optional * wildcards
        value: Value to match against
        
    Returns:
        True if pattern matches value
    """
    if pattern == "*":
        return True
    # Convert glob pattern to regex
    regex_pattern = pattern.replace("*", ".*")
    return bool(re.match(f"^{regex_pattern}$", value, re.IGNORECASE))


def _evaluate_policies(
    action_type: str,
    target: str,
    agent_id: str,
    parameters: dict[str, Any],
    agents: dict[str, Any],
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate action against all active policies.
    
    Returns:
        Evaluation result with allowed status and reason
    """
    # Get agent info
    agent = agents.get(agent_id, {})
    trust_level = agent.get("trust_level", "low")
    allowed_tools = agent.get("allowed_tools", [])
    denied_tools = agent.get("denied_tools", [])
    
    # Trust level hierarchy
    trust_levels = {"low": 1, "medium": 2, "high": 3, "admin": 4}
    agent_trust_score = trust_levels.get(trust_level, 1)
    
    # Check agent-specific tool restrictions first
    if denied_tools:
        for pattern in denied_tools:
            if _match_pattern(pattern, target):
                return {
                    "allowed": False,
                    "reason": f"Tool '{target}' is explicitly denied for agent '{agent_id}'",
                    "policy_matched": "agent_denied_tools",
                }
    
    if allowed_tools and allowed_tools != ["*"]:
        tool_allowed = False
        for pattern in allowed_tools:
            if _match_pattern(pattern, target):
                tool_allowed = True
                break
        if not tool_allowed:
            return {
                "allowed": False,
                "reason": f"Tool '{target}' is not in allowed list for agent '{agent_id}'",
                "policy_matched": "agent_allowed_tools",
            }
    
    # Evaluate each policy
    for policy in policies:
        if not policy.get("enabled", True):
            continue
            
        rules = policy.get("rules", [])
        for rule in rules:
            condition = rule.get("condition", {})
            
            # Check tool pattern match
            tool_pattern = condition.get("tool_pattern")
            if tool_pattern and not _match_pattern(tool_pattern, target):
                continue
            
            # Check action type match
            action_pattern = condition.get("action_type")
            if action_pattern and not _match_pattern(action_pattern, action_type):
                continue
            
            # Check trust level requirement
            required_trust = condition.get("trust_level_at_least")
            if required_trust:
                required_score = trust_levels.get(required_trust, 1)
                if agent_trust_score < required_score:
                    action = rule.get("action", "deny")
                    if action == "deny":
                        return {
                            "allowed": False,
                            "reason": f"Tool '{target}' requires trust level '{required_trust}', agent has '{trust_level}'",
                            "policy_matched": policy.get("id", "unknown"),
                        }
            
            # Check trust level below (for denials)
            below_trust = condition.get("trust_level_below")
            if below_trust:
                below_score = trust_levels.get(below_trust, 1)
                if agent_trust_score < below_score:
                    action = rule.get("action", "deny")
                    if action == "deny":
                        return {
                            "allowed": False,
                            "reason": rule.get("message", f"Access denied by policy '{policy.get('id')}'"),
                            "policy_matched": policy.get("id", "unknown"),
                        }
                    elif action == "require_approval":
                        return {
                            "allowed": False,
                            "require_approval": True,
                            "reason": rule.get("message", "This action requires human approval"),
                            "policy_matched": policy.get("id", "unknown"),
                        }
    
    # Default: allow if no policy denied
    return {
        "allowed": True,
        "reason": "Action permitted by default policy",
        "policy_matched": "default_allow",
    }


@mcp.tool()
def validate_action(
    action_type: str,
    target: str,
    agent_id: str,
    parameters: str = "{}",
    context: str = "",
) -> str:
    """Validate whether an agent can perform a specific action.
    
    This is the PRIMARY security gate. Agents should call this BEFORE
    performing any sensitive action to ensure compliance with security policies.
    
    Args:
        action_type: Type of action (e.g., "tool_call", "resource_access", "data_read", "data_write")
        target: Target of the action (e.g., tool name, resource URI, database name)
        agent_id: Unique identifier of the requesting agent
        parameters: JSON string of action-specific parameters (optional)
        context: Additional context about why this action is needed (optional)
    
    Returns:
        JSON string with validation result:
        - action_id: Unique ID for this validation (for audit correlation)
        - allowed: Whether the action is permitted
        - require_approval: If true, action needs human approval first
        - reason: Explanation of the decision
        - warnings: Any non-blocking warnings
    
    Example:
        validate_action(
            action_type="tool_call",
            target="database_delete",
            agent_id="prod-agent-01",
            parameters='{"table": "users"}',
            context="Cleanup stale records"
        )
    """
    import json
    
    # Parse parameters
    try:
        params = json.loads(parameters) if parameters else {}
    except json.JSONDecodeError:
        params = {}
    
    # Generate action ID for audit trail
    action_id = generate_id("act")
    timestamp = get_timestamp()
    
    # Load data
    policies = _load_policies()
    agents = _load_agents()
    
    # Check if agent is registered
    if agent_id not in agents:
        # Auto-register unknown agents with low trust
        agents[agent_id] = {
            "agent_id": agent_id,
            "name": f"Auto-registered: {agent_id}",
            "trust_level": "low",
            "registered_at": timestamp,
            "auto_registered": True,
        }
        save_json_file("agents.json", agents)
    
    # Check if agent is suspended
    agent = agents.get(agent_id, {})
    if agent.get("status") == "suspended":
        result = {
            "action_id": action_id,
            "allowed": False,
            "reason": f"Agent '{agent_id}' is suspended",
            "warnings": [],
        }
    else:
        # Evaluate against policies
        eval_result = _evaluate_policies(
            action_type=action_type,
            target=target,
            agent_id=agent_id,
            parameters=params,
            agents=agents,
            policies=policies,
        )
        
        result = {
            "action_id": action_id,
            "allowed": eval_result.get("allowed", False),
            "require_approval": eval_result.get("require_approval", False),
            "reason": eval_result.get("reason", ""),
            "warnings": [],
        }
    
    # Create audit log entry
    audit_entry = {
        "entry_id": generate_id("aud"),
        "action_id": action_id,
        "timestamp": timestamp,
        "agent_id": agent_id,
        "action": {
            "type": action_type,
            "target": target,
            "parameters": params,
            "context": context,
        },
        "evaluation": {
            "allowed": result["allowed"],
            "require_approval": result.get("require_approval", False),
            "reason": result["reason"],
        },
    }
    
    # Save audit entry
    append_to_json_list("audit_log.json", audit_entry)
    
    # If denied, also log as potential incident
    if not result["allowed"]:
        incident = {
            "incident_id": generate_id("inc"),
            "timestamp": timestamp,
            "type": "policy_violation",
            "severity": "medium",
            "agent_id": agent_id,
            "action_id": action_id,
            "details": f"Agent '{agent_id}' attempted '{action_type}' on '{target}' - DENIED: {result['reason']}",
        }
        append_to_json_list("incidents.json", incident)
    
    return json.dumps(result, indent=2)
