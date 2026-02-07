"""Get Audit Log Tool - Retrieve audit trail for compliance and investigation.

The audit log contains records of all validation requests, policy violations,
and administrative actions for compliance reporting and incident investigation.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# Handle imports for both server runtime and test contexts
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

try:
    from core.server import mcp
    from core.utils import load_json_file
except ImportError:
    from src.core.server import mcp
    from src.core.utils import load_json_file


def _parse_time_range(time_range: str) -> Optional[datetime]:
    """Parse a time range string into a cutoff datetime.
    
    Args:
        time_range: Time range like "1h", "24h", "7d", "30d"
        
    Returns:
        Cutoff datetime or None if invalid
    """
    if not time_range:
        return None
    
    time_range = time_range.strip().lower()
    now = datetime.now(timezone.utc)
    
    try:
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            return now - timedelta(hours=hours)
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            return now - timedelta(days=days)
        elif time_range.endswith("m"):
            minutes = int(time_range[:-1])
            return now - timedelta(minutes=minutes)
    except (ValueError, IndexError):
        return None
    
    return None


def _filter_entries(
    entries: list[dict[str, Any]],
    agent_id: Optional[str],
    action_type: Optional[str],
    cutoff: Optional[datetime],
    status: Optional[str],
) -> list[dict[str, Any]]:
    """Filter audit entries based on criteria."""
    filtered = []
    
    for entry in entries:
        # Filter by agent
        if agent_id and entry.get("agent_id") != agent_id:
            continue
        
        # Filter by action type
        action = entry.get("action", {})
        if action_type and action.get("type") != action_type:
            continue
        
        # Filter by time
        if cutoff:
            timestamp_str = entry.get("timestamp", "")
            try:
                entry_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if entry_time < cutoff:
                    continue
            except (ValueError, AttributeError):
                pass
        
        # Filter by status (allowed/denied)
        if status:
            evaluation = entry.get("evaluation", {})
            entry_allowed = evaluation.get("allowed", True)
            if status == "denied" and entry_allowed:
                continue
            if status == "allowed" and not entry_allowed:
                continue
        
        filtered.append(entry)
    
    return filtered


@mcp.tool()
def get_audit_log(
    agent_id: str = "",
    action_type: str = "",
    time_range: str = "24h",
    status: str = "",
    limit: int = 100,
) -> str:
    """Retrieve audit log entries for compliance and investigation.
    
    The audit log records all action validations, policy violations,
    and administrative actions performed through Guardian Agent.
    
    Args:
        agent_id: Filter by specific agent ID (optional)
        action_type: Filter by action type like "tool_call", "resource_access" (optional)
        time_range: Time range to query - "1h", "24h", "7d", "30d" (default: "24h")
        status: Filter by status - "allowed", "denied", or "" for all (optional)
        limit: Maximum number of entries to return (default: 100)
    
    Returns:
        JSON string with:
        - entries: Array of audit log entries
        - count: Number of entries returned
        - total: Total entries matching filter (before limit)
        - time_range: The time range used
        - filters_applied: Summary of filters used
    
    Example:
        # Get all denied actions in the last hour
        get_audit_log(time_range="1h", status="denied")
        
        # Get all actions by a specific agent
        get_audit_log(agent_id="prod-agent-01", time_range="7d")
    """
    # Load audit log
    all_entries = load_json_file("audit_log.json", default=[])
    
    # Parse time range
    cutoff = _parse_time_range(time_range)
    
    # Apply filters
    filtered = _filter_entries(
        entries=all_entries,
        agent_id=agent_id or None,
        action_type=action_type or None,
        cutoff=cutoff,
        status=status or None,
    )
    
    # Sort by timestamp (most recent first)
    filtered.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    
    # Apply limit
    total = len(filtered)
    limited = filtered[:limit]
    
    # Build response
    filters = []
    if agent_id:
        filters.append(f"agent_id={agent_id}")
    if action_type:
        filters.append(f"action_type={action_type}")
    if status:
        filters.append(f"status={status}")
    
    return json.dumps({
        "entries": limited,
        "count": len(limited),
        "total": total,
        "time_range": time_range,
        "filters_applied": filters if filters else ["none"],
    }, indent=2)
