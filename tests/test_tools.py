"""Unit tests for PolicyGuard tools.

These tests verify the security policy logic WITHOUT requiring any LLM.
Run with: pytest tests/test_tools.py -v
"""

import importlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, tmp_path):
    """Set up test environment with temporary data directory."""
    # Use pytest's tmp_path fixture for a fresh directory each test
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir()
    
    # Set environment variable for data dir BEFORE imports
    monkeypatch.setenv("POLICYGUARD_DATA_DIR", str(test_data_dir))
    
    # Force reload of utils module to pick up new DATA_DIR
    import src.core.utils as utils_module
    utils_module.set_data_dir(str(test_data_dir))
    
    # Also patch in case something cached it
    monkeypatch.setattr("src.core.utils.DATA_DIR", test_data_dir)
    
    # Create empty data files
    for filename in ["audit_log.json", "incidents.json"]:
        filepath = test_data_dir / filename
        with open(filepath, "w") as f:
            json.dump([], f)
    
    # Create default agents
    agents = {
        "test-low": {"agent_id": "test-low", "name": "Low Trust", "trust_level": "low", "status": "active", "allowed_tools": [], "denied_tools": []},
        "test-medium": {"agent_id": "test-medium", "name": "Medium Trust", "trust_level": "medium", "status": "active", "allowed_tools": [], "denied_tools": []},
        "test-high": {"agent_id": "test-high", "name": "High Trust", "trust_level": "high", "status": "active", "allowed_tools": [], "denied_tools": []},
        "test-admin": {"agent_id": "test-admin", "name": "Admin", "trust_level": "admin", "status": "active", "allowed_tools": [], "denied_tools": []},
        "test-suspended": {"agent_id": "test-suspended", "name": "Suspended", "trust_level": "medium", "status": "suspended", "allowed_tools": [], "denied_tools": []},
    }
    with open(test_data_dir / "agents.json", "w") as f:
        json.dump(agents, f)
    
    # Create test policies
    policies = [
        {
            "id": "test-policy",
            "name": "Test Policy",
            "rules": [
                {"condition": {"tool_pattern": "delete_*", "trust_level_below": "admin"}, "action": "deny", "message": "Delete requires admin"},
                {"condition": {"tool_pattern": "read_*", "trust_level_at_least": "low"}, "action": "allow", "message": "Read allowed"},
            ],
            "enabled": True,
            "priority": 100,
        }
    ]
    with open(test_data_dir / "policies.json", "w") as f:
        json.dump(policies, f)
    
    yield


class TestValidateAction:
    """Tests for validate_action tool."""
    
    def test_allow_read_for_low_trust(self):
        """Low trust agent should be able to read."""
        from src.tools.validate_action import validate_action
        
        # Access the underlying function via .fn
        result = json.loads(validate_action.fn(
            action_type="tool_call",
            target="read_data",
            agent_id="test-low",
        ))
        
        assert result["allowed"] is True
    
    def test_deny_delete_for_low_trust(self):
        """Low trust agent should not be able to delete."""
        from src.tools.validate_action import validate_action
        
        result = json.loads(validate_action.fn(
            action_type="tool_call",
            target="delete_records",
            agent_id="test-low",
        ))
        
        assert result["allowed"] is False
        assert "admin" in result["reason"].lower()
    
    def test_allow_delete_for_admin(self):
        """Admin agent should be able to delete."""
        from src.tools.validate_action import validate_action
        
        result = json.loads(validate_action.fn(
            action_type="tool_call",
            target="delete_records",
            agent_id="test-admin",
        ))
        
        assert result["allowed"] is True
    
    def test_deny_suspended_agent(self):
        """Suspended agent should be denied all actions."""
        from src.tools.validate_action import validate_action
        
        result = json.loads(validate_action.fn(
            action_type="tool_call",
            target="read_data",
            agent_id="test-suspended",
        ))
        
        assert result["allowed"] is False
        assert "suspended" in result["reason"].lower()
    
    def test_auto_register_unknown_agent(self):
        """Unknown agent should be auto-registered with low trust."""
        from src.tools.validate_action import validate_action
        
        result = json.loads(validate_action.fn(
            action_type="tool_call",
            target="delete_records",
            agent_id="unknown-agent",
        ))
        
        # Should be denied because auto-registered as low trust
        assert result["allowed"] is False
    
    def test_action_id_generated(self):
        """Each validation should generate a unique action ID."""
        from src.tools.validate_action import validate_action
        
        result1 = json.loads(validate_action.fn(
            action_type="tool_call",
            target="read_data",
            agent_id="test-low",
        ))
        
        result2 = json.loads(validate_action.fn(
            action_type="tool_call",
            target="read_data",
            agent_id="test-low",
        ))
        
        assert result1["action_id"] != result2["action_id"]
        assert result1["action_id"].startswith("act_")


