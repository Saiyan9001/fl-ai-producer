"""
FL Studio MIDI Controller Device Definition
This file defines the MIDI device to FL Studio.
"""

# Device name as it appears in FL Studio
name = "FL-AI-Producer"

# Number of input and output ports
InputPortCount = 0
OutputPortCount = 0

# Device type
# 0 = MIDI, 1 = Generic controller, 2 = MMC controller
DeviceType = 1

# Device flags
# Bit 0: Show in browser
# Bit 1: Show mixer
# Bit 2: Show plugin editor
# Bit 3: Show native plugins
DeviceFlags = 0

# Optional: MIDI device IDs for auto-detection
# Not needed for virtual controller
