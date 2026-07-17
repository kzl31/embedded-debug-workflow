# Embedded Firmware Debugging Workflow Skill

> An automated debugging assistant skill for embedded development, designed for VS Code Copilot Agent and compatible with other capable coding agents.

<p align="center">
  <a href="README.md"><strong>🇨🇳 中文 README</strong></a>
</p>

## 📖 Overview

This skill defines a complete automated embedded firmware debugging workflow, covering the entire chain from issue discovery to standardized report output:

```text
Issue discovery → Fault classification → CHESHI instrumentation iterations → Automated build and flash
→ Serial log analysis → Business code fix → Regression verification → Standardized report
```

The workflow definition is centralized in the single file **`flow.yaml`** (a linearly numbered step table). The engine logic lives in the `scripts/engine/` package (table lookup + sequence jump resolver, zero hardcoded steps); `scripts/workflow_engine.py` is only a CLI entry that forwards to this package. Runtime parameters and workspace paths are centralized in `scripts/skill-config.json`; Python scripts access them through `scripts/path_config.py`.

The engine is split by single responsibility into the following modules; all files are available under `scripts/engine/`:

| Module file | Responsibility |
|:---|:---|
| `engine/__init__.py` | Package exports, exposing `WorkflowEngine` and `main` |
| `engine/constants.py` | Engine constants and paths (Skill dir resolution, `flow.yaml` path, action type classification AUTO/AI/TERMINATE, state encryption key) |
| `engine/utils.py` | Pure utility functions: JSON/YAML loading, template path substitution, time/value parsing, XOR+base64 lightweight encryption/decryption, config fingerprint |
| `engine/state.py` | Workflow state `flow-gate.json` read/write and default structure: path resolution, progress toggle, encrypted read / atomic write / concurrency protection |
| `engine/conditions.py` | Condition evaluation and state writes: dotted-path reads, AI param placeholder expansion, condition expression comparison, state field write/increment |
| `engine/executors.py` | Concrete executors: locate script absolute path, run external Python scripts and collect per-project results, check file existence |
| `engine/auto_steps.py` | Auto-step driving and flow control: chained advancement, single-step execution (assert → action → branch), action dispatch, goto/exit/wait/log primitives |
| `engine/ai_instructions.py` | AI step instructions and terminal states: generate AI work instructions, minimal progress payload, waiting/completed output |
| `engine/config_sync.py` | Config and project-mode sync: respond to `--set`, reload and validate config, generate run state per project mode, derive execution capabilities |
| `engine/core.py` | Engine core: load `flow.yaml`/`flow-gate`, basic queries, sequence advancement, public entry `run/ack/wake/show_status/reset/init`, unified result construction |
| `engine/workflow.py` | `WorkflowEngine` composition class: multiple-inheritance aggregation of each Mixin, identical interface/behavior to the original single-file engine |
| `engine/cli.py` | CLI entry `argparse`/`main`: `--init/--mode/--ack/--wake/--reset/--set/--reload-config`, identical behavior to the original engine |

## 🎯 Use Cases

| Scenario | Description |
|:---|:---|
| Wired communication protocol faults | Modbus / CAN / SPI / TTL communication failures |
| Data parsing errors | Invalid length / offset / CRC checks |
| State-machine anomalies | Stuck states, incorrect transition logic |
| Basic peripheral driver issues | Flash / sensor read timeouts |

## Installation

This repository contains one Skill. Use this public source for all installations:

<https://github.com/kzl31/embedded-debug-workflow>

The following commands perform a global, non-interactive installation.

### GitHub Copilot

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent github-copilot --global --yes
```

### Claude Code

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent claude-code --global --yes
```

### Codex

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent codex --global --yes
```

### Cursor

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent cursor --global --yes
```

List, update, or remove global Skills:

```powershell
npx skills list --global
npx skills update --global --yes
npx skills remove embedded-debug-workflow --global --yes
```

Reload the target agent or restart the editor after installation.

## 📁 Repository Structure

