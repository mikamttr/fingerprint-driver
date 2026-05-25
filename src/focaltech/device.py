import time
import usb.core
import usb.util

from .protocol import build_packet, parse_response

VID = 0x2808
PID = 0xC652

INTERFACE = 0
EP_OUT = 0x03
EP_IN = 0x81
USB_CHUNK_SIZE = 64


class FocalTechDevice:
    def __init__(self):
        self.dev = None
        self.width = None
        self.height = None

    def open(self):
        self.dev = usb.core.find(idVendor=VID, idProduct=PID)

        if self.dev is None:
            raise RuntimeError("FocalTech device 2808:c652 not found")

        try:
            if self.dev.is_kernel_driver_active(INTERFACE):
                self.dev.detach_kernel_driver(INTERFACE)
        except (NotImplementedError, usb.core.USBError):
            pass

        try:
            self.dev.set_configuration()
        except usb.core.USBError as err:
            print("set_configuration warning:", err)

        usb.util.claim_interface(self.dev, INTERFACE)

    def close(self):
        if self.dev is None:
            return

        try:
            usb.util.release_interface(self.dev, INTERFACE)
        except usb.core.USBError:
            pass

        usb.util.dispose_resources(self.dev)
        self.dev = None

    def read_response(self, timeout=3000) -> tuple[int, bytes]:
        first = bytes(self.dev.read(EP_IN, USB_CHUNK_SIZE, timeout=timeout))

        if len(first) < 5:
            raise RuntimeError("Response too short")

        length = (first[1] << 8) | first[2]
        total_size = 1 + 2 + length + 1

        chunks = [first]
        received = len(first)

        while received < total_size:
            chunk = bytes(self.dev.read(EP_IN, USB_CHUNK_SIZE, timeout=timeout))
            chunks.append(chunk)
            received += len(chunk)

        data = b"".join(chunks)[:total_size]
        return parse_response(data)

    def command(self, cmd: int, payload: bytes = b"", timeout=3000) -> bytes:
        packet = build_packet(cmd, payload)
        self.dev.write(EP_OUT, packet, timeout=timeout)

        response_type, response_payload = self.read_response(timeout=timeout)

        if response_type != 0x04:
            raise RuntimeError(f"Unexpected response type: 0x{response_type:02x}")

        return response_payload

    def get_firmware_version(self) -> str:
        payload = self.command(0x30)
        return payload.decode(errors="replace")

    def heartbeat(self) -> bytes:
        return self.command(0x35)

    def check_alive(self) -> bytes:
        return self.command(0x82, bytes([0x83, 0x01]))

    def read_info(self, info_id: int, length: int = 1) -> bytes:
        return self.command(0x80, bytes([info_id & 0xFF, length & 0xFF]))

    def read_resolution(self) -> tuple[int, int]:
        width = self.read_info(0x03, 1)[0]
        height = self.read_info(0x04, 1)[0]

        self.width = width
        self.height = height

        return width, height

    def set_scan_image_mode(self):
        try:
            return self.command(0x87, bytes([0x6C, 0x01, 0x6C]))
        except RuntimeError as err:
            print("scan mode warning:", err)
            return b""

    def initialize(self):
        firmware = self.get_firmware_version()
        self.heartbeat()
        self.check_alive()
        self.read_info(0x07, 1)
        width, height = self.read_resolution()
        self.set_scan_image_mode()

        return firmware, width, height

    def capture_raw(self, timeout=5000) -> bytes:
        if self.width is None or self.height is None:
            self.read_resolution()

        return self.command(0x81, timeout=timeout)