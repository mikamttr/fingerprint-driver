# FocalTech Fingerprint Driver — Reverse Engineering

Reverse engineering notes and Linux PoC for the FocalTech fingerprint stack.
Based on reversing the Windows UMDF driver and rebuilding the protocol under Linux using `libusb`. 

---

# Target Device

```text
Manufacturer : HOLTEK
Product      : FocalTech Fingerprint Device
VID:PID      : 2808:c652
```

---

# Current Status

### Working:
- [x] USB communication
- [x] Packet TX/RX parsing
- [x] Firmware version read
- [x] Heartbeat / alive checks
- [x] Device info read/write
- [x] STM wake-up sequence
- [x] Scan image mode switching
- [x] RAW image acquisition
- [x] RAW16 to PNG conversion
- [x] Linux/libusb PoC

## Still Missing

- [ ] Proper finger detection
- [ ] Real capture trigger sequence
- [ ] Capture synchronization
- [ ] Exact semantics of all device statuses
- [ ] Full RX protocol coverage
- [ ] Enrollment / matching pipeline
- [ ] Windows biometric integration replacement

---

# Project Structure

```text
src/
├── capture.py
└── focaltech/
    ├── __init__.py
    ├── device.py
    ├── image.py
    └── protocol.py
```

---

# USB Communication

## Interface

```text
Interface : 0
Class     : CDC Data
```

## Endpoints

```text
OUT = 0x03
IN  = 0x81
```

## Transfer Type

```text
USB Bulk Transfer
```

---

# Packet Protocol

Recovered from:

```text
ProtocolWriteData
```

## TX Packet Format

```text
[0]      = 0x02
[1]      = LEN_H
[2]      = LEN_L
[3]      = CMD
[4..N]   = PAYLOAD
[last]   = XOR checksum
```

## Checksum

```text
XOR of all bytes from LEN_H to end of payload
```

---

# Confirmed Commands

| CMD    | Description       |
| ------ | ----------------- |
| `0x30` | Firmware version  |
| `0x34` | STM status query  |
| `0x35` | Heartbeat         |
| `0x3D` | Sensor UID        |
| `0x3F` | Upgrade counter   |
| `0x40` | Touch keys state  |
| `0x80` | Read device info  |
| `0x81` | Capture RAW image |
| `0x82` | Alive check       |
| `0x87` | Write device info |

---

# Firmware Version

## TX

```text
02 00 01 30 31
```

## Example RX

```text
APP_V0211_HT32_20250117
```

---

# Heartbeat

## TX

```text
02 00 01 35 34
```

## RX

```text
55 BB
```

Purpose:

```text
keepalive / wake-up
```

---

# Alive Check

## TX

```text
02 00 03 82 83 01 03
```

## RX

```text
00
```

Purpose:

```text
device ready check
```

---

# STM Wake-Up Sequence

Recovered from:

```text
ff_sc_st_config_power_mode
ff_sc_query_st_status
ff_sc_DataWrite
```

## STM Status Query

### TX

```text
CMD = 0x34
```

### Expected RX

```text
0xAA55
```

Meaning:

```text
STM ready
```

---

## Raw Wake-Up Packet

When STM is sleeping, Windows sends:

```text
00
```

Important:

```text
This is NOT wrapped in the FocalTech protocol.
```

It is sent directly through:

```text
USB bulk OUT transfer
```

Linux implementation now reproduces this behavior.

---

# Sensor Information

## Resolution

Read through:

```text
CMD 0x80
```

### Width

```text
INFO_ID = 0x03
```

Response:

```text
0x40 = 64
```

### Height

```text
INFO_ID = 0x04
```

Response:

```text
0x50 = 80
```

---

## Final Resolution

```text
64 × 80
```

---

# Device Status

Recovered from:

```text
ff_sc_query_device_status
```

Read through:

```text
CMD 0x80
INFO_ID = 0x01
```

Expected value:

```text
0x5AA5
```

Meaning:

```text
new frame available
```

Important:

