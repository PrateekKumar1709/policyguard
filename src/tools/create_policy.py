"""Create Policy Tool - Define security policies for agent governance.

Policies control what agents can and cannot do. They are evaluated
by the validate_action tool before any action is performed.
"""

import json
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


def _validate_policy_rules(rules: list[dict[str, Any]]) -> tuple[bool, str]:
    """Validate policy rules structure.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not rules:
        return False, "Policy must have at least one rule"
    
    valid_actions = ["allow", "deny", "require_approval"]
    
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            return False, f"Rule {i} must be an object"
        
        condition = rule.get("condition", {})
        if not condition:
            return False, f"Rule {i} must have a 'condition' object"
        
        action = rule.get("action", "deny")
        if action not in valid_actions:
            return False, f"Rule {i} has invalid action '{action}'. Must be one of: {valid_actions}"
    
    return True, ""


@mcp.tool()
def create_policy(
    policy_id: str,
    name: str,
    description: str,
    rules: str,
    priority: int = 100,
    enabled: bool = True,
) -> str:
    """Create or update a security policy for agent governance.
    
    Policies define rules that control what agents can do. Each policy
    contains conditions and actions (allow/deny/require_approval).
    
    Args:
        policy_id: Unique identifier for the policy (e.g., "prod-db-access")
        name: Human-readable name (e.g., "Production Database Access Control")
        description: Description of what this policy controls
        rules: JSON array of rule objects. Each rule has:
            - condition: Object with matching criteria
                - tool_pattern: Glob pattern for tool names (e.g., "database_*")
                - action_type: Type of action (e.g., "tool_call")
                - trust_level_at_least: Minimum trust level required
                - trust_level_below: Trigger if trust below this level
            - action: "allow", "deny", or "require_approval"
            - message: Message to show when rule matches
        priority: Higher priority policies are evaluated first (default: 100)
        enabled: Whether the policy is active (default: true)
    
    Returns:
        JSON string with creation result:
        - success: Whether creation succeeded
        - policy_id: The policy's ID
        - message: Status message
    
    Example:
        create_policy(
            policy_id="prevent-deletions",
            name="Prevent Dangerous Deletions",
            description="Block delete operations for non-admin agents",
            rules='[{"condition": {"tool_pattern": "delete_*", "trust_level_below": "admin"}, "action": "deny", "message": "Delete operations require admin access"}]'
        )
    """
    timestamp = get_timestamp()
    
    # Parse rules JSON
    try:
        rules_list = json.loads(rules) if rules else []
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "policy_id": policy_id,
            "message": f"Invalid rules JSON: {e}",
        }, indent=2)
    
    # Validate rules
    is_valid, error_msg = _validate_policy_rules(rules_list)
    if not is_valid:
        return json.dumps({
            "success": False,
            "policy_id": policy_id,
            "message": f"Invalid policy rules: {error_msg}",
        }, indent=2)
    
    # Load existing policies
    policies = load_json_file("policies.json", default=[])
    
    # Check if policy already exists
    existing_idx = None
    for i, p in enumerate(policies):
        if p.get("id") == policy_id:
            existing_idx = i
            break
    
    is_update = existing_idx is not None
    
    # Create policy record
    policy_record = {
        "id": policy_id,
        "name": name,
        "description": description,
        "rules": rules_list,
        "priority": priority,
        "enabled": enabled,
        "created_at": policies[existing_idx].get("created_at", timestamp) if is_update else timestamp,
        "updated_at": timestamp,
    }
    
    # Save policy
    if is_update:
        policies[existing_idx] = policy_record
    else:
        policies.append(policy_record)
    
    # Sort by priority (higher first)
    policies.sort(key=lambda p: p.get("priority", 0), reverse=True)
    
    save_json_file("policies.json", policies)
    
    # Log the policy creation
    audit_entry = {
        "entry_id": generate_id("aud"),
        "timestamp": timestamp,
        "agent_id": "guardian-system",
        "action": {
            "type": "policy_management",
            "target": policy_id,
            "parameters": {
                "operation": "update" if is_update else "create",
                "rules_count": len(rules_list),
                "enabled": enabled,
            },
        },
        "evaluation": {
            "allowed": True,
            "reason": "Policy management completed",
        },
    }
    append_to_json_list("audit_log.json", audit_entry)
    
    action = "updated" if is_update else "created"
    return json.dumps({
        "success": True,
        "policy_id": policy_id,
        "message": f"Policy '{name}' ({policy_id}) {action} successfully with {len(rules_list)} rules",
    }, indent=2)
