"""P01 measurement and SocketCAN frame validation helpers.

SocketCAN send success means only that the kernel accepted the frame.  It is
not an on-wire completion or a CAN-controller automatic retransmission count.
"""
from dataclasses import dataclass

CAN_EFF_FLAG = 0x80000000
CAN_RTR_FLAG = 0x40000000
CAN_ERR_FLAG = 0x20000000
CAN_SFF_MASK = 0x7FF


@dataclass
class Metrics:
    send_attempts: int = 0
    software_drops: int = 0
    socket_send_success: int = 0
    send_errors: int = 0
    protocol_rx: int = 0
    retransmit_attempts: int = 0
    retransmit_send_success: int = 0
    invalid_protocol_rx: int = 0

    def attempt_send(self, bus, frame, dropped=False, retransmit=False):
        """Account one host send attempt; ENOBUFS retries are socket errors."""
        import errno
        import time
        self.send_attempts += 1
        if retransmit:
            self.retransmit_attempts += 1
        if dropped:
            self.software_drops += 1
            return False
        while True:
            try:
                bus.send(frame)
                self.socket_send_success += 1
                if retransmit:
                    self.retransmit_send_success += 1
                return True
            except OSError as exc:
                self.send_errors += 1
                if exc.errno == errno.ENOBUFS:
                    time.sleep(0.0005)
                    continue
                raise


def standard_data_id(can_id, expected_id):
    """Reject EFF/RTR/ERR frames rather than masking their flags away."""
    return (can_id & (CAN_EFF_FLAG | CAN_RTR_FLAG | CAN_ERR_FLAG)) == 0 and \
        (can_id & CAN_SFF_MASK) == expected_id


def overhead_pct(metrics):
    """Retransmission send attempts / all host send attempts, in percent."""
    return (100.0 * metrics.retransmit_attempts / metrics.send_attempts
            if metrics.send_attempts else 0.0)