```text
embedded-debug-workflow/
├── README.md              # Chinese documentation
├── README_EN.md           # English documentation (this file)
├── SKILL.md               # AI core entry (hard rules + engine invocation + flow.yaml quick reference)
├── flow.yaml              # 🔑 Single source of truth for the workflow (linear numbered steps, with phase grouping)
├── commands/              # /kzl command entry points
│   ├── help.md            #   /kzl help
│   ├── init.md            #   /kzl init (initialize configuration)
│   ├── build.md           #   /kzl build (compile only) / /kzl build-flash (build + flash)
│   └── add-flow.md        #   /kzl add-flow (add step/phase → edit flow.yaml)
├── scripts/               # Python automation scripts
│   ├── config_reader.py   #   Config read/write (Python)
│   ├── keil_build.py      #   Keil build (Python)
│   ├── keil_flash.py      #   Firmware flash (Python)
│   ├── build_and_flash.py #   One-click build + flash (Python)
│   ├── serial_read.py     #   One-shot serial read (Python)
│   ├── serial_monitor.py  #   Continuous serial monitoring (Python)
│   ├── batch_build.py     #   Batch operations across projects (Python)
│   ├── multi_project_runner.py # Per-project build/flash/serial by mode
│   ├── path_config.py     #   Centralized path and runtime-parameter interface
│   ├── skill-config.json  #   Single source for paths, defaults, and timeouts
│   ├── engine/            #   🔑 Modular workflow engine (table lookup + sequence jump, zero hardcoded steps)
│   │   ├── __init__.py    #   Package exports (WorkflowEngine, main)
│   │   ├── constants.py   #   Engine constants & paths, action types, encryption key
│   │   ├── utils.py       #   Pure utilities (IO / crypto / parse / fingerprint)
│   │   ├── state.py       #   flow-gate state read/write & default structure
│   │   ├── conditions.py  #   Condition evaluation & state writes
│   │   ├── executors.py   #   External script & file-check executors
│   │   ├── auto_steps.py  #   Auto-step driving & flow control
│   │   ├── ai_instructions.py # AI step instructions & terminal states
│   │   ├── config_sync.py #   Config & project-mode sync
│   │   ├── core.py        #   Init / query / main entry / result builder
│   │   ├── workflow.py    #   WorkflowEngine composition class (Mixins)
│   │   └── cli.py         #   argparse entry main()
│   └── workflow_engine.py #   Engine CLI entry (delegates to engine/ package)
├── refs/                  # Detailed specs loaded by AI on demand
│   ├── core-rules.md      #   Mandatory rules (AI behavior constraints)
│   ├── script-commands.md #   Script command reference
│   ├── config-format.md   #   Config file format
│   ├── debug-loop.md      #   Core debug loop (8-iteration)
│   ├── git-rules.md       #   Git local version management
│   ├── cheshi-macro.md    #   CHESHI macro spec (incl. ISR-safe printing)
│   ├── pause-scenarios.md #   Manual pause spec
│   ├── common-faults.md   #   Common faults quick lookup & JLink/Map analysis
│   ├── add-flow-guide.md  #   Add step/phase guide (edit flow.yaml)
│   ├── runtime-config.md  #   Centralized runtime configuration rules
│   └── workflow-diagram.md#   Full workflow diagram (interactive + sequence)
├── templates/             # Templates
│   ├── checklist.md       #   Iteration checklist (with verification & FAQ)
│   ├── report.md          #   Fault report template
│   ├── flow-gate.json     #   State file template (currentSeq, etc.)
│   └── cheshi_snippet.c   #   CHESHI macro code template
└── data/                  # Skill history index (auto-generated / configuration-controlled)
  └── debug-history.yaml #   Debug history index
```

### Workspace file locations

Workspace configuration, workflow state, build/flash/serial logs, and reports are not
written into the Skill repository. Their locations are resolved from the `paths` section
of `scripts/skill-config.json` through `scripts/path_config.py`.

Project logs use unique names such as `build_log_p<index>_<name>.txt`,
`flash_log_p<index>_<name>.txt`, `debug_log_p<index>_<name>.txt`, and
`verify_log_p<index>_<name>.txt`.

