# Microsoft WebWright — Google Flights Example

> A reference implementation of the **Microsoft WebWright architecture**.
>A real-world WebWright agent that autonomously browses Google Flights, compares round-trip itineraries (HKG ⇌ CJU), and saves a structured recommendation — powered by GPT-4o, Playwright, and a three-component Runner / Model / Environment loop with built-in self-reflection.

---

## Project Structure

```
Microsoft-WebWright-Example/
├── env.py                              # Environment: shell execution, workspace I/O
├── model.py                            # Model endpoint: OpenAI GPT-4o wrapper
├── run.py                              # Runner: agent loop, orchestration, logging
├── self_reflection.py                  # Self-reflection: evaluates critical points post-run
├── requirements.txt                    # Python dependencies
├── .env                                # API key (not committed)
├── README.md                           # This file
├── skills/
│   └── google_flights_comparison.py    # Skill: task definition, metadata, workflow steps
├── workspace/                          # Agent working directory (created at runtime)
│   ├── flights_report.txt              # Final recommendation report (generated)
│   ├── flights_data.json               # Structured comparison data (generated)
│   ├── screenshots/                    # Browser screenshots captured during run
│   └── run_log_<YYYYMMDD_HHMMSS>.jsonl # Step-by-step agent log (generated)
└── final_runs/                         # Promoted artifacts after successful run
    └── run_1/
        ├── final_script.py             # The agent's final reusable script
        ├── final_script_log.txt        # Log from the final script execution
        ├── screenshots/                # Screenshots copied from workspace
        └── self_reflect_result.json    # Self-reflection evaluation output
```

---

## Skill: `google-flights-comparison`

> *Skill-guided Google Flights comparison for a Hong Kong to Jeju trip.*
> *Shows a generated flight skill being selected and reused as a task-specific workflow.*

The skill is defined in `skills/google_flights_comparison.py` and loaded by `run.py` at startup. It encapsulates all task parameters and the ordered workflow steps the agent follows.

**Skill metadata:**

| Field | Value |
|---|---|
| Route | HKG ⇌ CJU |
| Dates | 08-Aug-2026 → 14-Aug-2026 |
| Budget | HK$20,000 |
| Cabin | Economy · 1 passenger |
| Min options | 3 complete round-trip itineraries |

**Workflow steps:**

| Time | Step | Description |
|---|---|---|
| 00:00 | TASK START | Agent receives the HKG ⇌ CJU prompt with fixed dates, economy class, budget, and min 3 c |
| 01:00 | SETUP: load skill | Agent selects the `google-flights-comparison` skill to run the browser-backed workflow |
| 01:43 | BROWSER TASK START | Browser opens Google Flights scoped to HKG and CJU, form ready for date selection |
| 02:30 | DATA LOAD | First fares appear while prices are still stabilising |
| 03:20 | KEY FINDING | Cheapest nonstop option identified and recorded |
| 03:46 | RETURN SELECTION | Workflow advances to return-leg page, pairs outbound + inbound into itineraries |
| 04:08 | BALANCED OPTION | Identifies a more practical nonstop avoiding very early departures |
| 04:45 | BOOKING SOURCE CHECK | Notes the booking platform (e.g. Agoda, Google Flights direct) |
| 05:20 | COMPARISON OPTION | Third itinerary checked — may be pricier but with a later return |
| 05:56 | TASK END | Recommendation delivered, `flights_report.txt` and `flights_data.json` saved |

---

## Architecture

This project follows the three-component **WebWright** pattern:

```
User Task ——→ |          run.py (Runner)           |
              | • Initialises history with the task |
              | • Orchestrates the agent loop       |
              | • Logs every step to .jsonl         |
                        |
                  history + observation
                        ▼
              |      model.py (Model Endpoint)      |
              | • Wraps OpenAI GPT-4o API           |
              | • Sends system prompt + history     |
              | • Returns { thought, action, done } |
                        |
                predicted action (shell cmd)
                        ▼
              |        env.py (Environment)         |
              | • Executes commands in workspace/   |
              | • Captures stdout / stderr          |
              | • Reads and writes workspace files  |
                        |
                   observation
                        ————————————→ back to Runner
```

### Agent Loop — step by step

| Step | Component | What happens |
|---|---|---|
| 1 | `run.py` | Receives the task string, initialises an empty conversation history |
| 2 | `model.py` | Runner sends history → GPT-4o returns `{ thought, action, done }` |
| 3 | `env.py` | Runner passes `action` (a shell command) to `execute_command()` |
| 4 | `env.py` | `capture_observation()` formats stdout + stderr + workspace file listing |
| – | `run.py` | Runner logs the step, appends observation to history, goes to step 2 |
| – | `run.py` | Loop ends when model sets `done: true` or `MAX_STEPS` (15) is reached |

