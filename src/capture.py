from focaltech import FocalTechDevice
from focaltech.image import save_capture


def main():
    device = FocalTechDevice()

    try:
        device.open()

        firmware, width, height = device.initialize()

        print(f"Firmware: {firmware}")
        print(f"Resolution: {width}x{height}")
        print(f"RAW16 size: {width * height * 2} bytes")

        input("Place finger on sensor, then press Enter...")

        raw = device.capture_raw()
        raw_path, png_path = save_capture(raw, width, height)

        print(f"Saved RAW: {raw_path}")
        print(f"Saved PNG: {png_path}")

    finally:
        device.close()


if __name__ == "__main__":
    main()