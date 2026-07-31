# capture.py - Capture raw fingerprint data and save as PNG images.

from focaltech import FocalTechDevice
from focaltech.image import save_capture


def main():
    device = FocalTechDevice()

    try:
        device.open()
        firmware, width, height = device.initialize()

        print(f"Firmware: {firmware}")
        print(f"Resolution: {width}x{height}")

        device.clear_sensor_data()

        input("Place finger on sensor, then press Enter...")

        for i in range(5):
            device.clear_sensor_data()
            device.set_scan_image_mode()
            raw = device.capture_raw()
            print(f"Capture {i + 1}: {len(raw)} bytes")

            raw_path, png_path = save_capture(raw, width, height)
            print(f"Saved: {png_path}")

            device.clear_sensor_data()

            input("Press Enter for next capture...")

    finally:
        device.close()


if __name__ == "__main__":
    main()