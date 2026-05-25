STX = 0x02


def bcc(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value


def build_packet(cmd: int, payload: bytes = b"") -> bytes:
    length = len(payload) + 1

    body = bytes([
        (length >> 8) & 0xFF,
        length & 0xFF,
        cmd & 0xFF,
    ]) + payload

    return bytes([STX]) + body + bytes([bcc(body)])


def parse_response(data: bytes) -> tuple[int, bytes]:
    if len(data) < 5:
        raise RuntimeError("Response too short")

    if data[0] != STX:
        raise RuntimeError(f"Invalid STX: {data[0]:02x}")

    response_type = data[3]
    payload = data[4:-1]
    checksum = data[-1]
    expected = bcc(data[1:-1])

    if checksum != expected:
        raise RuntimeError(f"Invalid checksum: got {checksum:02x}, expected {expected:02x}")

    return response_type, payload