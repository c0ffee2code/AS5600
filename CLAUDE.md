# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AS5600 is a MicroPython driver for the AS5600 magnetic rotary encoder sensor, designed as a reference sensor for flight control systems. The sensor communicates via I2C and provides 12-bit angular position data (4096 steps per revolution).

## Project Goals & Priorities

**Primary use case**: Reference sensor for flight control systems

**Priority 1 - Lowest Sensor Lag** ✓ Achieved:
- Use fastest filter settings (SF=11 gives 0.286ms settling time)
- Enable fast filter (FTH bits) for quick step response
- Use NOM power mode (PM=00, always on) - no polling delays

**Priority 2 - Moderate to High Angular Precision** ✓ Achieved:
- 12-bit resolution provides ~0.088° per step
- Proper handling of 0/360° wrap-around boundary for PID loops (implemented in `wrap_error()`)

**Side Goal - Noise Exploration** ✓ Achieved:
- Characterize noise at different filter settings (SF=11: 0.043° RMS, SF=00: 0.015° RMS)
- Trade-off analysis between latency and noise

## Architecture

**driver/as5600.py** - Core driver module containing:
- `AS5600` class: I2C interface for reading raw angle (0-4095 steps) and sensor status
- `to_degrees()`: Converts raw steps to relative degrees using a calibrated axis center
- `wrap_error()`: Normalizes angular errors across the 0/360° boundary for PID control loops

**tests/test_encoder.py** - Usage example demonstrating continuous angle monitoring

**specification/** - Contains AS5600 datasheet (reference for register map and timing)

**decision/** - Design decision documents:
- `LATENCY_PRECISION_TRADEOFF.md` - RAW_ANGLE vs ANGLE analysis, filter configuration choice

## Key Registers (from datasheet)

| Register | Address | Description |
|----------|---------|-------------|
| RAW_ANGLE | 0x0C-0x0D | Unfiltered 12-bit angle (currently used) |
| ANGLE | 0x0E-0x0F | Filtered/scaled angle output |
| STATUS | 0x0B | Magnet detection (MD, ML, MH bits) |
| AGC | 0x1A | Automatic gain control value |
| MAGNITUDE | 0x1B-0x1C | Magnetic field magnitude |
| CONF | 0x07-0x08 | Configuration: SF, FTH, PM, HYST, OUTS, PWMF, WD |
| ZPOS | 0x01-0x02 | Zero/start position |
| MPOS | 0x03-0x04 | Maximum/stop position |
| MANG | 0x05-0x06 | Maximum angle range |

## CONF Register Settings for Low Latency

- **SF (Slow Filter)**: bits 9:8 - Use `11` for 0.286ms settling (fastest)
- **FTH (Fast Filter Threshold)**: bits 12:10 - Enable for quick step response
- **PM (Power Mode)**: bits 1:0 - Use `00` (NOM, always on) for no polling delay
- **HYST (Hysteresis)**: bits 3:2 - 0-3 LSB to prevent toggling

## Filter Settings Trade-off (from datasheet)

| SF | Settling Time | RMS Noise (1σ) |
|----|---------------|----------------|
| 00 | 2.2 ms | 0.015° |
| 01 | 1.1 ms | 0.021° |
| 10 | 0.55 ms | 0.030° |
| 11 | 0.286 ms | 0.043° |

## Development Notes

- Python 3.13 virtual environment in `.venv/`
- No external dependencies beyond MicroPython standard library (`machine`, `micropython`)
- The `axis_center` parameter in `to_degrees()` represents the calibrated mechanical zero position
- I2C default address: `0x36`, max clock: 1 MHz (currently using 400 kHz)
- Sampling rate: 150 μs internal

## Development Milestones

### Milestone 1: Debug/Diagnostic Toolkit ✓ COMPLETE
Grep-friendly diagnostic telemetry via `diagnose()` method:
- **Single-line output** - Pipe-delimited, no interleaving issues
- **Timestamp** - `time.ticks_ms()` for time-series analysis
- **Magnet flags** - MAGNET, WEAK, STRONG
- **AGC** - Raw value and percentage (0-100)
- **Magnitude** - CORDIC magnitude value
- **Angle** - RAW steps and optional DEG if axis_center provided

Library constraint: 3.3V operation only (AGC range 0-128)

### Milestone 2: Configuration Register Access ✓ COMPLETE
Implemented CONF register read/write per [decision/LATENCY_PRECISION_TRADEOFF.md](decision/LATENCY_PRECISION_TRADEOFF.md):
- `read_conf()` / `write_conf()` - Low-level register access
- `configure_low_latency_mode()` - Convenience method applying recommended settings:
  - SF=11 (fastest filter, 0.286ms)
  - FTH=001 (fast filter threshold 6 LSB)
  - PM=00 (NOM, always on)
- CONF_LOW_LATENCY constant (0x0700) exported for direct use
- Target: ~486 μs total latency, 0.043° RMS noise

### Milestone 3: Noise Characterization (Side Goal) ✓ COMPLETE
Implemented in `tests/test_noise_levels.py`:
- Tests all SF settings (0-3) with magnet stationary
- Collects 200 samples per setting
- Calculates RMS and peak-to-peak noise in steps and degrees
- Compares measured vs expected noise from datasheet
- Summary table for easy comparison
