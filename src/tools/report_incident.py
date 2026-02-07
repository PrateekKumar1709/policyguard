"""Report Incident Tool - Log security incidents for investigation.

Used to report security incidents, suspicious activity, or policy violations
that require investigation or immediate action.
"""

import json
import sys
from pathlib import Path

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


@mcp.tool()
def report_incident(
    incident_type: str,
    severity: str,
    description: str,
    agent_id: str = "",
    evidence: str = "{}",
    recommended_action: str = "",
) -> str:
    """Report a security incident for investigation and tracking.
    
    Use this tool to log security incidents such as policy violations,
    suspicious agent behavior, or potential security threats.
    
    Args:
        incident_type: Type of incident:
            - "policy_violation": Agent violated a security policy
            - "suspicious_activity": Unusual or potentially malicious behavior
            - "unauthorized_access": Attempt to access restricted resources
            - "rate_limit_exceeded": Agent exceeded rate limits
            - "data_exfiltration": Potential data leak detected
            - "configuration_error": Security misconfiguration detected
            - "other": Other security concern
        severity: Incident severity:
            - "low": Minor issue, no immediate action needed
            - "medium": Notable issue, should be reviewed
            - "high": Serious issue, needs prompt attention
            - "critical": Emergency, immediate action required
        description: Detailed description of the incident
        agent_id: ID of the agent involved (if applicable)
        evidence: JSON object with supporting evidence/data
        recommended_action: Suggested remediation steps
    
    Returns:
        JSON string with:
        - incident_id: Unique incident identifier
        - success: Whether the incident was logged
        - message: Status message
        - agent_suspended: Whether the agent was auto-suspended
    
    Example:
        report_incident(
            incident_type="suspicious_activity",
            severity="high",
            description="Agent attempted to access 50 databases in 1 minute",
            agent_id="rogue-agent-01",
            evidence='{"databases_accessed": 50, "time_window": "60s"}',
            recommended_action="Review agent permissions and suspend if needed"
        )
    """
    timestamp = get_timestamp()
    incident_id = generate_id("inc")
    
    # Validate incident type
    valid_types = [
        "policy_violation",
        "suspicious_activity", 
        "unauthorized_access",
        "rate_limit_exceeded",
        "data_exfiltration",
        "configuration_error",
        "other",
    ]
    if incident_type not in valid_types:
        incident_type = "other"
    
    # Validate severity
    valid_severities = ["low", "medium", "high", "critical"]
    if severity not in valid_severities:
        severity = "medium"
    
    # Parse evidence
    try:
        evidence_data = json.loads(evidence) if evidence else {}
    except json.JSONDecodeError:
        evidence_data = {"raw": evidence}
    
    # Create incident record
    incident = {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "type": incident_type,
        "severity": severity,
        "description": description,
        "agent_id": agent_id or None,
        "evidence": evidence_data,
        "recommended_action": recommended_action,
        "status": "open",
        "resolution": None,
    }
    
    # Save incident
    append_to_json_list("incidents.json", incident)
    
    # Auto-suspend agent for critical incidents
    agent_suspended = False
    if severity == "critical" and agent_id:
        agents = load_json_file("agents.json", default={})
        if agent_id in agents:
            agents[agent_id]["status"] = "suspended"
            agents[agent_id]["suspended_at"] = timestamp
            agents[agent_id]["suspension_reason"] = f"Auto-suspended due to critical incident: {incident_id}"
            save_json_file("agents.json", agents)
            agent_suspended = True
    
    # Log to audit trail
    audit_entry = {
        "entry_id": generate_id("aud"),
        "timestamp": timestamp,
        "agent_id": "guardian-system",
        "action": {
            "type": "incident_report",
            "target": incident_id,
            "parameters": {
                "incident_type": incident_type,
                "severity": severity,
                "related_agent": agent_id,
            },
        },
        "evaluation": {
            "allowed": True,
            "reason": "Incident logged for investigation",
        },
    }
    append_to_json_list("audit_log.json", audit_entry)
    
    # Build response
    message = f"Incident '{incident_id}' logged with severity '{severity}'"
    if agent_suspended:
        message += f" - Agent '{agent_id}' has been automatically suspended"
    
    return json.dumps({
        "incident_id": incident_id,
        "success": True,
        "message": message,
        "agent_suspended": agent_suspended,
        "severity": severity,
        "type": incident_type,
    }, indent=2)
