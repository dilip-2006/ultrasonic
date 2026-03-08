#!/usr/bin/env python3
"""
measure_client — On-demand single distance measurement
=======================================================
Waits for you to type  'measure'  then prints one reading and publishes it.
Type  'quit'  or press Ctrl+C to exit.

Usage (in a separate terminal):
  ros2 run ir_control measure_client
"""

import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Range

_GREEN  = '\033[92m'
_YELLOW = '\033[93m'
_RED    = '\033[91m'
_CYAN   = '\033[96m'
_BOLD   = '\033[1m'
_RESET  = '\033[0m'


class MeasureClient(Node):
    """Subscribe to /ultrasonic/range and print one value on-demand."""

    def __init__(self):
        super().__init__('measure_client')

        sensor_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self._latest_range: float | None = None
        self._sub = self.create_subscription(
            Range, '/ultrasonic/range',
            self._range_cb, sensor_qos)

        print(f'\n{_CYAN}{_BOLD}{"═"*44}{_RESET}')
        print(f'{_CYAN}{_BOLD}  📏 Measure Client — On-Demand Readings{_RESET}')
        print(f'{_CYAN}{_BOLD}{"═"*44}{_RESET}')
        print(f"  Type  {_BOLD}measure{_RESET}  → get one reading")
        print(f"  Type  {_BOLD}quit{_RESET}     → exit\n")

    def _range_cb(self, msg: Range):
        self._latest_range = msg.range

    def prompt_loop(self):
        """Blocking prompt loop — run after spinning is started in a thread."""
        import threading
        spin_thread = threading.Thread(
            target=rclpy.spin, args=(self,), daemon=True)
        spin_thread.start()

        while rclpy.ok():
            try:
                cmd = input(f'  {_CYAN}>{_RESET} ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd in ( 'exit', 'q'):
                print(f'\n  {_CYAN}Goodbye!{_RESET}\n')
                break

            if cmd == 'm':
                # Clear stale reading and wait for a fresh one
                self._latest_range = None
                spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                deadline = time.time() + 2.0     # wait up to 2 s for fresh data
                i = 0
                while self._latest_range is None and time.time() < deadline:
                    frame = spinner[i % len(spinner)]
                    print(f'\r  {_CYAN}{frame} Measuring …{_RESET}  ',
                          end='', flush=True)
                    time.sleep(0.1)
                    i += 1
                print('\r' + ' ' * 30 + '\r', end='', flush=True)   # clear line

                if self._latest_range is None:
                    print(f'  {_YELLOW}⏳ No data received.'
                          f' Is ultrasonic_node running?{_RESET}\n')
                    continue

                dist_m  = self._latest_range
                dist_cm = dist_m * 100.0

                if dist_m == float('inf'):
                    print(f'  {_RED}{_BOLD}  Result: OUT OF RANGE (> 400 cm){_RESET}\n')
                    continue
                if dist_m <= 0:
                    print(f'  {_RED}{_BOLD}  Result: TOO CLOSE (< 2 cm){_RESET}\n')
                    continue

                # Colour by distance
                if dist_cm < 30:
                    colour = _RED
                    status = '⚠  DANGER'
                elif dist_cm < 100:
                    colour = _YELLOW
                    status = '⚡ CAUTION'
                else:
                    colour = _GREEN
                    status = '✔  SAFE'

                print(f'\n  {colour}{_BOLD}┌─────────────────────────┐{_RESET}')
                print(f'  {colour}{_BOLD}│  📏 {dist_cm:>8.2f} cm          │{_RESET}')
                print(f'  {colour}{_BOLD}│  📡 {dist_m:>8.4f} m           │{_RESET}')
                print(f'  {colour}{_BOLD}│  {status:<23} │{_RESET}')
                print(f'  {colour}{_BOLD}└─────────────────────────┘{_RESET}\n')

            else:
                print(f"  {_YELLOW}Unknown command. Type 'measure' or 'quit'.{_RESET}")

        self.destroy_node()


def main(args=None):
    rclpy.init(args=args)
    client = MeasureClient()
    try:
        client.prompt_loop()
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
