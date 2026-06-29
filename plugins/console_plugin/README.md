# console_plugin

A dummy plugin for `ai_nn_controller` that prints structured messages to stdout.

This is the **reference implementation** — the minimum required structure for any
plugin in the ecosystem. Real plugins replace the `print` calls with SDK calls to
InfluxDB, MLflow, Prometheus, ModelRDB, etc.

## Install

```bash
pip install -e plugins/console_plugin/
```

## API

| Method | Description |
|---|---|
| `log(message, level="INFO")` | Free-form message |
| `log_measurement(node_id, data)` | Latest measurement snapshot for a node |
| `log_command(command, payload)` | A command being sent |
| `log_event(event, **kwargs)` | Named event with arbitrary key/value metadata |

## Usage in a control app

```python
from ai_nn_controller import AicApp, aic_app

@aic_app(name="MyApp")
class MyApp(AicApp):
    required_plugins = ["ConsolePlugin"]
    read_measurements = {3: ["gain", "power"]}

    @classmethod
    def process(cls, measurements):
        console = cls.plugins["ConsolePlugin"]
        latest = measurements.get(3, [{}])[-1]
        console.log_measurement(3, latest)
        console.log_event("process_tick", app="MyApp")
```

## Entry-point group

Plugins are discovered via the `ai_nn_controller.plugin_init` entry-point group.
If `console-plugin` is not installed, any control app that declares
`required_plugins = ["ConsolePlugin"]` will raise a `RuntimeError` at controller
startup with a clear message listing what is missing.
