# PolicyGuard

**Security & Governance MCP Server for AI Agents**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PolicyGuard is an MCP (Model Context Protocol) server that provides policy-based access control, incident tracking, and compliance monitoring for AI agents. 

Built for **MCP_HACK//26** hackathon - **"MCP & AI Agents Starter Track"** category.

---

## Table of Contents

- [Overview](#overview)
- [What I Learned](#what-i-learned)
- [Features](#features)
- [Architecture](#architecture)
- [MCP Tools](#mcp-tools)
- [Quick Start](#quick-start)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Testing](#testing)
- [kagent Integration](#kagent-integration)
- [Security Model](#security-model)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview

As AI agents become more autonomous, organizations need controls to govern their behavior. PolicyGuard is my first MCP server project - built to explore how security and governance can be implemented at the MCP layer.

### The Problem

AI agents can call any tool they have access to. Without governance:
- Agents might perform destructive operations
- No audit trail of agent actions
- No way to enforce security policies
- No visibility into compliance

### The Solution

PolicyGuard adds a security layer that agents call **before** taking action:

```
User Request → AI Agent → PolicyGuard (validate_action) → Allowed/Denied
```

---

## What I Learned

This was my first time building:

1. **An MCP Server** - Using FastMCP to expose tools via Model Context Protocol
2. **Policy Engine** - Pattern matching and trust level evaluation
3. **Helm Charts** - Kubernetes-native deployment
4. **kagent Integration** - Creating Agent and RemoteMCPServer custom resources

### Key Takeaways

- MCP makes it easy to expose tools to AI agents
- FastMCP simplifies Python MCP server development
- Kubernetes CRDs enable declarative agent management
- Security should be built-in, not bolted-on

---

## Features

| Feature | Description |
|---------|-------------|
| **Policy Enforcement** | Validate actions against security rules |
| **Trust Levels** | low, medium, high, admin hierarchy |
| **Pattern Matching** | Wildcard patterns like `delete_*`, `*_production` |
| **Auto-Registration** | Unknown agents get minimal trust |
| **Incident Tracking** | Automatic violation logging |
| **Audit Trail** | Complete action history |
| **Compliance Dashboard** | Security metrics at a glance |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Agent / LLM                          │
│                                                                 │
│  "Before any action, call validate_action to check permission" │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PolicyGuard MCP Server                      │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  validate   │  │   create    │  │   report    │             │
│  │   action    │  │   policy    │  │  incident   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  register   │  │  get_audit  │  │    get      │             │
│  │   agent     │  │    log      │  │ compliance  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   JSON Storage    │
                    │   (policies,      │
                    │    agents,        │
                    │    audit_log,     │
                    │    incidents)     │
                    └───────────────────┘
```

---

## MCP Tools

PolicyGuard exposes 6 tools via MCP:

### 1. `validate_action` ⭐ Primary Tool

Check if an action is allowed before executing it.

```json
{
  "action_type": "tool_call",
  "target": "delete_records",
  "agent_id": "my-agent"
}
```

**Response:**
```json
{
  "action_id": "act_a1b2c3d4e5f6",
  "allowed": false,
  "reason": "Delete operations require admin trust level"
}
```

### 2. `register_agent`

Register an agent with a trust level.

```json
{
  "agent_id": "data-processor",
  "name": "Data Agent",
  "trust_level": "medium"
}
```

### 3. `create_policy`

Create security rules.

```json
{
  "policy_id": "block-deletes",
  "name": "Block Deletes",
  "rules": "[{\"condition\": {\"tool_pattern\": \"delete_*\"}, \"action\": \"deny\"}]"
}
```

### 4. `get_audit_log`

Query action history.

### 5. `get_compliance_status`

Get security dashboard metrics.

### 6. `report_incident`

Manually report security incidents.

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Local Installation

```bash
# Clone
git clone https://github.com/PrateekKumar1709/policyguard.git
cd policyguard

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Run
python src/main.py
```

### Test the Tools

```python
import json
from src.tools.validate_action import validate_action
from src.tools.register_agent import register_agent

# Register an agent
result = json.loads(register_agent.fn(
    agent_id="test-agent",
    name="Test Agent",
    trust_level="medium"
))
print(f"Registered: {result['agent_id']}")

# Validate an action
result = json.loads(validate_action.fn(
    action_type="tool_call",
    target="read_data",
    agent_id="test-agent"
))
print(f"Allowed: {result['allowed']}")
```

### HTTP Mode

```bash
python src/main.py --transport http --port 8000
```

---

## Kubernetes Deployment

PolicyGuard includes a Helm chart for Kubernetes deployment.

### Using Kind

```bash
# Create cluster
kind create cluster --name policyguard

# Build and load image
docker build -t policyguard:latest .
kind load docker-image policyguard:latest --name policyguard

# Deploy
kubectl create namespace policyguard
helm install policyguard ./helm/policyguard -n policyguard

# Verify
kubectl get pods -n policyguard
```

### Port Forward

```bash
kubectl port-forward -n policyguard svc/policyguard 8000:8000
```

---

## Testing

### Unit Tests

```bash
pytest tests/ -v
```

### Test Results

```
tests/test_tools.py::TestValidateAction::test_allow_read_for_low_trust PASSED
tests/test_tools.py::TestValidateAction::test_deny_delete_for_low_trust PASSED
tests/test_tools.py::TestValidateAction::test_allow_delete_for_admin PASSED
tests/test_tools.py::TestValidateAction::test_deny_suspended_agent PASSED
tests/test_tools.py::TestRegisterAgent::test_register_new_agent PASSED
tests/test_tools.py::TestCreatePolicy::test_create_valid_policy PASSED
... (16 tests total)
============================== 16 passed ==============================
```

### E2E Test Output

```
[1/6] register_agent      ✅ SUCCESS
[2/6] create_policy       ✅ SUCCESS  
[3/6] validate_action     ✅ ALLOWED (read_data)
[4/6] validate_action     ✅ DENIED (delete_records)
[5/6] report_incident     ✅ SUCCESS
[6/6] get_compliance_status ✅ SUCCESS

ALL 6 MCP TOOLS WORKING!
```

---

## kagent Integration

PolicyGuard can be integrated with [kagent](https://kagent.dev) for Kubernetes-native agent management.

### RemoteMCPServer

```yaml
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: policyguard
spec:
  protocol: STREAMABLE_HTTP
  url: http://policyguard.policyguard:8000/mcp
```

### Agent

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: secure-agent
spec:
  type: Declarative
  declarative:
    systemMessage: "Call validate_action before any operation"
    tools:
    - type: McpServer
      mcpServer:
        name: policyguard
        toolNames:
        - validate_action
        - register_agent
```

---

## Security Model

### Trust Levels

| Level | Score | Use Case |
|-------|-------|----------|
| `low` | 1 | Unknown agents, read-only |
| `medium` | 2 | Verified agents |
| `high` | 3 | Trusted agents |
| `admin` | 4 | Full access |

### Policy Rules

```json
{
  "condition": {
    "tool_pattern": "delete_*",
    "trust_level_below": "admin"
  },
  "action": "deny",
  "message": "Delete requires admin"
}
```

### Evaluation Order

1. Agent suspended? → DENY
2. Tool in denied list? → DENY
3. Tool not in allowed list? → DENY
4. Policy match? → Apply rule
5. Default → ALLOW

---

## Project Structure

```
policyguard/
├── helm/
│   └── policyguard/          # Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── src/
│   ├── main.py               # Entry point
│   ├── core/
│   │   ├── server.py         # MCP server
│   │   └── utils.py          # Utilities
│   └── tools/
│       ├── validate_action.py
│       ├── register_agent.py
│       ├── create_policy.py
│       ├── get_audit_log.py
│       ├── get_compliance_status.py
│       └── report_incident.py
├── tests/
│   └── test_tools.py         # 16 unit tests
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## Technologies Used

- **FastMCP** - Python MCP server SDK
- **Pydantic** - Data validation
- **Helm** - Kubernetes packaging
- **pytest** - Testing

---

## Future Improvements

- [ ] Database backend (PostgreSQL)
- [ ] Web dashboard UI
- [ ] Prometheus metrics
- [ ] RBAC integration
- [ ] Policy versioning

---

## License

MIT License

---

## Hackathon

**MCP_HACK//26** - "MCP & AI Agents Starter Track"

This is my first MCP server project! I built PolicyGuard to learn:
- How MCP servers work
- How to expose tools to AI agents
- How to deploy MCP servers on Kubernetes
- How security/governance can be implemented at the MCP layer

### What I Built

- ✅ 6 MCP tools for security governance
- ✅ Policy engine with pattern matching
- ✅ Trust level system
- ✅ Audit logging and incident tracking
- ✅ Helm chart for Kubernetes
- ✅ 16 unit tests
- ✅ kagent integration examples