When changing a directory or filename, edit only `scripts/skill-config.json`.
Do not duplicate path construction in Python, YAML, or Markdown.

## 🔧 Requirements

| Dependency | Description |
|:---|:---|
| **Python 3.8+** | Runs the Python automation scripts (recommended) |
| **pyserial** | Serial communication (`pip install pyserial`) |
| **PyYAML** | Parses `flow.yaml` (`pip install pyyaml`) |
| **Keil MDK** | ARM build environment (UV4.exe, fixed path `C:\Keil_v5\UV4\UV4.exe`) |
| **J-Link / ST-Link** | Debugger / programmer |

## 🚀 Quick Start

### Startup / initialization flow

Once the skill is activated, the AI drives the engine in the following pattern (**the only workflow entry point**):

```text
① New conversation → run engine --init to initialize state, without asking the user
② If config is missing, scan the current VS Code workspace and generate the configuration in the workspace data directory resolved from `skill-config.json`
③ Read the actual projects array from config; ask per-project execution mode (build+flash / compile-only / none)
④ Run engine --mode 0 to read current state (current seq / phase / todo)
⑤ Run engine --mode 1 to execute/advance the current step:
   - Auto steps (run_script/check_file/...): engine executes directly and jumps per on_success/on_failure
     until it hits an AI step or completion
   - AI steps (ask_user/edit_source/analyze/report/...): engine outputs an instruction (status=awaiting_ai);
     after the AI acts, submit --ack success (or --ack failure)
   - Manual pause (wait_user): status=awaiting_user; after handling, --wake to resume
⑥ Repeat ④~⑤ until status=completed
```

Common commands:

```powershell
# ① initialize state (no prompt)
python scripts/workflow_engine.py --init --project "<workspace>"

# ④ read current state (seq / phase / todo)
python scripts/workflow_engine.py --project "<workspace>" --mode 0

# ⑤ execute / advance current step
python scripts/workflow_engine.py --project "<workspace>" --mode 1

# after an AI step, submit the result
python scripts/workflow_engine.py --project "<workspace>" --ack success
python scripts/workflow_engine.py --project "<workspace>" --ack failure
```

> Initialization recursively scans the workspace for Keil projects, preserves existing manual parameters, and appends newly discovered projects. The actual configuration path is resolved centrally.
> All workflow logic (step order, jumps, conditions) lives in `flow.yaml`; the engine merely executes by looking up `seq`.

### Typical debugging flow

```text
1. STARTUP auto-ensures the workspace Keil configuration exists
2. AI confirms whether to use the current or newly modified config, then asks per-project modes from the final configProjects (seq 1)
3. AI quickly reviews source/history, then asks structured fault questions and a separate final supplement question (seq 2~3)
4. AI injects the CHESHI debug macro only when it is worthwhile and can produce new evidence; otherwise it fixes build/connection/config issues first (seq 6~11)
5. AI analyzes logs and iteratively locates the root cause (seq 10, return to seq 6 if needed)
6. After locating the root cause, fix the business code first while keeping CHESHI observation points
7. Rebuild, flash, and continuously read serial logs to confirm the fault is fully resolved; on failure return to the debug loop
8. After confirmation, clean up CHESHI, then build, run regression verification, and output the report
```

## 📝 Key Conventions

- **CHESHI macro**: bitmask or numeric levels; debug logging is not mandatory every round. It should be added only when AI judges it can provide new evidence for the current fault stage. All debug content must be wrapped by CHESHI. Communication layers only capture snapshots; the `main` loop outputs uniformly; delete the whole block when debugging ends.
- **Git control**: local operations only, `git push` is forbidden; debug branch naming `debug/<fault-brief>_YYYYMMDD`.
- **8-iteration limit**: after 8 rounds of auto-instrumentation still unable to locate the fault → trigger human assistance (`wait_user`).
- **Three types of pause**: device power-cycle restart / Keil breakpoint debugging / iteration-limit assistance.

## 📄 Report Template

After the fault is resolved, a standardized report is automatically generated, containing: fault description, root cause analysis, changed-files list, verification results, and impact scope.
