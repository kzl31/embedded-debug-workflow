# Embedded Firmware Debugging Workflow Skill

> An automated debugging assistant skill for embedded development, designed for VS Code Copilot Agent and compatible with other capable coding agents.

<p align="center">
  <a href="README.md"><strong>🇨🇳 中文 README</strong></a>
</p>   

## Overview

This skill defines an end-to-end embedded firmware debugging workflow, covering the complete process from issue discovery to a standardized debugging report:

```text
Issue discovery -> Fault classification -> CHESHI instrumentation iterations
-> Automated build and flash -> Serial log analysis -> Business logic fix
-> Regression verification -> Standardized report
```

The workflow definition is centralized in [`flow.yaml`](flow.yaml), which contains a globally numbered linear step table. The [`workflow_engine.py`](scripts/workflow_engine.py) engine performs table lookup and sequence transitions without hard-coding individual workflow steps.

## Use Cases

| Scenario | Examples |
|:---|:---|
| Wired protocol failures | Modbus, CAN, SPI, or TTL communication faults |
| Data parsing errors | Invalid lengths, offsets, or CRC checks |
| State-machine failures | Stalled states or incorrect transitions |
| Peripheral driver issues | Flash or sensor read timeouts |

## Repository Structure

```text
embedded-debug-workflow/
|-- README.md                    # Chinese documentation
|-- README_EN.md                 # English documentation
|-- SKILL.md                     # Agent entry point and mandatory rules
|-- flow.yaml                    # Single source of truth for workflow steps
|-- commands/                    # /kzl command definitions
|   |-- help.md
|   |-- init.md
|   |-- build.md
|   `-- add-flow.md
|-- scripts/
|   |-- config_reader.py         # Configuration management
|   |-- keil_build.py            # Single-project Keil build
|   |-- keil_flash.py            # Single-project firmware flash
|   |-- build_and_flash.py       # Single-project build and flash
|   |-- multi_project_runner.py  # Per-project build/flash/serial modes
|   |-- serial_read.py           # One-shot serial capture
|   |-- serial_monitor.py        # Continuous serial monitoring
|   |-- batch_build.py           # Batch project operations
|   `-- workflow_engine.py       # Sequence-driven workflow engine
|-- refs/                        # Detailed rules and references
|-- templates/                   # Reports, checklists, and code templates
`-- data/
    `-- debug-history.yaml       # Debug history index
```

## Requirements

| Dependency | Purpose |
|:---|:---|
| Python 3.8+ | Runs the automation scripts |
| PyYAML | Parses `flow.yaml` (`pip install pyyaml`) |
| pyserial | Captures serial output (`pip install pyserial`) |
| Keil MDK | ARM firmware build environment |
| J-Link or ST-Link | Firmware programming and debugging |

The default Keil executable path is:

```text
C:\Keil_v5\UV4\UV4.exe
```

It can be changed in `.copilot/embedded-debug-config.json`.

## Quick Start

### 1. Initialize the workflow

```powershell
python scripts/workflow_engine.py --init --project "<workspace>"
```

Initialization creates the workflow state. If the workspace configuration does not exist, the workflow generates a two-project template at:

```text
<workspace>/.copilot/embedded-debug-config.json
```

Initialization does not scan the workspace for project files. Edit the generated configuration and provide the actual project paths, Keil project files, serial ports, and debugger settings.

### 2. Run the current workflow step

```powershell
python scripts/workflow_engine.py --project "<workspace>" --mode 1
```

The engine returns one of the following states:

- `awaiting_ai`: the agent must perform an analysis, edit, question, report, or regression step.
- `auto_pending`: the engine executed an automated step and advanced the workflow.
- `awaiting_user`: manual action is required before continuing with `--wake`.
- `completed`: the workflow has finished.

After completing an AI-owned step, acknowledge the result:

```powershell
python scripts/workflow_engine.py --project "<workspace>" --ack success
python scripts/workflow_engine.py --project "<workspace>" --ack failure
```

## Multi-Project Configuration

The `projects` array in `embedded-debug-config.json` is the authoritative project list. Users may add, remove, or reorder entries. The runtime does not rely on `project_count` to determine how many projects exist.

Example:

```json
{
  "keil": {
    "uv4_path": "C:\\Keil_v5\\UV4\\UV4.exe"
  },
  "projects": [
    {
      "name": "controller",
      "dir": "E:\\firmware\\controller\\MDK-ARM",
      "file": "controller.uvprojx",
      "serial": {
        "port": "COM19",
        "baud": 256000,
        "data_bits": 8,
        "stop_bits": 1,
        "parity": "None"
      },
      "debugger": {
        "type": "JLink",
        "com": "COM9"
      }
    }
  ]
}
```

Each project receives an independent execution mode:

| Mode | Behavior |
|:---|:---|
| `full` | Build, flash, and monitor serial output |
| `compile_only` | Build only |
| `none` | Skip the project |

The default recommendation is to compile only the project associated with the current source file and skip all other projects. Flashing requires explicit user confirmation and must never be selected as the implicit default.

## Single-Project Commands

The single-project scripts retain index `0` as their CLI default. In a multi-project workspace, callers should always pass the selected project index explicitly:

```powershell
# Build project 1 only
python scripts/keil_build.py --config-dir "<workspace>" --project-index 1

# Flash project 1 only
python scripts/keil_flash.py --config-dir "<workspace>" --project-index 1

# Build and flash project 1
python scripts/build_and_flash.py --config-dir "<workspace>" --project-index 1
```

## Typical Debugging Flow

1. Ensure the workspace configuration exists.
2. Read the actual `projects` array and choose an independent execution mode for every project.
3. Locate suspicious source code and insert CHESHI-controlled observations.
4. Build, flash, and capture serial logs according to each project's mode.
5. Iterate until the evidence identifies a root cause.
6. Fix the business logic and add falsifiable temporary verification observations.
7. Rebuild, flash, and verify the fix from serial evidence.
8. Remove all CHESHI instrumentation and temporary verification code.
9. Rebuild, run regression checks, and generate the final report.

## CHESHI Instrumentation Rules

- `CHESHI` is the only temporary debugging switch.
- Every added debug print, helper, capture buffer, flush path, and temporary verification check must be wrapped by CHESHI conditional compilation.
- Communication layers, ISRs, DMA callbacks, and protocol callbacks must not call `printf` directly.
- Timing-sensitive code should only capture compact event or data snapshots.
- Formatting and output must be performed from the `main` loop through a function such as `Debug_Flush()`.
- Instrumentation should cover function entry and exit, important branches, state transitions, lengths, indexes, errors, timeouts, retries, counters, and required frame summaries.
- Once the fix is verified, remove the CHESHI definition, snapshots, buffers, flush calls, prints, and temporary verification checks as one complete block.

See [`refs/cheshi-macro.md`](refs/cheshi-macro.md) for the complete specification.

## Workflow Limits and Safety Rules

- The workflow allows up to eight instrumentation iterations before requesting human assistance.
- Build, flash, analysis, and reporting operations must follow the sequence defined in `flow.yaml`.
- A successful build or flash is not proof that the bug is fixed. Verification must use evidence directly related to the root cause.
- The workflow must distinguish between "the fault did not occur during this run" and "the conditions that caused the fault have been eliminated."
- Temporary debugging code and permanent business logic fixes must remain separable.

## Reports

After verification, the workflow generates a Markdown report containing:

- Fault description
- Root cause
- Fix summary
- Changed files
- Verification logs
- Regression result

Reports and serial logs are stored under the target workspace's `.copilot` directory.

## License

Add a license file before publishing or redistributing the repository if you want to define explicit reuse terms.