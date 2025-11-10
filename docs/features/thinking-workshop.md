# Thinking Workshop

The Thinking Workshop is Open Notebook's multi-agent deliberation system that enables AI agents to collaborate, debate, and synthesize insights on research topics.

## Overview

The Thinking Workshop supports different modes of multi-agent collaboration:

- **Dialectical Analysis**: Supporter and Critic agents debate a topic across multiple rounds, with a Synthesizer providing the final judgment
- **Brainstorm Mode**: Multiple agents with different perspectives generate creative ideas and explore possibilities

## Key Features

### Real-Time Streaming (SSE)

The Thinking Workshop uses Server-Sent Events (SSE) for real-time streaming of agent responses, providing a more engaging user experience compared to traditional polling.

#### How It Works

1. **Frontend initiates SSE connection** to `/api/workshops/sessions/stream`
2. **Backend creates session** and starts multi-agent workflow
3. **Agents execute** with tools (notebook_reader, tavily_search, calculator)
4. **Responses stream** immediately after each agent completes
5. **Heartbeat mechanism** prevents HTTP buffering with keepalive comments every 2 seconds

#### SSE Implementation Details

**Backend** (`api/routers/thinking_workshop.py`):
- Uses `StreamingResponse` with `text/event-stream` media type
- Implements heartbeat task to prevent buffering
- Sends events: `session_created`, `agent_start`, `agent_chunk`, `session_complete`

**Frontend** (`frontend/src/lib/hooks/use-workshop.ts`):
- Connects directly to backend (`http://localhost:5055`) to bypass Next.js proxy buffering
- Parses SSE events and updates UI in real-time
- Falls back to polling mode if SSE connection fails

#### Key Technical Solutions

**Problem**: Next.js development proxy buffers SSE responses, causing all events to arrive at once.

**Solution**: Frontend connects directly to backend, bypassing Next.js proxy:
```typescript
const response = await fetch('http://localhost:5055/api/workshops/sessions/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(request),
})
```

**Heartbeat Mechanism**: Prevents HTTP buffering by sending SSE comment lines every 2 seconds:
```python
async def heartbeat():
    while True:
        await asyncio.sleep(2)
        event_queue.put_nowait({'type': 'heartbeat'})

# In event loop:
if event['type'] == 'heartbeat':
    yield ": keepalive\n\n"  # Browser ignores but forces buffer flush
```

### Batch Streaming Mode

Since agents use tools (notebook_reader, web search), true character-level streaming isn't possible. Instead, we use **batch streaming**:

- Agent executes and calls tools synchronously
- Once agent completes, full response is sent immediately (0 latency)
- Next agent starts, repeats the process
- Much faster than polling (which has 3-second intervals)

**Performance Comparison**:
- **Polling**: 13 requests over 40 seconds, 1.5s average latency
- **SSE Batch Streaming**: 1 connection, 0s latency per agent, 20 heartbeats
- **Improvement**: 92% fewer HTTP requests, 100% reduction in polling latency

### Tool Integration

Agents can use three types of tools:

1. **notebook_reader**: Reads all sources and notes from the notebook
   - Provides complete context to agents
   - Handles async database queries in new event loop
   - Returns up to 5 sources and 10 notes

2. **tavily_search**: Web search for current information
   - Requires `TAVILY_API_KEY` environment variable
   - Returns structured JSON with results

3. **calculator**: Safe mathematical expression evaluation
   - Validates data accuracy in papers
   - Uses AST parsing (no eval)

### Final Report Generation

The `_generate_report()` method creates a structured Markdown report:

```
================================================================================
  Dialectical Analysis - Discussion Report
================================================================================

📌 Topic: [Topic]
📝 Mode: [Mode Description]
⏰ Time: [Timestamp]
🔄 Rounds: X rounds
💬 Messages: Y messages

## 🧑 Supporter

### Round 1

**🔧 Tools Used:**

- **notebook_reader**: Read 1 source(s) and 6 note(s) (paper.md)
- **tavily_search**: Found 5 web results. Top: "..." (url)

**💬 Response:**

[Supporter's argument]

### Round 2

...

## 😈 Critic

...

## ⚖️ Synthesizer

**💬 Response:**

## Overall Score: X/10

## Key Strengths (2-3 items)
- [Evidence-backed strength]

## Key Weaknesses (1-2 items)
- [Evidence-backed weakness]

## Final Recommendation: Accept / Borderline / Reject
**Reasoning**: [1-2 sentences]
```

**Format Improvements**:
- `### Round N` for clear round headers
- `**🔧 Tools Used:**` (bold with emoji) instead of `*Tools:*` (italic)
- Each tool call: `- **tool_name**: summary` (bold tool name)
- `**💬 Response:**` header for agent content

## Configuration

### Agent Profiles

Agent configurations are defined in `open_notebook/thinking_workshop/agent_profiles.yaml`:

