"""
AS5600 Noise Characterization Script

Measures angular noise at different slow filter (SF) settings.
Run with magnet stationary to characterize sensor noise floor.

Expected results (from datasheet):
| SF | Settling | RMS Noise |
|----|----------|-----------|
| 0  | 2.2 ms   | 0.015°    |
| 1  | 1.1 ms   | 0.021°    |
| 2  | 0.55 ms  | 0.030°    |
| 3  | 0.286 ms | 0.043°    |
"""

from micropython import const
from machine import I2C, Pin
import time
import math

from as5600 import AS5600, DEG_PER_STEP, CONF_SF_MASK, CONF_FTH_MASK

# SF filter settings to test
SF_SETTINGS = [
    (0, "SF=0 (2.2ms, expect 0.015°)"),
    (1, "SF=1 (1.1ms, expect 0.021°)"),
    (2, "SF=2 (0.55ms, expect 0.030°)"),
    (3, "SF=3 (0.286ms, expect 0.043°)"),
]

# Test parameters
SAMPLES_PER_TEST = const(200)
SETTLE_TIME_MS = const(50)


def set_slow_filter(encoder, sf):
    """Set SF bits in CONF register, disable fast filter for pure SF measurement."""
    conf = encoder.read_conf()
    # Clear SF and FTH bits, then set new SF value (FTH=0 disables fast filter)
    conf = (conf & ~(CONF_SF_MASK | CONF_FTH_MASK)) | ((sf & 0x03) << 8)
    encoder.write_conf(conf)


def collect_samples(encoder, n):
    """Collect N raw angle samples."""
    samples = []
    for _ in range(n):
        samples.append(encoder.read_raw_angle())
    return samples


def calculate_stats(samples):
    """
    Calculate noise statistics from samples.

    Returns dict with:
    - mean: average value in steps
    - min/max: range in steps
    - pp_steps: peak-to-peak in steps
    - pp_deg: peak-to-peak in degrees
    - rms_steps: RMS deviation in steps
    - rms_deg: RMS deviation in degrees
    """
    n = len(samples)

    # Mean
    mean = sum(samples) / n

    # Min/Max
    min_val = min(samples)
    max_val = max(samples)
    pp_steps = max_val - min_val

    # RMS (standard deviation from mean)
    variance = sum((s - mean) ** 2 for s in samples) / n
    rms_steps = math.sqrt(variance)

    return {
        "n": n,
        "mean": mean,
        "min": min_val,
        "max": max_val,
        "pp_steps": pp_steps,
        "pp_deg": pp_steps * DEG_PER_STEP,
        "rms_steps": rms_steps,
        "rms_deg": rms_steps * DEG_PER_STEP,
    }


def run_noise_test(encoder, sf, label):
    """Run noise test at specified SF setting."""
    print(f"\n--- {label} ---")

    # Configure filter
    set_slow_filter(encoder, sf)
    time.sleep_ms(SETTLE_TIME_MS)  # Let filter settle

    # Collect samples
    samples = collect_samples(encoder, SAMPLES_PER_TEST)

    # Calculate and display stats
    stats = calculate_stats(samples)
    print(f"Samples: {stats['n']}")
    print(f"Mean: {stats['mean']:.1f} steps")
    print(f"Range: {stats['min']}-{stats['max']} steps")
    print(f"Peak-to-peak: {stats['pp_steps']} steps ({stats['pp_deg']:.3f}°)")
    print(f"RMS noise: {stats['rms_steps']:.2f} steps ({stats['rms_deg']:.4f}°)")

    return stats


def main():
    # Initialize I2C and encoder
    i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400_000)
    encoder = AS5600(i2c=i2c)

    # Verify sensor health
    print("AS5600 Noise Characterization")
    print("=" * 40)
    print(encoder.diagnose())
    print("\nEnsure magnet is STATIONARY during test!")
    print(f"Collecting {SAMPLES_PER_TEST} samples per setting...")

    # Store results for comparison
    results = []

    # Test each SF setting
    for sf, label in SF_SETTINGS:
        stats = run_noise_test(encoder, sf, label)
        results.append((sf, stats))

    # Summary table
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    print("SF | RMS (°)  | P-P (°)  | Expected")
    print("---|----------|----------|----------")
    expected = [0.015, 0.021, 0.030, 0.043]
    for (sf, stats), exp in zip(results, expected):
        rms = stats["rms_deg"]
        pp = stats["pp_deg"]
        delta = rms - exp
        print(f" {sf} | {rms:7.4f}° | {pp:7.3f}° | {exp:.3f}° ({delta:+.4f})")

    # Restore low-latency config
    encoder.configure_low_latency_mode()
    print("\nRestored low-latency configuration (SF=3, FTH=1)")


if __name__ == "__main__":
    main()
