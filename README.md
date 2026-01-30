# AS5600 MicroPython Driver

A minimalistic MicroPython driver for the AS5600 12-bit magnetic rotary position sensor, designed for low-latency angle reading in flight control applications.

## Features

- **Low-latency design** - Uses RAW_ANGLE register (~486 μs total latency)
- 12-bit angular position (4096 steps per revolution, ~0.088° resolution)
- Sensor health monitoring (magnet detection, field strength)
- Diagnostic telemetry with grep-friendly output
- PID-friendly angle wrapping across 0/360° boundary

See [decision/LATENCY_PRECISION_TRADEOFF.md](decision/LATENCY_PRECISION_TRADEOFF.md) for design rationale.

## Hardware Requirements

- AS5600 magnetic encoder module (e.g., Adafruit)
- **3.3V operation** (library constraint - 5V mode not supported)
- Diametrically magnetized magnet positioned above sensor
- I2C connection (default address: 0x36)

## Installation

Copy `driver/as5600.py` to your MicroPython device.

## Quick Start

```python
from machine import I2C, Pin
from as5600 import AS5600, to_degrees

# Initialize I2C and encoder
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400_000)
encoder = AS5600(i2c)

# Read raw angle (0-4095 steps)
raw = encoder.read_raw_angle()

# Convert to degrees relative to mechanical center
AXIS_CENTER = 422  # Calibrate for your setup
angle_deg = to_degrees(raw, AXIS_CENTER)

# Check if magnet is detected (via diagnostic output)
diag = encoder.diagnose()
print(diag)

# Generate diagnostic telemetry
print(encoder.diagnose(axis_center=AXIS_CENTER))
```

## API Reference

### `AS5600(i2c, address=0x36)`

Initialize the driver.

- `i2c`: MicroPython I2C instance
- `address`: I2C address (default 0x36)

### `read_raw_angle() -> int`

Returns raw angle in steps (0-4095).

### `diagnose(axis_center=None) -> str`

Returns grep-friendly diagnostic telemetry string. See [Diagnostic Output](#diagnostic-output) section.

### `to_degrees(raw_angle, axis_center) -> float`

Converts raw steps to degrees relative to axis center, with proper 0/360° wrap handling.

### `wrap_error(err) -> int`

Normalizes angular error to [-2048, +2047] range for PID control loops.

### `read_conf() -> int`

Reads the CONF register (0x07-0x08) and returns the 16-bit configuration value.

### `write_conf(value)`

Writes a 16-bit value to the CONF register. Changes take effect immediately but are not persistent across power cycles.

### `configure_low_latency_mode()`

Configures the sensor for low-latency flight control applications with optimal settings:
- SF=11: Fastest filter (0.286ms settling)
- FTH=001: Fast filter threshold at 6 LSB
- PM=00: Always-on power mode

See [decision/LATENCY_PRECISION_TRADEOFF.md](decision/LATENCY_PRECISION_TRADEOFF.md) for detailed rationale.

## Diagnostic Output

The `diagnose()` method returns a single-line, pipe-delimited string for easy parsing:

```
AS5600|TS=123456|MAGNET=true|WEAK=false|STRONG=false|AGC=85|AGC_PCT=66|MAG=1847|RAW=422|DEG=0.0
```

### Fields

| Field | Description |
|-------|-------------|
| TS | Timestamp in milliseconds since boot |
| MAGNET | Magnet detected (true/false) |
| WEAK | Magnet too weak flag |
| STRONG | Magnet too strong flag |
| AGC | Raw AGC value (0-128) |
| AGC_PCT | AGC as percentage (0-100) |
| MAG | CORDIC magnitude value |
| RAW | Raw angle in steps (0-4095) |
| DEG | Relative angle in degrees (if axis_center provided) |

### Parsing Example

```bash
# Filter for AGC readings
cat telemetry.log | grep "AS5600" | grep "AGC_PCT"

# Extract specific field
cat telemetry.log | grep "AS5600" | cut -d'|' -f6
```

## AGC Interpretation Guide

The AGC (Automatic Gain Control) value indicates magnetic field strength and is key for optimal sensor performance.

| AGC % | Status | Meaning | Recommended Action |
|-------|--------|---------|-------------------|
| 0-20% | `low` | Magnet too strong | Increase air gap between magnet and sensor |
| 20-40% | acceptable | Strong but usable | Consider increasing gap slightly |
| **40-60%** | **`optimal`** | **Ideal range** | **Best noise performance** |
| 60-80% | acceptable | Weak but usable | Consider reducing gap slightly |
| 80-100% | `high` | Magnet too weak | Reduce air gap or use stronger magnet |

### Optimal Setup Procedure

1. Position magnet above sensor (typical air gap: 0.5-3mm)
2. Run diagnostic: `print(encoder.diagnose())`
3. Check `AGC_PCT` value
4. Adjust air gap until AGC is in 40-60% range
5. Verify `MAGNET=true` and `WEAK=false` and `STRONG=false`

## Noise Characterization Results

**Test date:** 2026-01-31
**Test script:** `tests/test_noise_levels.py`
**Samples:** 200 per SF setting, magnet stationary

| SF | Settling Time | Expected RMS | Measured RMS | Measured P-P |
|----|---------------|--------------|--------------|--------------|
| 0  | 2.2 ms        | 0.015°       | 0.000°       | 0.000°       |
| 1  | 1.1 ms        | 0.021°       | 0.000°       | 0.000°       |
| 2  | 0.55 ms       | 0.030°       | 0.011°       | 0.088°       |
| 3  | 0.286 ms      | 0.043°       | 0.006°       | 0.088°       |

**Observations:**
- All measured values are better than datasheet specifications
- SF=0 and SF=1 show zero noise (below 12-bit resolution of 0.088°/step)
- SF=3 (low-latency config) shows only 1-step occasional jitter
- SF=3 is the minimum filtering available (2x averaging); filters cannot be fully disabled

**Conclusion:** The low-latency configuration (SF=3) provides excellent noise performance in practice, validating its use for flight control applications.

## Troubleshooting

### No magnet detected (`MAGNET=false`)

- Verify magnet is positioned above sensor
- Check magnet is diametrically magnetized (not axially)
- Reduce air gap
- Verify I2C connection

### Magnet too weak (`WEAK=true`, high AGC)

- Reduce air gap between magnet and sensor
- Use stronger magnet (recommended: 30-90 mT field strength)
- Check for magnetic interference from nearby components

### Magnet too strong (`STRONG=true`, low AGC)

- Increase air gap
- Use weaker magnet or add non-magnetic spacer

### Noisy angle readings

- Check AGC is in optimal range (40-60%)
- Verify magnet is centered over sensor
- Check for mechanical vibration or magnet wobble
- See [Filter Configuration](decision/LATENCY_PRECISION_TRADEOFF.md#decision-2-filter-configuration) for tuning options
- Run noise characterization: `tests/test_noise_levels.py`

## Calibrating Axis Center

The `axis_center` parameter defines the mechanical zero position:

1. Move mechanism to desired center/neutral position
2. Read raw angle: `center = encoder.read_raw_angle()`
3. Use this value as `axis_center` in your application
4. Re-calibrate after mechanical changes (reassembly, etc.)

```python
# Calibration
print(f"Center position: {encoder.read_raw_angle()}")
# Note this value and use it as AXIS_CENTER constant
```

## License

MIT
