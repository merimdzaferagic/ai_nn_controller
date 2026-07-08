# Control Application v2 Example

Canonical reference control application for **ai_nn_controller**. A single
`aic_app.py` defines three cooperating apps that together demonstrate the
framework's command registry, validators, agent-controlled operations, plugin
dependency, and conflict-arbitration patterns.

## Apps defined here

- **`NetworkApp1`** (`aic_app_id=1`) — reads measurements from all six optical
  dummy nodes (Amp1–3, ROADM1–3, ids 3–8) and periodically sends `SET_GAIN` to
  ROADM3 (node 8). Declares `required_plugins = ["ConsolePlugin"]`, a
  `@command_validator` on `SET_GAIN` (clamps `target_gain` to 0–25 dB and
  validates `amp_type`), and an `@agent_controlled` operation `optimize_gain`
  that an AI agent can call via MCP to adjust ROADM3's preamp gain using a
  named strategy (`max_snr` / `min_power` / `balanced`).
- **`NetworkApp2`** (`aic_app_id=2`) — a simpler app that also reads Amp1/ROADM3
  and periodically sends `SET_GAIN` to node 8, intentionally conflicting with
  `NetworkApp1`.
- **`ConflictMitigatorApp`** (`aic_app_id=3`) — drains both apps' pending
  `SET_GAIN` commands to node 8 each cycle, resolves the conflict by priority
  (`NetworkApp1` > `NetworkApp2`), and re-queues only the winning command.

See :doc:`/examples/conflict_mitigation` in the Sphinx docs (or
`docs/examples/conflict_mitigation.rst`) and the repo-root `AGENT.md` for the
full explanation of this pattern.

## Plugin dependency

`NetworkApp1` requires `ConsolePlugin` (from `plugins/console_plugin/`) to be
installed. If it isn't, `AicController` raises a `RuntimeError` at startup
listing the missing plugin. See `docs/user_guide/developing_plugins.rst` for
how the plugin system works.

## Commands (`commands.py`)

| Command | Purpose |
|---|---|
| `SET_GAIN` | Set target gain for a line amp, preamp, or booster |
| `SET_VOA` | Set Variable Optical Attenuator attenuation on a channel |
| `SET_TILT` | Set spectral tilt compensation |
| `LAUNCH_POWER` | Adjust transmitter launch power |
| `CHANNEL_ALLOCATION` | Set channel allocation configuration |
| `AMPLIFIER_GAIN` | Set amplifier gain directly |

Each command has a handler plus a JSON schema used for REST validation and
MCP tool generation.

## Configuration

`aic_app.conf` only needs the register service address:

```ini
ip_address = aic_register
register_port = 5558
```

## Running

**Containerized (recommended):** this app is built and run as the `aic_server`
service in the repo-root `docker-compose.yml`:

```bash
docker compose up -d aic_server
```

> Note: the standalone `docker-compose.yml` in this directory is stale (it
> references a nonexistent `run_server.py` and `ofc_amp1_node`) and is not
> used by the actual stack — the root compose file is authoritative.

**Local/direct run:**

```bash
python3 aic_app.py --verbose
```
