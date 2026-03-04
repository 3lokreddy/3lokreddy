# 👋 Hi, I'm @3lokreddy

- 👀 Interested in AutoGPT, multi-agent AI, and autonomous systems
- 🌱 Building things with AI — agents, orchestration, and plugins
- 💞️ Looking to collaborate on AI plugins and the power of Claude / ChatGPT

---

## 🤖 Multi-Agent Orchestration System

A production-ready **multi-agent AI framework** built on top of the [Anthropic API](https://docs.anthropic.com/) (Claude). The system uses an **Orchestrator** to decompose complex goals into sub-tasks and dispatches them to specialised agents that collaborate via shared memory.

### Architecture

```
User Goal
    │
    ▼
┌─────────────┐
│ Orchestrator│  ← Plans & routes tasks, synthesises final answer
└──────┬──────┘
       │  SharedMemory (results, messages, context)
   ┌───┴───────────────────────────┐
   │           │          │        │
   ▼           ▼          ▼        ▼
┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Rese- │ │ Coder  │ │Analyst │ │Reviewer│
│archer│ │        │ │        │ │        │
└──────┘ └────────┘ └────────┘ └────────┘
   │           │          │        │
   └─── Tools: web_search, execute_code, file_ops ───┘
```

### Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Researcher** | Web research, fact-finding, summaries | `web_search`, `file_ops` |
| **Coder** | Write, test & debug Python code | `execute_code`, `file_ops` |
| **Analyst** | Data analysis, statistics, insights | `execute_code`, `file_ops` |
| **Reviewer** | Quality-check outputs, rate & flag issues | `execute_code`, `file_ops` |

### Orchestration Strategies

| Strategy | When used |
|----------|-----------|
| **sequential** | Tasks must run in order (each uses prior results) |
| **parallel** | Independent tasks run concurrently (ThreadPoolExecutor) |
| **pipeline** | Researcher → Coder/Analyst → Reviewer fixed flow |

The orchestrator automatically selects the best strategy using Claude.

### Tools

| Tool | Description |
|------|-------------|
| `web_search` | Live web search (stub by default; plug in Tavily/SerpAPI) |
| `execute_code` | Run Python snippets in a sandboxed subprocess |
| `file_ops` | Read/write files in a sandboxed workspace directory |

---

### Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/3lokreddy/3lokreddy.git
cd 3lokreddy/multi_agent_system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 4. Run with a custom goal
python main.py --goal "Write a Python binary search tree with unit tests"

# 5. Or start the interactive REPL
python main.py --interactive
```

### Using Individual Agents

```python
from memory.shared_memory import SharedMemory
from agents import ResearcherAgent, CoderAgent

memory = SharedMemory()

# Researcher
researcher = ResearcherAgent(memory=memory)
result = researcher.run("What are the key differences between LLM agents and traditional AI?")
print(result)

# Coder
coder = CoderAgent(memory=memory)
code = coder.run("Write a Python async HTTP client with retry logic")
print(code)
```

### Using the Orchestrator

```python
from orchestrator import Orchestrator

orch = Orchestrator(verbose=True)

result = orch.run(
    "Research how transformer attention works, "
    "then implement a minimal self-attention layer in Python, "
    "and review the code for correctness."
)
print(result)
```

### Running Examples

```bash
cd multi_agent_system
python examples/example_tasks.py
```

Five built-in examples covering research, coding, analysis, pipeline, and data tasks.

---

### Project Structure

```
multi_agent_system/
├── main.py                  # CLI entry point
├── orchestrator.py          # Orchestrator (planner + synthesiser)
├── requirements.txt
├── agents/
│   ├── base_agent.py        # Abstract base with agentic tool-use loop
│   ├── researcher.py
│   ├── coder.py
│   ├── analyst.py
│   └── reviewer.py
├── tools/
│   ├── web_search.py        # Web search (stub + Tavily provider)
│   ├── file_ops.py          # Sandboxed file read/write
│   └── code_executor.py     # Safe Python subprocess executor
├── memory/
│   └── shared_memory.py     # Key-value store + message bus + result store
└── examples/
    └── example_tasks.py     # 5 runnable demos
```

---

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | **Yes** | Your Anthropic API key |
| `SEARCH_PROVIDER` | No | `stub` (default) or `tavily` |
| `TAVILY_API_KEY` | If Tavily | Tavily search API key |
| `AGENT_WORKSPACE` | No | Directory for file_ops (default `/tmp/agent_workspace`) |

---

> Built with the Anthropic Claude API by @3lokreddy

<!---
3lokreddy/3lokreddy is a ✨ special ✨ repository because its `README.md` (this file) appears on your GitHub profile.
You can click the Preview link to take a look at your changes.
--->
