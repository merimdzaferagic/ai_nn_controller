# Amp1 Control Application (NetworkApp1)

This is an aic_app (AI Controller Application) for controlling the Amp1 (Amplifier 1) device via the Amp1 Node.

## Overview

The Amp1 Control aic_app (`aic_app.py`) is responsible for:
- Listening to measurements from the `ofc_amp1_node` (node_id = 3)
- Processing Amp1 parameters: target gain, gain tilt, target power, control mode
- Applying intelligent control logic to optimize amplifier operation
- Issuing commands to adjust Amp1 parameters based on thresholds and modes

## Architecture

```
ofc_amp1_node (Amp1 Node)
    ↓
    node_msg_broker
    ↓
NetworkApp1 (Amp1Control aic_app)
```

## Configuration

### aic_app.conf
- `ip_address`: Register service address (default: `aic_register`)
- `register_port`: Port to register aic_app (default: `5558`)

## Measurements Consumed

This aic_app listens for the following measurements from `ofc_amp1_node`:
- `amp1_target_gain` - Amplifier target gain in dB
- `amp1_gain_tilt` - Gain tilt in dB/nm
- `amp1_target_power` - Target output power in dBm
- `amp1_control_mode` - Control mode indicator

## Control Modes

The aic_app supports three control modes:

### Mode 0: Manual Monitoring
- No automatic control applied
- Displays current Amp1 parameters
- Operator can manually adjust parameters

### Mode 1: Auto-Optimize
- Automatically adjusts gain and power
- Maintains gain between 15-25 dB
- Maintains power between 10-15 dBm
- Issues commands to keep parameters within acceptable ranges

### Mode 2: Adaptive Control
- Adjusts parameters based on gain tilt
- Optimizes gain distribution when tilt is high
- Compensates for uneven spectral response

## Commands Issued

The aic_app issues commands to adjust:
- **CELL_GAIN**: Adjust target gain in dB
- **LAUNCH_POWER**: Adjust target power in dBm

## Port Allocations

- **Subscribing Measurements**: `5562` (from ofc_amp1_node)
- **Publishing Commands**: `5563` (via broker)
- **Register Connection**: `5558`

## Usage

```bash
# Run directly
python3 aic_app.py

# Run via Docker
docker-compose up
```

## Integration Flow

1. **ofc_amp1_node** fetches Amp1 parameters from Twilight REST API
2. **ofc_amp1_node** publishes measurements every 1 second
3. **NetworkApp1** listens for measurements on a 2-second interval
4. **NetworkApp1** processes measurements and applies control logic
5. **NetworkApp1** issues commands back to **ofc_amp1_node** via broker
6. **ofc_amp1_node** applies the commands to Amp1 parameters

## Example Output

```
[Amp1Control] Processing 1 measurement(s) at 1234567890.12
[Amp1Control] Latest measurements: {'amp1_target_gain': 20.5, 'amp1_gain_tilt': 0.2, 'amp1_target_power': 13.0, 'amp1_control_mode': 0}

[Amp1Control] ===== Amp1 Parameters =====
  Target Gain: 20.5 dB
  Gain Tilt: 0.2 dB/nm
  Target Power: 13.0 dBm
  Control Mode: 0
  App Control Mode: 1
====================================

[Amp1Control] Mode=1: Auto-optimize — analyzing parameters...
[Amp1Control] Target Gain 20.5 dB in acceptable range
[Amp1Control] Target Power 13.0 dBm in acceptable range
```
