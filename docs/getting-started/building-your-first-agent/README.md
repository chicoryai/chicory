# Building Your First Agent Cookbook

This cookbook provides a comprehensive guide to creating, evaluating, and deploying your first **Chicory AI** agent. You'll learn the complete **Agent Development Life Cycle (ADLC)** from initial creation to production deployment.

Whether you're new to AI agents or transitioning from other platforms, this step-by-step guide will help you build a robust, production-ready agent.

---

## Quick Start

Chicory offers **two flexible approaches** to build and manage your agents:

### 1. Platform Approach (Visual Dashboard)
1. Log into the Chicory AI dashboard and set up your organization/project
2. Create your first agent with proper integrations (data, code, documents, tools)
3. Define evaluation criteria and upload a validation dataset
4. Run evaluations to test and improve your agent iteratively
5. Deploy your agent using the REST API or MCP Gateway with proper authentication

### 2. MCP Tools Approach (Natural Language)
1. Connect Chicory's MCP tools to your preferred LLM interface (Claude Desktop, IDEs, etc.)
2. Build agents conversationally using natural language commands
3. Iterate locally with full tool access and context
4. Validate your agent thoroughly before deployment
5. Publish to Chicory for production-ready deployment

---

## Contents

- [Agent Creation](docs/1-agent-creation.md) - Building agents using the Platform or MCP tools
  - **Part 1: Platform Approach** - Visual dashboard for agent creation
  - **Part 2: MCP Tools Approach** - Natural language agent building
- [Evaluation](docs/2-evaluation.md) - Testing and iterating on your agent using validation datasets
- [Deployment](docs/3-deployment.md) - Deploying your agent to production using the REST API or MCP Gateway

---

## What You'll Learn

- **Agent Creation**: How to build agents using either the visual platform or natural language MCP tools
- **MCP Integration**: Leverage local or cloud LLMs to interact with Chicory through conversational commands
- **Evaluation Framework**: Understanding the Agent Development Life Cycle (ADLC) and validation processes
- **Iterative Improvement**: Using evaluation results to evolve your agent through multiple iterations
- **Production Deployment**: Securely deploying agents using API tokens and proper authentication

---

## Prerequisites

- Access to Chicory AI dashboard
- Basic understanding of AI agents and their use cases
- API token for deployment (generated from Chicory platform)

---

## Agent Development Life Cycle (ADLC)

This cookbook follows the complete ADLC process:

1. **Build** - Create your agent with proper configurations
2. **Evaluate** - Test against validation datasets with defined criteria
3. **Evolve** - Iterate based on evaluation results and feedback
4. **Deploy** - Push to production using REST API or MCP Gateway
5. **Monitor** - Track performance and make ongoing improvements
