#!/usr/bin/env python3
import re
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String

WORD = re.compile(r'word=(\S+)')

class Stage2(Node):
    def __init__(self):
        super().__init__('stage2_solver')
        self.a = None
        self.b = None
        self.logged = False

        # config: RELIABLE + TRANSIENT_LOCAL (둘 다 맞춰야 과거 값을 받는다)
        qos_config = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)

        # stream: BEST_EFFORT + VOLATILE (reliable로 요청하면 매칭 실패)
        qos_stream = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE)

        # answer: 로봇이 RELIABLE을 요청
        qos_answer = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE)

        self.create_subscription(String, '/bb_b7f2/config', self.cb_config, qos_config)
        self.create_subscription(String, '/bb_b7f2/stream', self.cb_stream, qos_stream)
        self.pub = self.create_publisher(String, '/bb_b7f2/answer', qos_answer)

        self.create_timer(1.0, self.try_answer)

    def cb_config(self, msg):
        m = WORD.search(msg.data)
        if m:
            self.a = m.group(1)
        self.get_logger().info(f'[config] {msg.data}')   # 잘린 '다음 신호' 확인용

    def cb_stream(self, msg):
        m = WORD.search(msg.data)
        if m:
            self.b = m.group(1)

    def try_answer(self):
        if self.a is None or self.b is None:
            self.get_logger().info(f'대기 중 A={self.a} B={self.b}')
            return
        answer = f'{self.a}-{self.b}'
        self.pub.publish(String(data=answer))
        if not self.logged:
            self.get_logger().info(f'[answer] {answer}')
            self.logged = True

rclpy.init()
rclpy.spin(Stage2())