```yaml
dialectical_mode:
  name: "Dialectical Analysis"
  description: "Critical academic paper review"
  agents:
    - id: supporter
      tools: ["notebook_reader", "tavily_search", "calculator"]
      temperature: 0.8
    - id: critic
      tools: ["notebook_reader", "tavily_search"]
      temperature: 0.9
    - id: synthesizer
      tools: []
      temperature: 0.7
  workflow:
    type: "sequential"
    rounds: 4  # 4 rounds of debate (S→C→S→C→S→C→S→C) + Synthesizer
```

### Environment Variables

No additional configuration required beyond existing API keys:
- `OPENAI_API_KEY` or other provider keys for agent LLMs
- `TAVILY_API_KEY` for web search tool (optional)

## Usage

### From UI

1. Navigate to a notebook
2. Switch to "Thinking Workshop" tab
3. Select a template (Dialectical Analysis / Brainstorm)
4. Enter discussion topic
5. Click "Start Discussion"
6. Watch agents collaborate in real-time via SSE

### From API

```bash
# Create and stream session
curl -N http://localhost:5055/api/workshops/sessions/stream \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "notebook_id": "notebook:xxx",
    "mode": "dialectical_mode",
    "topic": "Analyze the Transformer architecture",
    "context": {}
  }'

# List templates
GET /api/workshops/templates

# Get session details
GET /api/workshops/sessions/{session_id}

# Get final report
GET /api/workshops/sessions/{session_id}/report
```

## Troubleshooting

### SSE Not Streaming

**Symptoms**: All events arrive at once at the end instead of progressively.

**Diagnosis**:
1. Test with curl: `curl -N http://localhost:5055/api/workshops/sessions/stream ...`
2. If curl works but browser doesn't → Frontend buffering issue
3. If curl also buffered → Backend issue

**Solutions**:
- Frontend connects directly to backend (bypasses Next.js proxy)
- Heartbeat mechanism sends keepalive every 2 seconds
- SSE comments force HTTP buffer flushing

### notebook_reader Returns Empty

**Symptoms**: Tool call shows `Result: (empty)` or error message.

**Diagnosis**: Check backend logs for `[notebook_reader]` entries:
```
[notebook_reader] Step 1: Getting notebook notebook:xxx
[notebook_reader] Step 2: Getting sources and notes
[notebook_reader] Found X sources and Y notes
[notebook_reader] Fetching source 1/X: source:xxx
[notebook_reader] ✓ Added source: Title (chars)
[notebook_reader] SUCCESS: Returning N chars total
```

**Common Issues**:
- Database connection fails in new thread/event loop
- Notebook has no sources or notes
- Sources have no `full_text` content

**Solution**: Enhanced logging shows exact failure point. If database connection fails, the tool returns clear error message instead of empty string.

### Layout Issues

**Page Layout**: Chat column takes 50% width, Sources and Notes share the other 50% (25% each).

Modified in `frontend/src/app/(dashboard)/notebooks/[id]/page.tsx`:
```tsx
// Changed from grid-cols-3 to grid-cols-2
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    <SourcesColumn /> {/* 25% */}
    <NotesColumn />   {/* 25% */}
  </div>
  <ChatColumn />      {/* 50% */}
</div>
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  useWorkshop Hook                                     │  │
│  │  - Manages SSE connection                             │  │
│  │  - Parses events (session_created, agent_chunk, etc)  │  │
│  │  - Updates streaming messages Map                     │  │
│  │  - Falls back to polling on error                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↓ SSE                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ http://localhost:5055/api/...
┌──────────────────────────┴──────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  /api/workshops/sessions/stream                       │  │
│  │  - Creates session                                    │  │
│  │  - Starts workflow in background task                 │  │
│  │  - Yields SSE events via queue                        │  │
│  │  - Heartbeat task sends keepalive every 2s            │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ThinkingWorkshopService                              │  │
│  │  - run_session_streaming(stream_callback)             │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  WorkflowEngine                                       │  │
│  │  - Orchestrates multi-agent workflow                  │  │
│  │  - LangGraph sequential execution                     │  │
│  │  - Calls stream_callback on agent completion          │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  AgentExecutor                                        │  │
│  │  - Executes single agent with tools                   │  │
│  │  - Tool calling via LangChain                         │  │
│  │  - Returns {content, tool_calls}                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  WorkshopTools                                        │  │
│  │  - notebook_reader (async in new thread)              │  │
│  │  - tavily_search                                      │  │
│  │  - calculator                                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Related Documentation

- [REST API Reference](../development/api-reference.md) - Complete API documentation
- [Architecture](../development/architecture.md) - System design overview
- [AI Models](ai-models.md) - Multi-provider AI configuration

## References

- [SSE Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [LangChain Tool Calling](https://python.langchain.com/docs/modules/agents/agent_types/react)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