class TestRegisterAgent:
    """Tests for register_agent tool."""
    
    def test_register_new_agent(self):
        """Should successfully register a new agent."""
        from src.tools.register_agent import register_agent
        
        result = json.loads(register_agent.fn(
            agent_id="new-agent",
            name="New Agent",
            description="A new test agent",
            trust_level="medium",
        ))
        
        assert result["success"] is True
        assert "registered" in result["message"].lower()
    
    def test_reject_invalid_trust_level(self):
        """Should reject invalid trust levels."""
        from src.tools.register_agent import register_agent
        
        result = json.loads(register_agent.fn(
            agent_id="bad-agent",
            name="Bad Agent",
            trust_level="superadmin",  # Invalid
        ))
        
        assert result["success"] is False
        assert "invalid" in result["message"].lower()
    
    def test_warn_on_admin_registration(self):
        """Should warn when registering admin agent."""
        from src.tools.register_agent import register_agent
        
        result = json.loads(register_agent.fn(
            agent_id="admin-agent-2",
            name="Another Admin",
            trust_level="admin",
        ))
        
        assert result["success"] is True
        assert len(result["warnings"]) > 0
        assert "admin" in result["warnings"][0].lower()


class TestCreatePolicy:
    """Tests for create_policy tool."""
    
    def test_create_valid_policy(self):
        """Should create a valid policy."""
        from src.tools.create_policy import create_policy
        
        rules = json.dumps([
            {"condition": {"tool_pattern": "test_*"}, "action": "allow", "message": "Test allowed"}
        ])
        
        result = json.loads(create_policy.fn(
            policy_id="new-policy",
            name="New Policy",
            description="A test policy",
            rules=rules,
        ))
        
        assert result["success"] is True
    
    def test_reject_empty_rules(self):
        """Should reject policy with no rules."""
        from src.tools.create_policy import create_policy
        
        result = json.loads(create_policy.fn(
            policy_id="empty-policy",
            name="Empty Policy",
            description="No rules",
            rules="[]",
        ))
        
        assert result["success"] is False
    
    def test_reject_invalid_action(self):
        """Should reject policy with invalid action."""
        from src.tools.create_policy import create_policy
        
        rules = json.dumps([
            {"condition": {"tool_pattern": "test_*"}, "action": "explode", "message": "Invalid"}
        ])
        
        result = json.loads(create_policy.fn(
            policy_id="bad-policy",
            name="Bad Policy",
            description="Invalid action",
            rules=rules,
        ))
        
        assert result["success"] is False


class TestGetAuditLog:
    """Tests for get_audit_log tool."""
    
    def test_get_audit_log_structure(self):
        """Should return valid audit log structure."""
        from src.tools.get_audit_log import get_audit_log
        
        result = json.loads(get_audit_log.fn())
        
        # Check structure is correct
        assert "count" in result
        assert "entries" in result
        assert "total" in result
        assert "time_range" in result
        assert isinstance(result["entries"], list)
    
    def test_filter_by_agent(self):
        """Should filter by agent ID."""
        from src.tools.get_audit_log import get_audit_log
        from src.tools.validate_action import validate_action
        
        # Create some audit entries
        validate_action.fn("tool_call", "read_data", "test-low")
        validate_action.fn("tool_call", "read_data", "test-medium")
        
        result = json.loads(get_audit_log.fn(agent_id="test-low"))
        
        # All entries should be for test-low
        for entry in result["entries"]:
            assert entry["agent_id"] == "test-low"


class TestReportIncident:
    """Tests for report_incident tool."""
    
    def test_report_incident(self):
        """Should successfully report an incident."""
        from src.tools.report_incident import report_incident
        
        result = json.loads(report_incident.fn(
            incident_type="suspicious_activity",
            severity="high",
            description="Test incident",
            agent_id="test-low",
        ))
        
        assert result["success"] is True
        assert result["incident_id"].startswith("inc_")
    
    def test_auto_suspend_on_critical(self):
        """Should auto-suspend agent on critical incident."""
        from src.tools.report_incident import report_incident
        
        result = json.loads(report_incident.fn(
            incident_type="unauthorized_access",
            severity="critical",
            description="Critical security breach",
            agent_id="test-medium",
        ))
        
        assert result["success"] is True
        assert result["agent_suspended"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
