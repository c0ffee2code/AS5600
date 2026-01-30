# Decision: Latency vs Precision Trade-off Analysis

**Date:** 2026-01-30
**Status:** Approved
**Context:** AS5600 driver for flight control test bench reference sensor

## Overview

This document records the design decisions for optimizing the AS5600 magnetic encoder driver for a flight control test bench application where the sensor is mounted at the rotation axis of a gimbal ring/lever.

**Requirements:**
- Minimal sensor latency (primary)
- Reasonable angular precision (secondary)
- Reduced noise (nice to have)

## Decision 1: Register Choice - RAW_ANGLE vs ANGLE

### Options Analyzed

| Register | Address | Description |
|----------|---------|-------------|
| RAW_ANGLE | 0x0C-0x0D | Unscaled, unmodified 12-bit angle |
| ANGLE | 0x0E-0x0F | Scaled output with 10-LSB hysteresis |

### RAW_ANGLE Characteristics
- Direct output from CORDIC algorithm (after digital filter)
- No scaling applied
- No hysteresis
- Full 12-bit resolution (4096 steps = 360°)
- Wrap-around at 0/4095 boundary

### ANGLE Characteristics
- Scaled based on ZPOS/MPOS configuration
- **10-LSB hysteresis at 0°/360° boundary** (~0.88° dead zone)
- Additional processing latency from scaling logic

### Decision: **Use RAW_ANGLE**

**Rationale:**
1. **No hysteresis artifacts** - The 10-LSB hysteresis on ANGLE creates ~0.88° dead zone, unacceptable for control loops
2. **Lower latency** - No scaling computation overhead
3. **Software handles wrap-around** - The `wrap_error()` function already handles 0/360° boundary correctly
4. **180° tilt application** - Won't hit the boundary anyway in our use case

## Decision 2: Filter Configuration

### Slow Filter (SF) Options

The AS5600 digital filter is configured via SF bits in CONF register (bits 9:8).

| SF | Settling Time | RMS Noise (1σ) | 3σ Noise | Use Case |
|----|---------------|----------------|----------|----------|
| 00 | 2.2 ms | 0.015° | ±0.045° | Static calibration |
| 01 | 1.1 ms | 0.021° | ±0.063° | Slow movements |
| 10 | 0.55 ms | 0.030° | ±0.090° | Balanced |
| **11** | **0.286 ms** | **0.043°** | **±0.129°** | **Fast control loops** |

### Fast Filter Threshold (FTH) Options

The fast filter bypasses the slow filter when input change exceeds threshold (bits 12:10).

| FTH | Threshold | Behavior |
|-----|-----------|----------|
| 000 | Disabled | Slow filter only |
| **001** | **6 LSB (~0.5°)** | **Quick response + low hold noise** |
| 010 | 7 LSB | |
| 011 | 9 LSB | |
| 100 | 18 LSB | |
| 101 | 21 LSB | |
| 110 | 24 LSB | |
| 111 | 10 LSB | |

### Power Mode (PM) Options

| PM | Mode | Polling Time | Current |
|----|------|--------------|---------|
| **00** | **NOM (always on)** | **None** | **6.5 mA** |
| 01 | LPM1 | 5 ms | 3.4 mA |
| 10 | LPM2 | 20 ms | 1.8 mA |
| 11 | LPM3 | 100 ms | 1.5 mA |

### Decision: **SF=11, FTH=001, PM=00**

**Rationale:**
- **SF=11** - Fastest filter (0.286 ms settling), acceptable noise for flight control
- **FTH=001** - Fast filter enabled at 6 LSB threshold for quick step response during movement, falls back to slow filter when holding position for better noise performance
- **PM=00** - No polling delay, always-on for consistent low latency

## Expected Performance

### Latency Budget

| Stage | Latency | Notes |
|-------|---------|-------|
| Internal ADC sampling | 150 μs | Fixed |
| Digital filter (SF=11) | 286 μs | Configurable |
| I2C read (400 kHz) | ~50 μs | 2 bytes |
| **Total** | **~486 μs** | |

### Precision

| Condition | RMS Noise | Peak-to-Peak (3σ) |
|-----------|-----------|-------------------|
| Dynamic (moving) | 0.043° | ±0.129° |
| Static (fast filter fallback) | Better | Due to FTH |

### Resolution

- 12-bit = 4096 steps per revolution
- Step size = 360° / 4096 = **0.088° per step**

## Configuration Summary

```
CONF Register (0x07-0x08) recommended settings:

Bit 13    (WD):   0    - Watchdog off
Bit 12:10 (FTH):  001  - Fast filter threshold 6 LSB
Bit 9:8   (SF):   11   - Slow filter 2x (0.286 ms)
Bit 7:6   (PWMF): 00   - PWM freq (not used for I2C)
Bit 5:4   (OUTS): 00   - Analog output (not used for I2C)
Bit 3:2   (HYST): 00   - Hysteresis off
Bit 1:0   (PM):   00   - Normal power mode (always on)

CONF value: 0b00_001_11_00_00_00_00 = 0x0700
```

## Trade-off Visualization

```
Latency ←────────────────────────────────→ Precision

SF=11 (0.286ms, 0.043°)  ←── Our choice (flight control)
SF=10 (0.55ms, 0.030°)
SF=01 (1.1ms, 0.021°)
SF=00 (2.2ms, 0.015°)    ←── Best for static measurement
```

## References

- AS5600 Datasheet v1-06 (2018-Jun-20), pages 7, 19, 28-29
- `specification/Magnetic_Rotary_Position_Sensor_AS5600_Datasheet.pdf`
