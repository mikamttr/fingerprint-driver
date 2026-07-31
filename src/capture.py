# capture.py - Automatically capture fingerprints when a finger is detected.

from time import time
from focaltech import FocalTechDevice
from focaltech.image import save_capture


def main():
    device = FocalTechDevice()

    try:
        device.open()
        firmware, width, height = device.initialize()

        print(f"Firmware: {firmware}")
        print(f"Resolution: {width}x{height}")
        print("Waiting for finger... Press Ctrl+C to stop.")

        capture_index = 1

        while True:
            raw = device.capture_raw()

            print(f"RAW length: {len(raw)} bytes")
            print(f"First 32 bytes: {raw[:32].hex(' ')}")

            pixels = [
                int.from_bytes(raw[i:i + 2], "little")
                for i in range(0, len(raw), 2)
            ]

            print(f"Minimum pixel value: {min(pixels)}")
            print(f"Maximum pixel value: {max(pixels)}")
            print(f"First 16 pixels: {pixels[:16]}")

            print(f"Capture {capture_index}: {len(raw)} bytes")

            raw_path, png_path = save_capture(raw, width, height)
            print(f"Saved: {png_path}")

            capture_index += 1

            while device.query_finger_status():
                time.sleep(0.02)

            print("Finger removed. Waiting for next finger...")
            
    except KeyboardInterrupt:
        print("\nCapture stopped.")

    finally:
        device.close()


if __name__ == "__main__":
    main()