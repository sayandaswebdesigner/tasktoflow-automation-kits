# TaskToFlow Automation Kits

Production-ready Python, MCP Agent Security, and n8n Infrastructure starters featured on [@TaskToFlow](https://www.youtube.com/@TaskToFlow).

## Kits Included

| Kit | Folder | What It Solves |
|---|---|---|
| **10-Second Offline Data Cleaner** | [`10-second-ai-data-cleaner/`](10-second-ai-data-cleaner/) | Deduplicates messy CSVs, preserves true financial `NaN`s (no silent zero-fill), parses mixed ISO/US/EU dates, and runs a 10,000-row benchmark locally. |
| **Claude + MCP Sanitizer & HITL Gate** | [`claude-cowork-mcp-security/`](claude-cowork-mcp-security/) | Stops prompt-injected PDFs/emails from triggering sensitive DB writes or payouts using field allowlists, schema validation, and Human-in-the-Loop confirmation. |
| **n8n Production Queue Mode** | [`n8n-production-docker-redis/`](n8n-production-docker-redis/) | Separates n8n Main UI, Redis/BullMQ queue, PostgreSQL persistence, and scalable Worker containers for high-throughput reliability. |

## Quick Start

```bash
git clone https://github.com/sayandaswebdesigner/tasktoflow-automation-kits.git
cd tasktoflow-automation-kits
```
