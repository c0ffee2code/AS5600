"""
AS5600 Encoder Test Fixture

Demonstrates continuous angle monitoring with diagnostic telemetry.
Outputs grep-friendly diagnostic lines for analysis and plotting.
"""

from micropython import const
from machine import I2C, Pin
import time
from as5600 import AS5600

# Initialize I2C bus
i2c = I2C(
    0,
    scl=Pin(1),
    sda=Pin(0),
    freq=400_000
)

# Initialize encoder
encoder = AS5600(i2c=i2c)

# Configure for low-latency operation (SF=11, FTH=001, PM=00)
encoder.configure_low_latency_mode()

# Mechanical center point - recalibrate after reassembly!
# Recorded while holding lever at horizontal position
AXIS_CENTER = const(413)

# Main monitoring loop
while True:
    # Output diagnostic telemetry (grep-friendly single line)
    print(encoder.diagnose(axis_center=AXIS_CENTER))

    time.sleep(0.05)
