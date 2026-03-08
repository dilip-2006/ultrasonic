#!/usr/bin/env python3
"""
rviz_marker_node — Ultrasonic Range → RViz2 Visual Markers
===========================================================
Subscribes to /ultrasonic/range and publishes two markers:
  • A distance cone   (TRIANGLE_LIST) — color-coded by distance
  • A text label      (TEXT_VIEW_FACING) — shows distance in cm

Color scheme:
  🟢 Green  : > 100 cm  (safe)
  🟡 Yellow : 30–100 cm (caution)
  🔴 Red    : < 30 cm   (danger)
"""

import math
from typing import List

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from sensor_msgs.msg import Range
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA


class RvizMarkerNode(Node):
    """Converts sensor_msgs/Range into RViz2 visualisation markers."""

    # Distance thresholds (metres)
    DANGER_M   = 0.30   # < 30 cm → red
    CAUTION_M  = 1.00   # < 100 cm → yellow
    # >= CAUTION_M → green

    CONE_SEGMENTS = 32  # polygon smoothness

    def __init__(self):
        super().__init__('rviz_marker_node')

        sensor_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )

        self.sub = self.create_subscription(
            Range, '/ultrasonic/range',
            self._range_callback, sensor_qos)

        self.marker_pub = self.create_publisher(
            MarkerArray, '/ultrasonic/markers', 10)

        self.get_logger().info('RvizMarkerNode ready — listening on /ultrasonic/range')

    # ──────────────────────────────────────────────────────────────────────────

    def _range_callback(self, msg: Range):
        distance_m = msg.range

        # Handle out-of-range / too-close
        if not math.isfinite(distance_m) or distance_m <= 0:
            return

        color = self._distance_color(distance_m)
        fov   = msg.field_of_view         # radians (cone half-angle)
        frame = msg.header.frame_id

        array = MarkerArray()
        array.markers.append(
            self._make_cone_marker(frame, msg.header.stamp,
                                   distance_m, fov, color))
        array.markers.append(
            self._make_text_marker(frame, msg.header.stamp,
                                   distance_m))
        self.marker_pub.publish(array)

    # ──────────────────────────────────────────────────────────────────────────
    # Color coding
    # ──────────────────────────────────────────────────────────────────────────

    def _distance_color(self, distance_m: float) -> ColorRGBA:
        c = ColorRGBA()
        c.a = 0.55   # semi-transparent

        if distance_m < self.DANGER_M:
            # Red
            c.r, c.g, c.b = 1.0, 0.18, 0.18
        elif distance_m < self.CAUTION_M:
            # Interpolate yellow→orange based on proximity
            t = (self.CAUTION_M - distance_m) / (self.CAUTION_M - self.DANGER_M)
            c.r = 1.0
            c.g = max(0.18, 0.85 - t * 0.67)
            c.b = 0.0
        else:
            # Green
            c.r, c.g, c.b = 0.18, 0.9, 0.35

        return c

    # ──────────────────────────────────────────────────────────────────────────
    # Cone marker (TRIANGLE_LIST — sensor FOV sweep)
    # ──────────────────────────────────────────────────────────────────────────

    def _make_cone_marker(self, frame: str, stamp,
                          dist: float, half_fov: float,
                          color: ColorRGBA) -> Marker:
        m = Marker()
        m.header.frame_id = frame
        m.header.stamp    = stamp
        m.ns              = 'ultrasonic'
        m.id              = 0
        m.type            = Marker.TRIANGLE_LIST
        m.action          = Marker.ADD
        m.lifetime.sec    = 1            # auto-disappear if no new data

        m.scale.x = m.scale.y = m.scale.z = 1.0
        m.color = color

        # Build fan of triangles from origin outward
        apex = Point(x=0.0, y=0.0, z=0.0)
        n = self.CONE_SEGMENTS

        for i in range(n):
            angle0 = -half_fov + (2 * half_fov * i       / n)
            angle1 = -half_fov + (2 * half_fov * (i + 1) / n)

            p0 = Point(
                x=dist * math.cos(angle0),
                y=dist * math.sin(angle0),
                z=0.0,
            )
            p1 = Point(
                x=dist * math.cos(angle1),
                y=dist * math.sin(angle1),
                z=0.0,
            )

            m.points.extend([apex, p0, p1])

        return m

    # ──────────────────────────────────────────────────────────────────────────
    # Text marker (distance label)
    # ──────────────────────────────────────────────────────────────────────────

    def _make_text_marker(self, frame: str, stamp, dist: float) -> Marker:
        m = Marker()
        m.header.frame_id = frame
        m.header.stamp    = stamp
        m.ns              = 'ultrasonic'
        m.id              = 1
        m.type            = Marker.TEXT_VIEW_FACING
        m.action          = Marker.ADD
        m.lifetime.sec    = 1

        # Position text above the cone tip
        m.pose.position.x = dist
        m.pose.position.y = 0.0
        m.pose.position.z = 0.08
        m.pose.orientation.w = 1.0

        m.scale.z = 0.08         # text height in metres
        m.color.r = m.color.g = m.color.b = 1.0
        m.color.a = 1.0

        dist_cm = dist * 100.0
        if dist_cm >= 100:
            m.text = f'{dist_cm:.0f} cm'
        else:
            m.text = f'{dist_cm:.1f} cm'

        return m


def main(args=None):
    rclpy.init(args=args)
    node = RvizMarkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
