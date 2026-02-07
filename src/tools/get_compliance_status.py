"""Get Compliance Status Tool - Generate compliance reports and health metrics.

Provides an overview of security posture, policy violations, and compliance
metrics for regulatory reporting (SOC2, HIPAA, etc.).
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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


def _calculate_metrics(
    entries: list[dict[str, Any]],
    time_range_hours: int,
) -> dict[str, Any]:
    """Calculate compliance metrics from audit entries."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=time_range_hours)
    
    # Filter to time range
    recent_entries = []
    for entry in entries:
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", "").replace("Z", "+00:00"))
            if ts >= cutoff:
                recent_entries.append(entry)
        except (ValueError, AttributeError):
            pass
    
    # Calculate stats
    total = len(recent_entries)
    allowed = sum(1 for e in recent_entries if e.get("evaluation", {}).get("allowed", True))
    denied = total - allowed
    
    # Group by agent
    agent_stats = {}
    for entry in recent_entries:
        agent_id = entry.get("agent_id", "unknown")
        if agent_id not in agent_stats:
            agent_stats[agent_id] = {"allowed": 0, "denied": 0}
        if entry.get("evaluation", {}).get("allowed", True):
            agent_stats[agent_id]["allowed"] += 1
        else:
            agent_stats[agent_id]["denied"] += 1
    
    # Find top offenders
    offenders = [
        {"agent_id": aid, "violations": stats["denied"]}
        for aid, stats in agent_stats.items()
        if stats["denied"] > 0
    ]
    offenders.sort(key=lambda x: x["violations"], reverse=True)
    
    # Group by action type
    action_breakdown = {}
    for entry in recent_entries:
        action_type = entry.get("action", {}).get("type", "unknown")
        if action_type not in action_breakdown:
            action_breakdown[action_type] = {"allowed": 0, "denied": 0}
        if entry.get("evaluation", {}).get("allowed", True):
            action_breakdown[action_type]["allowed"] += 1
        else:
            action_breakdown[action_type]["denied"] += 1
    
    return {
        "total_actions": total,
        "allowed_actions": allowed,
        "denied_actions": denied,
        "denial_rate": round(denied / total * 100, 2) if total > 0 else 0,
        "top_offenders": offenders[:5],
        "action_breakdown": action_breakdown,
        "unique_agents": len(agent_stats),
    }


@mcp.tool()
def get_compliance_status(
    time_range: str = "24h",
    include_incidents: bool = True,
    include_policy_summary: bool = True,
) -> str:
    """Get compliance status and security health metrics.
    
    Generates a compliance report showing policy violations, security
    incidents, and overall governance health for the specified time period.
    
    Args:
        time_range: Time range - "1h", "24h", "7d", "30d" (default: "24h")
        include_incidents: Include active incidents in report (default: true)
        include_policy_summary: Include policy overview (default: true)
    
    Returns:
        JSON string with compliance report:
        - status: Overall status ("healthy", "warning", "critical")
        - metrics: Key security metrics
        - incidents: Active security incidents (if requested)
        - policies: Policy summary (if requested)
        - recommendations: Suggested actions to improve security
    
    Example:
        # Get daily compliance status
        get_compliance_status(time_range="24h")
        
        # Get weekly report with all details
        get_compliance_status(time_range="7d", include_incidents=True)
    """
    # Parse time range
    time_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
    hours = time_map.get(time_range, 24)
    
    # Load data
    audit_entries = load_json_file("audit_log.json", default=[])
    incidents = load_json_file("incidents.json", default=[])
    policies = load_json_file("policies.json", default=[])
    agents = load_json_file("agents.json", default={})
    
    # Calculate metrics
    metrics = _calculate_metrics(audit_entries, hours)
    
    # Determine overall status
    denial_rate = metrics["denial_rate"]
    if denial_rate > 20:
        status = "critical"
        status_message = "High denial rate indicates potential security issues or misconfigured policies"
    elif denial_rate > 10:
        status = "warning"
        status_message = "Elevated denial rate - review agent configurations"
    else:
        status = "healthy"
        status_message = "Security posture is within acceptable parameters"
    
    # Build report
    report = {
        "status": status,
        "status_message": status_message,
        "time_range": time_range,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "recommendations": [],
    }
    
    # Add recommendations
    if metrics["denied_actions"] > 0 and metrics["top_offenders"]:
        top_offender = metrics["top_offenders"][0]
        report["recommendations"].append(
            f"Review agent '{top_offender['agent_id']}' - {top_offender['violations']} violations"
        )
    
    if not policies:
        report["recommendations"].append(
            "No security policies defined - create policies using create_policy tool"
        )
    
    enabled_policies = sum(1 for p in policies if p.get("enabled", True))
    if enabled_policies == 0:
        report["recommendations"].append(
            "No policies are enabled - enable policies to enforce security"
        )
    
    # Include incidents if requested
    if include_incidents:
        # Get recent incidents
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        recent_incidents = []
        
        for inc in incidents:
            try:
                ts = datetime.fromisoformat(inc.get("timestamp", "").replace("Z", "+00:00"))
                if ts >= cutoff:
                    recent_incidents.append(inc)
            except (ValueError, AttributeError):
                pass
        
        # Sort by timestamp
        recent_incidents.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        report["incidents"] = {
            "total": len(recent_incidents),
            "by_severity": {
                "critical": sum(1 for i in recent_incidents if i.get("severity") == "critical"),
                "high": sum(1 for i in recent_incidents if i.get("severity") == "high"),
                "medium": sum(1 for i in recent_incidents if i.get("severity") == "medium"),
                "low": sum(1 for i in recent_incidents if i.get("severity") == "low"),
            },
            "recent": recent_incidents[:10],
        }
    
    # Include policy summary if requested
    if include_policy_summary:
        report["policies"] = {
            "total": len(policies),
            "enabled": enabled_policies,
            "disabled": len(policies) - enabled_policies,
            "list": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "enabled": p.get("enabled", True),
                    "rules_count": len(p.get("rules", [])),
                }
                for p in policies
            ],
        }
    
    # Add agent summary
    report["agents"] = {
        "total": len(agents),
        "by_trust_level": {
            "admin": sum(1 for a in agents.values() if a.get("trust_level") == "admin"),
            "high": sum(1 for a in agents.values() if a.get("trust_level") == "high"),
            "medium": sum(1 for a in agents.values() if a.get("trust_level") == "medium"),
            "low": sum(1 for a in agents.values() if a.get("trust_level") == "low"),
        },
        "suspended": sum(1 for a in agents.values() if a.get("status") == "suspended"),
    }
    
    return json.dumps(report, indent=2)
