#!/usr/bin/env python3
"""
ultrasonic_node — HC-SR04 Ultrasonic Sensor → ROS2 Node
=========================================================
Reads distance data from Arduino Nano over serial and:
  • Prints live measurements clearly in the terminal (bash)
  • Publishes /ultrasonic/range      (sensor_msgs/Range)
  • Publishes /ultrasonic/distance_m (std_msgs/Float32)
  • Broadcasts TF2: base_link → ultrasonic_link

For a single on-demand reading:
  ros2 run ir_control measure_client

Parameters:
  serial_port  (str)   default: /dev/ttyUSB0
  baud_rate    (int)   default: 115200
  frame_id     (str)   default: ultrasonic_link
  parent_frame (str)   default: base_link
  sensor_x/y/z (float) sensor offset from parent frame (metres)
"""

import math
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from sensor_msgs.msg import Range
from std_msgs.msg import Float32
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

try:
    import serial
except ImportError:
    raise ImportError('pyserial is required: pip install pyserial')

# ── Terminal colour codes ──────────────────────────────────────────────────────
_GREEN  = '\033[92m'
_YELLOW = '\033[93m'
_RED    = '\033[91m'
_CYAN   = '\033[96m'
_BOLD   = '\033[1m'
_RESET  = '\033[0m'

# Distance thresholds (cm)
_DANGER_CM  = 30
_CAUTION_CM = 100


def _bar(distance_cm: float, max_cm: float = 200.0, width: int = 30) -> str:
    """Return a coloured ASCII bar proportional to distance."""
    filled = int(min(distance_cm, max_cm) / max_cm * width)
    bar = '█' * filled + '░' * (width - filled)
    if distance_cm < _DANGER_CM:
        colour = _RED
    elif distance_cm < _CAUTION_CM:
        colour = _YELLOW
    else:
        colour = _GREEN
    return f'{colour}{bar}{_RESET}'


def _status_label(distance_cm: float) -> str:
    if distance_cm < _DANGER_CM:
        return f'{_RED}{_BOLD}⚠ DANGER {_RESET}'
    elif distance_cm < _CAUTION_CM:
        return f'{_YELLOW}{_BOLD}⚡ CAUTION{_RESET}'
    else:
        return f'{_GREEN}{_BOLD}✔ SAFE   {_RESET}'


