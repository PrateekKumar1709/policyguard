# PolicyGuard

**Security & Governance for AI Agents using kagent + agentgateway**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![kagent](https://img.shields.io/badge/kagent-compatible-green.svg)](https://kagent.dev/)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PolicyGuard is an AI agent security solution built with **kagent** and **agentgateway** for the **MCP_HACK//26** hackathon in the **"Secure & Govern MCP"** category.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [Features](#features)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [MCP Tools](#mcp-tools)
- [Configuration](#configuration)
- [Testing](#testing)
- [Security Model](#security-model)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview

As AI agents become more autonomous, organizations need robust controls to govern their behavior. PolicyGuard provides a complete security solution using the kagent ecosystem:

```
┌─────────────────────────────────────────────────────────────────┐
│                     kagent Agent                                │
│              (policyguard-agent)                                │
│                                                                 │
│  "Before ANY action, I MUST call validate_action"              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     agentgateway                                │
│                                                                 │
│  • Rate limiting        • CORS policies                        │
│  • Request logging      • Protocol security                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/MCP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PolicyGuard MCP Server                      │
│                                                                 │
│  • validate_action      • create_policy                        │
│  • register_agent       • get_audit_log                        │
│  • report_incident      • get_compliance_status                │
└─────────────────────────────────────────────────────────────────┘
```

### What This Demonstrates

| Hackathon Technology | How We Use It |
|---------------------|---------------|
| **kagent** | Creates the `policyguard-agent` - an AI agent that enforces security policies |
| **agentgateway** | Proxies and secures MCP traffic with rate limiting and observability |
| **MCP** | PolicyGuard exposes 6 security tools via Model Context Protocol |

---

## Architecture

### Three-Layer Security

```
User Request
     │
     ▼
┌────────────────┐
│ kagent Agent   │  Layer 1: Agent-Level Security
│                │  - System prompt enforces "validate before action"
│                │  - A2A skills for security tasks
└────────────────┘
     │
     ▼
┌────────────────┐
│ agentgateway   │  Layer 2: Network-Level Security
│                │  - Rate limiting (100 req/min)
│                │  - CORS policies
│                │  - Request/response logging
└────────────────┘
     │
     ▼
┌────────────────┐
│ PolicyGuard    │  Layer 3: Application-Level Security
│ MCP Server     │  - Policy-based access control
│                │  - Trust level enforcement
│                │  - Audit trail & incidents
└────────────────┘
```

---

## Components

### 1. PolicyGuard MCP Server (`helm/policyguard/`)

The core MCP server providing security tools:

- **validate_action** - Gate every action against security policies
- **register_agent** - Manage agent identities and trust levels
- **create_policy** - Define security rules
- **get_audit_log** - Query action history
- **get_compliance_status** - Security metrics dashboard
- **report_incident** - Track security violations

### 2. PolicyGuard Agent (`helm/policyguard-agent/`)

A kagent `Agent` custom resource that:

- Uses PolicyGuard as its MCP server
- Has a system prompt requiring security validation
- Exposes A2A skills for security operations

### 3. agentgateway (`helm/agentgateway/`)

Proxies MCP traffic with:

- Rate limiting protection
- CORS configuration
- Request logging
- Protocol-level security

---

## Features

| Feature | Component | Description |
|---------|-----------|-------------|
| **Policy Enforcement** | MCP Server | Evaluate actions against security rules |
| **Trust Levels** | MCP Server | low, medium, high, admin hierarchy |
| **Auto-Registration** | MCP Server | Unknown agents get minimal trust |
| **Incident Tracking** | MCP Server | Automatic violation logging |
| **Rate Limiting** | agentgateway | Prevent abuse (100 req/min default) |
| **Audit Trail** | MCP Server | Complete action history |
| **A2A Skills** | kagent Agent | Security operations as callable skills |

---

## Quick Start

### Prerequisites

- Kubernetes cluster (Kind, Minikube, or cloud)
- Helm 3.x
- kagent installed ([kagent.dev](https://kagent.dev))
- kubectl

### 1. Install kagent CRDs

```bash
# Install kagent (follow kagent.dev docs)
helm repo add kagent https://kagent.dev/charts
helm install kagent kagent/kagent -n kagent-system --create-namespace
```

### 2. Deploy PolicyGuard Stack

```bash
# Create namespace
kubectl create namespace policyguard

# Deploy PolicyGuard MCP Server
helm install policyguard ./helm/policyguard -n policyguard

# Deploy agentgateway (optional, adds rate limiting)
helm install agentgateway ./helm/agentgateway -n policyguard

# Deploy the kagent Agent
helm install policyguard-agent ./helm/policyguard-agent -n policyguard
```

### 3. Verify Deployment

```bash
# Check pods
kubectl get pods -n policyguard

# Check the kagent Agent
kubectl get agents -n policyguard

# Check RemoteMCPServer registration
kubectl get remotemcpservers -n policyguard
```

---

## Deployment

### Option A: Full Stack (Recommended)

Deploy all three components for complete security:

```bash
# 1. PolicyGuard MCP Server
helm install policyguard ./helm/policyguard -n policyguard

# 2. agentgateway for network security
helm install agentgateway ./helm/agentgateway -n policyguard \
  --set policyguardUrl=http://policyguard:8000/mcp

# 3. kagent Agent that uses PolicyGuard
helm install policyguard-agent ./helm/policyguard-agent -n policyguard \
  --set policyguardUrl=http://agentgateway:3000/mcp
```

### Option B: MCP Server Only

For integration with existing agents:

```bash
helm install policyguard ./helm/policyguard -n policyguard
```

### Option C: Local Development

```bash
# Start PolicyGuard locally
python src/main.py --transport http --port 8000

# Run with agentgateway (requires agentgateway binary)
agentgateway --config agentgateway/config-local.yaml
```

---

## MCP Tools

### validate_action

**The primary security gate.** Must be called before any action.

```json
{
  "action_type": "tool_call",
  "target": "delete_records",
  "agent_id": "my-agent",
  "parameters": "{}",
  "context": "User requested deletion"
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

### register_agent

Register an agent with a trust level.

```json
{
  "agent_id": "data-processor",
  "name": "Data Processing Agent",
  "trust_level": "medium",
  "allowed_tools": ["read_*"],
  "denied_tools": ["delete_*"]
}
```

### create_policy

Create a security policy.

```json
{
  "policy_id": "block-deletes",
  "name": "Block Delete Operations",
  "rules": "[{\"condition\": {\"tool_pattern\": \"delete_*\", \"trust_level_below\": \"admin\"}, \"action\": \"deny\"}]",
  "priority": 100
}
```

### get_audit_log

Query the audit trail.

```json
{
  "agent_id": "my-agent",
  "limit": 50,
  "include_allowed": true
}
```

### get_compliance_status

Get security metrics.

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

### report_incident

Report a security incident.

```json
{
  "agent_id": "suspicious-agent",
  "incident_type": "unauthorized_access",
  "severity": "critical",
  "description": "Attempted credential access",
  "auto_suspend": true
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POLICYGUARD_DATA_DIR` | `data` | Data storage directory |
| `MCP_TRANSPORT_MODE` | `stdio` | Transport: `stdio` or `http` |
| `HOST` | `0.0.0.0` | HTTP server host |
| `PORT` | `8000` | HTTP server port |

### Policy Rules

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
      "message": "Delete requires admin trust"
    }
  ],
  "enabled": true,
  "priority": 100
}
```

### agentgateway Configuration

```yaml
binds:
  - port: 3000
    listeners:
      - routes:
          - policies:
              rateLimit:
                requestsPerMinute: 100
                burstSize: 20
            backends:
              - mcp:
                  targets:
                    - name: policyguard
                      http:
                        url: http://policyguard:8000/mcp
```

---

## Testing

### Unit Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest tests/ -v
```

### Test Output

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

### Integration Test

```bash
# Deploy to Kind cluster
./scripts/setup-kind.sh

# Port forward
kubectl port-forward -n policyguard svc/policyguard 8000:8000

# Test MCP endpoint
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## Security Model

### Trust Level Hierarchy

| Level | Score | Access |
|-------|-------|--------|
| `low` | 1 | Read-only, auto-registered agents |
| `medium` | 2 | Standard operations |
| `high` | 3 | Sensitive operations |
| `admin` | 4 | Full access, destructive operations |

### Policy Evaluation Order

1. Check if agent is suspended → **DENY**
2. Check `denied_tools` list → **DENY if matched**
3. Check `allowed_tools` list → **DENY if not in list**
4. Evaluate policies by priority → **Apply matching rule**
5. Default → **ALLOW**

### Agent System Prompt (kagent)

The kagent agent is instructed to:

```
CRITICAL RULE: Before performing ANY action, you MUST call 
validate_action to check if the action is permitted. 
Never bypass this security check.
```

---

## Project Structure

```
policyguard/
├── helm/
│   ├── policyguard/           # MCP Server Helm chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── configmap.yaml
│   │       └── remotemcpserver.yaml
│   │
│   ├── policyguard-agent/     # kagent Agent Helm chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       ├── agent.yaml           # kagent Agent CR
│   │       └── remotemcpserver.yaml
│   │
│   └── agentgateway/          # agentgateway Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           └── configmap.yaml
│
├── agentgateway/              # Local agentgateway configs
│   ├── config.yaml
│   └── config-local.yaml
│
├── src/                       # PolicyGuard MCP Server
│   ├── main.py
│   ├── core/
│   │   ├── server.py
│   │   └── utils.py
│   └── tools/
│       ├── validate_action.py
│       ├── register_agent.py
│       ├── create_policy.py
│       ├── get_audit_log.py
│       ├── get_compliance_status.py
│       └── report_incident.py
│
├── tests/                     # Unit tests
│   └── test_tools.py
│
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## License

MIT License

---

## Hackathon

**MCP_HACK//26** - "Secure & Govern MCP" Category

This project demonstrates:

| Requirement | Implementation |
|-------------|----------------|
| **Use kagent** | `policyguard-agent` - A kagent Agent that enforces security |
| **Use agentgateway** | Network-level security with rate limiting and logging |
| **Build MCP Server** | PolicyGuard provides 6 security tools via MCP |
| **Security Focus** | Policy-based access control, trust levels, audit trail |
| **Kubernetes Native** | Full Helm chart deployment |

### Technologies Used

- **kagent** - AI agent platform for Kubernetes
- **agentgateway** - MCP data plane for security
- **FastMCP** - Python MCP server SDK
- **Helm** - Kubernetes package manager
