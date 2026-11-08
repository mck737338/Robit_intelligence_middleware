#!/usr/bin/env python3
# pong.py — /ping 으로 온 메시지를 그대로 /pong 으로 되돌려준다
# 사용법: ROS_DOMAIN_ID=5 python3 pong.py <reliable|best_effort>
import sys, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String

def make_qos(name):
    r = ReliabilityPolicy.RELIABLE if name == 'reliable' else ReliabilityPolicy.BEST_EFFORT
    return QoSProfile(depth=10, reliability=r, durability=DurabilityPolicy.VOLATILE)

class Pong(Node):
    def __init__(self, qos_name):
        super().__init__('pong')
        qos = make_qos(qos_name)
        self.pub = self.create_publisher(String, '/pong', qos)
        self.create_subscription(String, '/ping', lambda m: self.pub.publish(m), qos)
        self.get_logger().info(f'pong ready  qos={qos_name}')

qos_name = sys.argv[1] if len(sys.argv) > 1 else 'reliable'
rclpy.init()
rclpy.spin(Pong(qos_name))