---

## WebWright Paradigm

> *"The agent can launch multiple browser sessions in terminal."*

Unlike traditional web agents that keep one browser session alive and predict the next click/type/scroll, WebWright separates the agent from the browser session entirely.

| Principle | Description | Implemented in |
|---|---|---|
| **Disposable browsers** | Agent spawns fresh browser sessions, captures screenshots only when useful, inspects failures, and reruns scripts without being trapped in a single stateful page | `execute_command()`, `take_screenshot()` |
| **Code composes actions** | Date selection, form filling, filtering, comparison, and extraction are written as loops and functions — not long chains of primitive browser actions | `write_browser_script()` |
| **Artifacts survive** | The durable output is `workspace/` — exploratory scripts, action logs, screenshots, final outputs, and eventually a reusable task program | `write_workspace_file()`, `workspace/` |

---

## File Reference

### `run.py` — Runner

| Symbol | Purpose |
|---|---|
| `TASK` | Natural-language task string given to the agent |
| `MAX_STEPS` | Hard cap on loop iterations (default: 15) |
| `run()` | Entry point — starts and drives the agent loop |
| `log_step()` | Appends one JSONL line per step to `workspace/run_log_*.jsonl` |
| `promote_to_final_run()` | Copies all workspace artifacts to `final_runs/run_N/` after completion |
| `get_next_final_run_dir()` | Returns the next available `final_runs/run_N/` path |

### `self_reflection.py` — Self-Reflection

| Symbol | Purpose |
|---|---|
| `reflect(task, report, log_entries)` | Calls GPT-4o to evaluate critical points — returns `{ task_completed, critical_points, overall_status, recommendation }` |
| `run_reflection(task, report_path, log_path, output_path)` | Loads report + log, runs reflection, saves `self_reflect_result.json` |

**Self-reflection output schema:**
```json
{
  "task_completed": true,
  "critical_points": [
    { "point": "flights found", "status": "pass", "detail": "5 outbound, 5 return" },
    { "point": "budget respected", "status": "pass", "detail": "all options under HK$20,000" }
  ],
  "overall_status": "success",
  "recommendation": "None — task fully completed."
}
```

### `model.py` — Model Endpoint

| Symbol | Purpose |
|---|---|
| `SYSTEM_PROMPT` | Instructs GPT-4o to act as a web automation agent and respond in JSON |
| `get_next_action(history)` | Calls `gpt-4o` with full history, returns `{ thought, action, done }` |

**Model response schema:**
```json
{
  "thought": "reasoning about what to do next",
  "action": "python search.py",
  "done": false
}
```

### `env.py` — Environment

| Function | Purpose |
|---|---|
| `ensure_workspace()` | Creates `workspace/` directory if it does not exist |
| `execute_command(command)` | Spawns a fresh subprocess in `workspace/` — disposable browser sessions are launched this way |
| `write_browser_script(filename, url, extraction_code)` | Writes a self-contained Playwright script to `workspace/` — agent composes full scripts instead of primitive actions |
| `take_screenshot(script_name, url)` | Spawns a disposable browser, captures a screenshot to `workspace/`, then discards the session |
| `capture_observation(cmd_result)` | Formats command result + workspace file list into an observation string |
| `read_workspace_file(filename)` | Reads a file from `workspace/` |
| `write_workspace_file(filename, content)` | Writes a file to `workspace/` — artifacts persist after the browser session is gone |
| `list_workspace_files()` | Returns list of all files currently in `workspace/` |

### `workspace/` — Agent Working Directory

Created automatically at runtime. Contains:

| File | Description |
|---|---|
| `flights_report.txt` | Final itinerary recommendation written by the agent |
| `run_log_<timestamp>.jsonl` | One JSON line per agent step: `step`, `timestamp`, `thought`, `action`, `observation` |
| *(any scripts)* | Python/shell scripts the agent writes and executes during its run |

---

## Setup

### 1 — Configure API Key

Create a `.env` file in the project root:
```
OPENAI_API_KEY=sk-...
```

### 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

### 3 — Install Playwright Browser

```bash
playwright install chromium
```

### 4 — Run

```bash
python run.py
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `openai` | 1.30.0 | GPT-4o API calls in `model.py` |
| `playwright` | 1.44.0 | Browser automation executed by the agent |
| `python-dotenv` | 1.0.1 | Loads `OPENAI_API_KEY` from `.env` |
| `requests` | 2.31.0 | Available to agent-generated scripts |

---

## Output

After a successful run you will find:

- **`workspace/flights_report.txt`** — recommended itinerary within HK$20,000
- **`workspace/run_log_<timestamp>.jsonl`** — full trace of every thought, action, and observation
