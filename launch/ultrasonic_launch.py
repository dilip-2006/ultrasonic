#!/usr/bin/env python3
"""
ultrasonic_launch.py — Sensor nodes only (no RViz2 auto-open)
Measurements are printed live in the terminal.

To open RViz2 manually:
  rviz2 -d ~/ir/src/ultrasonic/rviz/ultrasonic.rviz

To take a single on-demand measurement:
  ros2 run ultrasonic measure_client
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import LogInfo


def generate_launch_description():

    welcome_msg = LogInfo(msg="""
\033[96m\033[1m
=========================================================
  _   _ _   _____ ____      _      ____   ___  _   _ _  ____
 | | | | | |_   _|  _ \    / \    / ___| / _ \| \ | | |/ ___|
 | | | | |   | | | |_) |  / _ \   \___ \| | | |  \| | | |
 | |_| | |___| | |  _ <  / ___ \   ___) | |_| | |\  | |___
  \___/|_____|_| |_| \_\/_/   \_\ |____/ \___/|_| \_|_|\____|

  HC-SR04 Ultrasonic Sensor  →  ROS 2 Humble  →  RViz2
  By Dilip Kumar
=========================================================
\033[0m""")

    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for Arduino Nano (/dev/ttyUSB0 or /dev/ttyACM0)',
    )
    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='115200',
        description='Baud rate matching the Arduino sketch',
    )
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='ultrasonic_link',
        description='TF frame name for the ultrasonic sensor',
    )
    parent_frame_arg = DeclareLaunchArgument(
        'parent_frame',
        default_value='base_link',
        description='Parent TF frame',
    )

    # Node 1: Ultrasonic serial reader — prints live to terminal
    ultrasonic_node = Node(
        package='ultrasonic',
        executable='ultrasonic_node',
        name='ultrasonic_node',
        output='screen',
        parameters=[{
            'serial_port':  LaunchConfiguration('serial_port'),
            'baud_rate':    LaunchConfiguration('baud_rate'),
            'frame_id':     LaunchConfiguration('frame_id'),
            'parent_frame': LaunchConfiguration('parent_frame'),
            'sensor_x': 0.05,
            'sensor_y': 0.0,
            'sensor_z': 0.05,
        }],
    )

    # Node 2: RViz marker publisher (delayed 1 s)
    marker_node = TimerAction(
        period=1.0,
        actions=[
            Node(
                package='ultrasonic',
                executable='rviz_marker_node',
                name='rviz_marker_node',
                output='screen',
            ),
        ],
    )

    return LaunchDescription([
        welcome_msg,
        serial_port_arg,
        baud_rate_arg,
        frame_id_arg,
        parent_frame_arg,
        ultrasonic_node,
        marker_node,
    ])
