# FocalTech Fingerprint Driver — Reverse Engineering

Reverse engineering notes and Linux PoC for the FocalTech fingerprint stack.

## Target Device

```text
Manufacturer : HOLTEK
Product : FocalTech Fingerprint Device
VID:PID = 2808:c652
```


### Working:
- [x] USB communication
- [x] Packet TX/RX parsing
- [x] Firmware read
- [x] Heartbeat
- [x] Alive check
- [x] Device info read/write
- [x] Scan image mode switching
- [x] RAW image acquisition
- [x] RAW16 → PNG conversion
- [x] Linux/libusb PoC

### Still unresolved:
- [ ] Real wake-up sequence
- [ ] Proper finger detection
- [ ] Exact capture synchronization
- [ ] Full RX protocol details

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

## Endpoints

```text
OUT = 0x03
IN  = 0x81
```

---

# Packet Format

Recovered from:

```text
ProtocolWriteData
```

Format:

```text
[0]      = 0x02
[1]      = LEN_H
[2]      = LEN_L
[3]      = CMD
[4..N]   = PAYLOAD
[last]   = XOR checksum
```

Checksum:

```text
XOR of all bytes from LEN_H to end of payload
```

---

# Confirmed Commands

| CMD    | Description         |
| ------ | ------------------- |
| `0x30` | Firmware version    |
| `0x35` | Heartbeat / wake-up |
| `0x3D` | Sensor UID          |
| `0x3F` | Upgrade counter     |
| `0x40` | Touch keys state    |
| `0x80` | Read device info    |
| `0x81` | Capture RAW image   |
| `0x82` | Alive check         |
| `0x87` | Write device info   |

---

# Important Commands

## Firmware Version

TX:

```text
02 00 01 30 31
```

Example response:

```text
APP_V0211_HT32_20250117
```

---

## Heartbeat

TX:

```text
02 00 01 35 34
```

RX:

```text
55 BB
```

Purpose:

```text
keepalive / wake-up
```

---

## Alive Check

TX:

```text
02 00 03 82 83 01 03
```

RX:

```text
00
```

Purpose:

```text
device ready check
```

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

Final resolution:

```text
64 × 80
```

---

## Device Status

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

TX:

```text
02 00 01 81 80
```

Returns:

```text
10240-byte RAW16 frame
```

---

# Image Processing

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

## Scan Image Mode

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

# Scan Flow

Recovered from:

```text
OnScanImage
```

Observed flow:

```text
wake device
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

Relevant functions:

```text
FUN_180007fc0  → wake-up sequence (unknown)
FUN_180006874  → mode switching
FUN_180007d00  → status polling
ff_sc_GetImage → image acquisition
```

---

# Identified Functions

## FtWbioDriverUmdfV3.dll

| Renamed Function            | Original Name   |
| --------------------------- | --------------- |
| `ff_sc_WriteData`           | `FUN_18000636c` |
| `ff_sc_ReadData`            | `FUN_180005ac8` |
| `ProtocolWriteData`         | `FUN_18000c7b0` |
| `UsbBulkTransfer`           | `FUN_18000d70c` |
| `ff_sc_GetImage`            | `FUN_180004f48` |
| `ff_sc_ReadImageRawData`    | `FUN_180005cb0` |
| `ConvertRaw16ToImage8`      | `FUN_180003e04` |
| `ff_sc_ReadInfo_directly`   | `FUN_180005f00` |
| `ff_sc_WriteInfo`           | `FUN_180006428` |
| `ff_sc_config_device_mode`  | `FUN_180006874` |
| `ff_sc_query_device_status` | `FUN_180007d00` |
| `OnScanImage`               | `FUN_18000a604` |

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

The device currently returns stale frames.

Observed behavior:

```text
- removing finger keeps previous frame
- 0x5AA5 only means "frame available"
- actual trigger sequence still unknown
```

Most likely caused by missing logic inside:

```text
FUN_180007fc0
```

---

# Next Steps

Priority:

```text
FUN_180007fc0
```

Goal:

```text
recover real capture trigger / wake-up sequence
```

This should explain:

```text
- stale frame behavior
- real finger detection
- automatic capture triggering
- synchronization logic
```
