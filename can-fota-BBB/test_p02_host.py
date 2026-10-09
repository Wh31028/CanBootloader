"""P02 host-only checks.  No CAN interface, board, or firmware write is used."""
import errno
import socket
import struct
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, "can-fota-BBB")
import fota_sender_p02 as sender
from fota_p01 import Metrics
from fota_p02 import LossModel

def response(ident, payload, dlc=8):
    return struct.pack("<IB3x8s", ident, dlc, bytes(payload).ljust(8, b"\0"))

class FakeBus:
    def __init__(self, replies=(), enobufs=False):
        self.replies, self.enobufs = list(replies), enobufs
    def settimeout(self, _): pass
    def send(self, _):
        if self.enobufs: raise OSError(errno.ENOBUFS, "full")
    def recv(self, _):
        if self.replies:
            reply = self.replies.pop(0)
            if reply is not None: return reply
        raise socket.timeout()

def main():
    cfg = SimpleNamespace(start_timeout=.001, data_timeout=.001, end_timeout=.001,
                          fc_timeout=.001, max_block_attempts=2, max_custom_probe_attempts=2)
    now = time.monotonic() + 1
    # Custom: START ACK, one DATA ACK, END ACK.
    custom_bus = FakeBus([response(sender.CUSTOM_RESP, [0], 2), response(sender.CUSTOM_RESP, [0], 2), response(sender.CUSTOM_RESP, [0], 2)])
    assert sender.custom(custom_bus, b"abcdefg", Metrics(), LossModel(7, 0), now, cfg)[0] == "OK"
    # ISO-TP: START SF ACK with 7-byte blocks, FC, DATA SF ACK, END SF ACK.
    iso_bus = FakeBus([response(sender.ISO_RESP, [5, 0x10, 0, 7, 0]), response(sender.ISO_RESP, [0x30, 8, 0]), response(sender.ISO_RESP, [2, 0x20]), response(sender.ISO_RESP, [2, 0x30])])
    assert sender.iso(iso_bus, b"abcdefg", Metrics(), LossModel(7, 0), now, cfg)[0] == "OK"
    # A missing terminal DATA frame is probed, then produces its bitmap NACK and ACK.
    probe_bus = FakeBus([response(sender.CUSTOM_RESP,[0],2), None, response(sender.CUSTOM_RESP,[0],2), response(sender.CUSTOM_RESP,[0],2)])
    probe_metrics = Metrics()
    # First reply is the START ACK; the next ACK follows a final-frame probe.
    assert sender.custom(probe_bus, b"abcdefghi", probe_metrics, LossModel(1,0), now, cfg)[0] == "OK"
    assert probe_metrics.retransmit_attempts == 1
    # Persistent no-response remains bounded and explicitly fails.
    assert sender.custom(FakeBus([response(sender.CUSTOM_RESP,[0],2)]), b"x", Metrics(), LossModel(1,0), now, cfg)[0] == "FAIL_DATA_TIMEOUT"
    crc_bus = FakeBus([response(sender.CUSTOM_RESP,[0],2), response(sender.CUSTOM_RESP,[0],2), response(sender.CUSTOM_RESP,[1],2)])
    assert sender.custom(crc_bus, b"x", Metrics(), LossModel(1,0), now, cfg)[0] == "FAIL_END_CRC"
    # Persistent ENOBUFS must stop at its deadline instead of spinning.
    metrics = Metrics(); assert not metrics.attempt_send(FakeBus(enobufs=True), b"x", deadline=time.monotonic()+.003, enobufs_backoff=.001)
    assert metrics.send_errors >= 1
    a, b = LossModel(99,.5), LossModel(99,.5)
    assert [a.drop('custom_data',0,i) for i in range(20)] == [b.drop('custom_data',0,i) for i in range(20)]
    print("P02 host checks: PASS (normal, ENOBUFS, timeout, CRC failure, deterministic seed)")
if __name__ == '__main__': main()