class UltrasonicNode(Node):
    """Reads HC-SR04 data from Arduino serial and publishes sensor_msgs/Range."""

    FIELD_OF_VIEW_RAD = math.radians(15)
    MIN_RANGE_M = 0.02
    MAX_RANGE_M = 4.00

    def __init__(self):
        super().__init__('ultrasonic_node')

        # ── Parameters ────────────────────────────────────────────────────────
        self.declare_parameter('serial_port',  '/dev/ttyUSB0')
        self.declare_parameter('baud_rate',    115200)
        self.declare_parameter('frame_id',     'ultrasonic_link')
        self.declare_parameter('parent_frame', 'base_link')
        self.declare_parameter('sensor_x',     0.05)
        self.declare_parameter('sensor_y',     0.0)
        self.declare_parameter('sensor_z',     0.05)

        self.serial_port  = self.get_parameter('serial_port').value
        self.baud_rate    = self.get_parameter('baud_rate').value
        self.frame_id     = self.get_parameter('frame_id').value
        self.parent_frame = self.get_parameter('parent_frame').value
        self.sensor_x     = self.get_parameter('sensor_x').value
        self.sensor_y     = self.get_parameter('sensor_y').value
        self.sensor_z     = self.get_parameter('sensor_z').value

        # ── QoS ───────────────────────────────────────────────────────────────
        sensor_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # ── Publishers ────────────────────────────────────────────────────────
        self.range_pub = self.create_publisher(Range,  '/ultrasonic/range',      sensor_qos)
        self.dist_pub  = self.create_publisher(Float32, '/ultrasonic/distance_m', sensor_qos)

        # ── TF2 ───────────────────────────────────────────────────────────────
        self.tf_broadcaster = TransformBroadcaster(self)

        # ── State ────────────────────────────────────────────────────────────
        self._serial: serial.Serial | None = None
        self._running  = True
        self._reading_count = 0

        # Print startup banner
        print(f'\n{_CYAN}{_BOLD}{"═"*54}{_RESET}')
        print(f'{_CYAN}{_BOLD}  🔊 HC-SR04 Ultrasonic Sensor — Live Measurements{_RESET}')
        print(f'{_CYAN}{_BOLD}  Port: {self.serial_port}  |  Baud: {self.baud_rate}{_RESET}')
        print(f'{_CYAN}{_BOLD}  Topic: /ultrasonic/range{_RESET}')
        print(f'{_CYAN}{_BOLD}{"═"*54}{_RESET}\n')
        print(f'  {"#":<6} {"Distance":>10}   {"Bar (0–200 cm)":^32}   Status')
        print(f'  {"─"*6} {"─"*10}   {"─"*32}   {"─"*8}')

        # ── Serial reader thread ──────────────────────────────────────────────
        self._thread = threading.Thread(target=self._serial_loop, daemon=True)
        self._thread.start()

    # ──────────────────────────────────────────────────────────────────────────
    def _open_serial(self) -> bool:
        try:
            self._serial = serial.Serial(self.serial_port, self.baud_rate, timeout=2.0)
            time.sleep(2.0)
            self._serial.reset_input_buffer()
            self.get_logger().info(f'Serial port {self.serial_port} opened.')
            return True
        except serial.SerialException as e:
            self.get_logger().error(f'Cannot open {self.serial_port}: {e}')
            return False

    def _serial_loop(self):
        while self._running:
            if self._serial is None or not self._serial.is_open:
                if not self._open_serial():
                    print(f'\n  {_RED}⚠  Cannot open {self.serial_port} — retrying in 3 s …{_RESET}\n')
                    time.sleep(3.0)
                    continue
            try:
                raw  = self._serial.readline()
                if not raw:
                    continue
                line = raw.decode('utf-8', errors='ignore').strip()
                self._parse_and_publish(line)
            except serial.SerialException as e:
                self.get_logger().error(f'Serial error: {e}. Reconnecting …')
                self._close_serial()
            except Exception as e:
                self.get_logger().debug(f'Parse error: {e}')

    def _close_serial(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    # ──────────────────────────────────────────────────────────────────────────
    def _parse_and_publish(self, line: str):
        if not line.startswith('DIST:'):
            return

        value_str = line[5:]
        now = self.get_clock().now().to_msg()

        msg = Range()
        msg.header.stamp    = now
        msg.header.frame_id = self.frame_id
        msg.radiation_type  = Range.ULTRASOUND
        msg.field_of_view   = self.FIELD_OF_VIEW_RAD
        msg.min_range       = self.MIN_RANGE_M
        msg.max_range       = self.MAX_RANGE_M

        if value_str in ('OUT_OF_RANGE', 'TOO_CLOSE'):
            msg.range = float('inf') if value_str == 'OUT_OF_RANGE' else 0.0
            self.range_pub.publish(msg)
            self._broadcast_tf(now)
            self._reading_count += 1
            # Print out-of-range row
            label = 'OUT OF RANGE' if value_str == 'OUT_OF_RANGE' else 'TOO CLOSE'
            print(f'  {self._reading_count:<6} {label:>10}   '
                  f'{"":32}   {_RED}✖ {label}{_RESET}', flush=True)
            return

        try:
            distance_cm = float(value_str)
        except ValueError:
            return

        distance_m = distance_cm / 100.0
        msg.range  = distance_m

        # Publish
        self.range_pub.publish(msg)
        f = Float32(); f.data = distance_m
        self.dist_pub.publish(f)
        self._broadcast_tf(now)

        self._reading_count += 1

        # ── Live terminal output ───────────────────────────────────────────
        bar    = _bar(distance_cm)
        status = _status_label(distance_cm)

        if distance_cm >= 100:
            dist_str = f'{distance_cm:6.1f} cm'
        else:
            dist_str = f'{distance_cm:6.2f} cm'

        print(f'  {self._reading_count:<6} {dist_str:>10}   {bar}   {status}',
              flush=True)

    def _broadcast_tf(self, now):
        t = TransformStamped()
        t.header.stamp    = now
        t.header.frame_id = self.parent_frame
        t.child_frame_id  = self.frame_id
        t.transform.translation.x = self.sensor_x
        t.transform.translation.y = self.sensor_y
        t.transform.translation.z = self.sensor_z
        t.transform.rotation.w = 1.0
        self.tf_broadcaster.sendTransform(t)

    def destroy_node(self):
        self._running = False
        self._close_serial()
        print(f'\n{_CYAN}{"═"*54}{_RESET}\n')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
