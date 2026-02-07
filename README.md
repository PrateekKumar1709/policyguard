# PolicyGuard

**Security & Governance MCP Server for AI Agent Deployments**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PolicyGuard is an MCP (Model Context Protocol) server that provides policy-based access control, incident tracking, and compliance monitoring for AI agents. Built for the **MCP_HACK//26** hackathon in the **"Secure & Govern MCP"** category.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [MCP Tools](#mcp-tools)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Testing](#testing)
- [Integration with kagent](#integration-with-kagent)
- [Using Different LLM Providers](#using-different-llm-providers)
- [Performance](#performance)
- [Project Structure](#project-structure)
- [Security Model](#security-model)
- [License](#license)

---

## Overview

As AI agents become more autonomous and powerful, organizations need robust security controls to govern their behavior. PolicyGuard acts as a **security gateway** that:

1. **Validates agent actions** before execution against configurable policies
2. **Tracks incidents** when agents attempt unauthorized operations
3. **Provides compliance metrics** for security auditing
4. **Maintains audit logs** of all agent activities

### Why PolicyGuard?

- **Zero Trust for AI** - Don't trust agents by default; verify every action
- **Policy as Code** - Define security rules in JSON, version control them
- **Real-time Enforcement** - Sub-millisecond validation latency
- **Complete Audit Trail** - Every action is logged for compliance

---

## Features

| Feature | Description |
|---------|-------------|
| **Policy Enforcement** | Evaluate agent actions against configurable security policies with wildcard pattern matching |
| **Trust Levels** | Assign agents trust levels (low, medium, high, admin) to control access |
| **Auto-Registration** | Unknown agents are automatically registered with minimal trust |
| **Incident Tracking** | Policy violations are automatically logged as security incidents |
| **Auto-Suspension** | Agents can be automatically suspended after critical incidents |
| **Compliance Dashboard** | Real-time security metrics including violation counts and agent status |
| **Audit Trail** | Complete log of all agent actions with timestamps and decisions |
| **Pattern Matching** | Flexible wildcard patterns for tool matching (`delete_*`, `*_production`) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Agent / LLM                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ MCP Protocol
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PolicyGuard                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Validate   │  │   Policy    │  │   Audit     │             │
│  │   Action    │  │   Engine    │  │    Log      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Register   │  │  Incident   │  │ Compliance  │             │
│  │   Agent     │  │  Tracker    │  │  Reporter   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────┐
                    │   Data Storage    │
                    │  (JSON Files)     │
                    └───────────────────┘
```

**Data Flow:**
1. Agent requests action validation via MCP
2. PolicyGuard evaluates against registered policies
3. Decision (allow/deny) is logged to audit trail
4. Violations create incidents automatically
5. Compliance metrics are updated in real-time

---

## MCP Tools

PolicyGuard exposes 6 MCP tools:

### 1. `validate_action`

**The primary security gate.** Agents should call this BEFORE performing any sensitive action.

```json
{
  "action_type": "tool_call",
  "target": "database_delete",
  "agent_id": "prod-agent-01",
  "parameters": "{\"table\": \"users\"}",
  "context": "Cleanup stale records"
}
```

**Response:**
```json
{
  "action_id": "act_a1b2c3d4e5f6",
  "allowed": false,
  "reason": "Delete operations require admin trust level",
  "warnings": []
}
```

### 2. `register_agent`

Register a new agent with a specific trust level.

```json
{
  "agent_id": "data-processor-01",
  "name": "Data Processing Agent",
  "trust_level": "medium",
  "description": "Processes daily data imports",
  "allowed_tools": ["read_*", "write_staging_*"],
  "denied_tools": ["*_production"]
}
```

### 3. `create_policy`

Create a security policy with rules.

```json
{
  "policy_id": "prod-safety",
  "name": "Production Safety Policy",
  "description": "Restrict production access",
  "rules": "[{\"condition\": {\"tool_pattern\": \"*_production\", \"trust_level_below\": \"admin\"}, \"action\": \"deny\", \"message\": \"Production access requires admin\"}]",
  "priority": 100
}
```

### 4. `get_audit_log`

Query the audit log with filters.

```json
{
  "agent_id": "data-processor-01",
  "limit": 50,
  "include_allowed": true
}
```

### 5. `get_compliance_status`

Get real-time compliance metrics.

```json
{}
```

**Response:**
```json
{
  "total_agents": 5,
  "active_agents": 4,
  "suspended_agents": 1,
  "total_policies": 3,
  "recent_violations": 12,
  "compliance_score": 87.5
}
```

### 6. `report_incident`

Manually report a security incident.

```json
{
  "agent_id": "suspicious-agent",
  "incident_type": "unauthorized_access",
  "severity": "critical",
  "description": "Agent attempted to access encrypted credentials",
  "auto_suspend": true
}
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Local Installation

```bash
# Clone the repository
git clone https://github.com/your-org/policyguard.git
cd policyguard

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Or with uv
uv sync
```

### Docker

```bash
docker build -t policyguard:latest .
docker run -p 8000:8000 policyguard:latest
```

---

## Quick Start

### 1. Start the Server

```bash
# stdio mode (for local MCP clients)
python src/main.py

# HTTP mode (for network access)
python src/main.py --transport http --port 8000
```

### 2. Test with Python

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

### 3. Test with curl (HTTP mode)

```bash
# Start server in HTTP mode
python src/main.py --transport http --port 8000

# Call MCP endpoint
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "validate_action",
      "arguments": {
        "action_type": "tool_call",
        "target": "read_data",
        "agent_id": "test-agent"
      }
    },
    "id": 1
  }'
```

---

## Kubernetes Deployment

PolicyGuard includes a Helm chart for Kubernetes deployment.

### Using Kind (Local Development)

```bash
# Create Kind cluster
kind create cluster --name policyguard

# Build and load image
docker build -t policyguard:latest .
kind load docker-image policyguard:latest --name policyguard

# Deploy with Helm
kubectl create namespace policyguard
helm install policyguard ./helm/policyguard -n policyguard

# Verify deployment
kubectl get pods -n policyguard
kubectl get svc -n policyguard

# Port forward to access locally
kubectl port-forward -n policyguard svc/policyguard 8000:8000
```

### Helm Values

Key configuration options in `values.yaml`:

```yaml
# Enable kagent integration (requires kagent CRDs)
kagentIntegration:
  enabled: false

# Resource limits
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi

# Default security policy
config:
  defaultPolicy:
    rules:
      - condition:
          tool_pattern: "delete_*"
          trust_level_below: "admin"
        action: "deny"
        message: "Delete operations require admin trust level"
```

### With kagent

To integrate with kagent, enable the RemoteMCPServer resource:

```bash
helm install policyguard ./helm/policyguard -n policyguard \
  --set kagentIntegration.enabled=true
```

This creates a `RemoteMCPServer` custom resource that registers PolicyGuard with the kagent controller.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POLICYGUARD_DATA_DIR` | `data` | Directory for JSON data files |
| `MCP_TRANSPORT_MODE` | `stdio` | Transport mode: `stdio` or `http` |
| `HOST` | `0.0.0.0` | HTTP server host |
| `PORT` | `8000` | HTTP server port |

### Policy Rules

Policies are defined as JSON with conditions and actions:

```json
{
  "id": "example-policy",
  "name": "Example Policy",
  "rules": [
    {
      "condition": {
        "tool_pattern": "delete_*",
        "trust_level_below": "admin"
      },
      "action": "deny",
      "message": "Delete operations require admin trust level"
    },
    {
      "condition": {
        "tool_pattern": "read_*",
        "trust_level_at_least": "low"
      },
      "action": "allow"
    }
  ],
  "enabled": true,
  "priority": 100
}
```

**Condition Fields:**
- `tool_pattern`: Glob pattern to match tool names (`*` is wildcard)
- `action_type`: Type of action (`tool_call`, `resource_access`, etc.)
- `trust_level_at_least`: Minimum trust level required
- `trust_level_below`: Apply rule if agent trust is below this level

**Actions:**
- `allow`: Permit the action
- `deny`: Block the action
- `require_approval`: Flag for human approval (not auto-denied)

---

## Testing

### Run Unit Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src
```

### Test Output

```
tests/test_tools.py::TestValidateAction::test_allow_read_for_low_trust PASSED
tests/test_tools.py::TestValidateAction::test_deny_delete_for_low_trust PASSED
tests/test_tools.py::TestValidateAction::test_allow_delete_for_admin PASSED
tests/test_tools.py::TestValidateAction::test_deny_suspended_agent PASSED
tests/test_tools.py::TestValidateAction::test_auto_register_unknown_agent PASSED
tests/test_tools.py::TestValidateAction::test_action_id_generated PASSED
tests/test_tools.py::TestRegisterAgent::test_register_new_agent PASSED
tests/test_tools.py::TestRegisterAgent::test_reject_invalid_trust_level PASSED
tests/test_tools.py::TestRegisterAgent::test_warn_on_admin_registration PASSED
tests/test_tools.py::TestCreatePolicy::test_create_valid_policy PASSED
tests/test_tools.py::TestCreatePolicy::test_reject_empty_rules PASSED
tests/test_tools.py::TestCreatePolicy::test_reject_invalid_action PASSED
tests/test_tools.py::TestGetAuditLog::test_get_audit_log_structure PASSED
tests/test_tools.py::TestGetAuditLog::test_filter_by_agent PASSED
tests/test_tools.py::TestReportIncident::test_report_incident PASSED
tests/test_tools.py::TestReportIncident::test_auto_suspend_on_critical PASSED

============================== 16 passed ==============================
```

### Testing with Ollama (Free Local LLM)

```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai

# Pull a model
ollama pull llama3.2

# Start PolicyGuard
python src/main.py --transport http --port 8000

# Configure your MCP client to use PolicyGuard
# The LLM will call PolicyGuard tools through MCP
```

---

## Integration with kagent

[kagent](https://kagent.dev) is a platform for deploying AI agents on Kubernetes. PolicyGuard integrates seamlessly:

### As a RemoteMCPServer

```yaml
apiVersion: kagent.dev/v1alpha2
kind: RemoteMCPServer
metadata:
  name: policyguard
spec:
  description: "Security & Governance MCP Server"
  protocol: STREAMABLE_HTTP
  url: http://policyguard.policyguard:8000/mcp
  timeout: 30s
```

### Agent Configuration

Configure your kagent agents to use PolicyGuard:

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: my-agent
spec:
  mcpServers:
    - name: policyguard
  systemPrompt: |
    IMPORTANT: Before performing any action, you MUST call the
    validate_action tool to check if you are allowed to proceed.
```

---

## Using Different LLM Providers

PolicyGuard is LLM-agnostic. Here's how to use it with various providers:

### Ollama (Free, Local)

```bash
# Start PolicyGuard
python src/main.py --transport http --port 8000

# Use with Ollama via MCP client
# The client handles tool invocation
```

### Claude (Anthropic)

```python
import anthropic

client = anthropic.Anthropic(api_key="your-key")

# Claude supports MCP natively
# Configure PolicyGuard as an MCP server
```

### OpenAI

```python
from openai import OpenAI

client = OpenAI(api_key="your-key")

# Use function calling with PolicyGuard tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "validate_action",
            "description": "Validate if an agent can perform an action",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string"},
                    "target": {"type": "string"},
                    "agent_id": {"type": "string"}
                },
                "required": ["action_type", "target", "agent_id"]
            }
        }
    }
]
```

### Groq (Free Tier)

```python
from groq import Groq

client = Groq(api_key="your-key")
# Similar function calling interface as OpenAI
```

---

## Performance

PolicyGuard is designed for minimal latency overhead:

| Metric | Value |
|--------|-------|
| Average validation latency | **< 1ms** |
| P99 validation latency | **< 5ms** |
| Memory footprint | **~50MB** |
| Startup time | **< 2s** |

### Benchmark

```python
import time
from src.tools.validate_action import validate_action

# Warm up
validate_action.fn(action_type="tool_call", target="test", agent_id="bench")

# Benchmark 1000 validations
start = time.perf_counter()
for _ in range(1000):
    validate_action.fn(action_type="tool_call", target="read_data", agent_id="bench")
elapsed = time.perf_counter() - start

print(f"1000 validations: {elapsed*1000:.2f}ms")
print(f"Per validation: {elapsed:.4f}ms")
```

**Result:** ~0.78ms per validation

This is **negligible** compared to LLM inference time (typically 1-30+ seconds).

---

## Project Structure

```
policyguard/
├── helm/policyguard/           # Helm chart for Kubernetes
│   ├── Chart.yaml              # Chart metadata
│   ├── values.yaml             # Default configuration
│   └── templates/              # Kubernetes manifests
│       ├── _helpers.tpl        # Template helpers
│       ├── configmap.yaml      # Default policies
│       ├── deployment.yaml     # Pod deployment
│       ├── remotemcpserver.yaml # kagent integration
│       ├── service.yaml        # Service exposure
│       └── serviceaccount.yaml # RBAC
├── src/                        # Python source code
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── core/                   # Core modules
│   │   ├── __init__.py
│   │   ├── server.py           # MCP server implementation
│   │   └── utils.py            # Shared utilities
│   └── tools/                  # MCP tools
│       ├── __init__.py
│       ├── validate_action.py  # Primary security gate
│       ├── register_agent.py   # Agent registration
│       ├── create_policy.py    # Policy management
│       ├── get_audit_log.py    # Audit log queries
│       ├── get_compliance_status.py # Compliance metrics
│       └── report_incident.py  # Incident reporting
├── tests/                      # Unit tests
│   ├── __init__.py
│   └── test_tools.py           # Tool tests (16 tests)
├── Dockerfile                  # Container image
├── pyproject.toml              # Python project config
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

---

## Security Model

### Trust Levels

| Level | Score | Typical Use Case |
|-------|-------|------------------|
| `low` | 1 | Unknown/auto-registered agents, read-only access |
| `medium` | 2 | Verified agents, standard operations |
| `high` | 3 | Trusted agents, sensitive operations |
| `admin` | 4 | Full access, destructive operations |

### Policy Evaluation Order

1. Check if agent is suspended → **DENY**
2. Check agent's `denied_tools` list → **DENY if matched**
3. Check agent's `allowed_tools` list → **DENY if not in list**
4. Evaluate policies by priority (highest first) → **Apply matching rule**
5. Default → **ALLOW** (if no policy denies)

### Automatic Protections

- **Auto-registration**: Unknown agents get `low` trust
- **Auto-suspension**: Critical incidents can auto-suspend agents
- **Audit everything**: All actions logged, successful or not
- **Incident tracking**: Violations create trackable incidents

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Hackathon

Built for **MCP_HACK//26** in the **"Secure & Govern MCP"** category.

PolicyGuard addresses the critical need for security and governance in AI agent deployments by providing:

- ✅ Policy-based access control
- ✅ Trust level management
- ✅ Incident tracking and auto-response
- ✅ Complete audit trail
- ✅ Real-time compliance metrics
- ✅ Kubernetes-native deployment
- ✅ kagent integration