```text
0x5AA5 does NOT mean "finger detected".
```

This explains stale frame behavior.

---

# Device Modes

Recovered from:

```text
ff_sc_config_device_mode
```

| Mode ID | Name       |
| ------- | ---------- |
| `0`     | SENSOR     |
| `1`     | POA        |
| `6`     | SCAN_IMAGE |
| `7`     | GESTURE    |

---

# Scan Image Mode

Enabled through:

```text
CMD 0x87
payload = [0x6C, 0x01, 0x6C]
```

Meaning:

```text
INFO_ID = 0x6C
VALUE   = 0x6C
```

---

# Image Capture

## RAW Format

Frame size:

```text
64 × 80 × 2
= 10240 bytes
```

Format:

```text
16-bit signed little-endian
```

---

## Capture Command

### TX

```text
02 00 01 81 80
```

### RX

```text
10240-byte RAW16 frame
```

---

# Image Processing Pipeline

Current Linux pipeline:

```text
RAW16
→ signed conversion
→ inversion
→ normalization
→ grayscale conversion
→ PNG export
```

Output:

```text
64 × 80 grayscale PNG
```

---

# Current Capture Flow

Recovered from:

```text
OnScanImage
```

Observed Windows flow:

```text
wake STM
    ↓
switch to scan image mode
    ↓
poll device status
    ↓
status == 0x5AA5
    ↓
capture RAW frame
    ↓
convert RAW16 → grayscale
```

---

# Important Recovered Functions

## FtWbioDriverUmdfV3.dll

| Renamed Function             | Original Name   |
| ---------------------------- | --------------- |
| `ff_sc_WriteData`            | `FUN_18000636c` |
| `ff_sc_ReadData`             | `FUN_180005ac8` |
| `ProtocolWriteData`          | `FUN_18000c7b0` |
| `ProtocolReadData`           | `FUN_18000c910` |
| `ff_sc_DataWrite`            | `FUN_18000cca0` |
| `UsbBulkTransfer`            | `FUN_18000d70c` |
| `ff_sc_GetImage`             | `FUN_180004f48` |
| `ff_sc_ReadImageRawData`     | `FUN_180005cb0` |
| `ConvertRaw16ToImage8`       | `FUN_180003e04` |
| `ff_sc_ReadInfo_directly`    | `FUN_180005f00` |
| `ff_sc_WriteInfo`            | `FUN_180006428` |
| `ff_sc_config_device_mode`   | `FUN_180006874` |
| `ff_sc_query_device_status`  | `FUN_180007d00` |
| `ff_sc_query_st_status`      | `FUN_180007ec0` |
| `ff_sc_st_config_power_mode` | `FUN_180007fc0` |
| `OnScanImage`                | `FUN_18000a604` |

---

## ftWbioEngineAdapter.dll

| Renamed Function            | Original Name   |
| --------------------------- | --------------- |
| `new_algo_focal`            | `FUN_18012d900` |
| `algo_init`                 | `FUN_18012c210` |
| `CreateAlgoConfig`          | `FUN_18012e2a0` |
| `focal_SetFakeFingerDetect` | `FUN_180008480` |

---

# Registry Configuration

Driver runtime configuration stored in:

```text
HKLM\SYSTEM\CurrentControlSet\Control\FocalFP
```

Used for:

```text
- runtime tuning
- debug flags
- sensor configuration
- fake finger parameters
```

---

# Current Limitation


Observed behavior:
- removing finger keeps previous frame
- 0x5AA5 only means "frame available"
- capture command alone is insufficient

Most likely caused by missing logic inside:

```text
ff_sc_st_config_power_mode
```

and/or:

```text
FUN_180007dec
```

which appears related to:

```text
finger presence detection
```

---

# Next Reverse Engineering Target

Priority target:

```text
FUN_180007dec
```

Expected purpose:

```text
finger detection / interrupt logic
```

This should explain:

```text
- automatic capture triggering
- stale frame behavior
- real finger detection
- synchronization logic
```
