#!/usr/bin/env python3
# ping.py — 매칭이 끝난 뒤 보내기 시작하고, 돌아온 시각으로 RTT를 잰다
# 사용법: ROS_DOMAIN_ID=5 python3 ping.py <reliable|best_effort> <tag>
import sys, time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String

N = 200          # 보낼 개수
TICK = 0.1       # 틱 = 발행 주기 (초) = 10 Hz
SETTLE = 10      # 매칭 후 안정화 1.0초
DRAIN = 30       # 마지막 발행 후 3.0초 더 기다림
TIMEOUT = 200    # 20초 안에 매칭 안 되면 포기

def make_qos(name):
    r = ReliabilityPolicy.RELIABLE if name == 'reliable' else ReliabilityPolicy.BEST_EFFORT
    return QoSProfile(depth=10, reliability=r, durability=DurabilityPolicy.VOLATILE)

class Ping(Node):
    def __init__(self, qos_name, tag):
        super().__init__('ping')
        self.qos_name, self.tag = qos_name, tag
        qos = make_qos(qos_name)
        self.pub = self.create_publisher(String, '/ping', qos)
        self.create_subscription(String, '/pong', self.on_pong, qos)
        self.seq, self.rtts, self.done = 0, {}, False
        self.state, self.cnt = 'wait', 0
        self.create_timer(TICK, self.tick)
        self.get_logger().info(f'ping start  qos={qos_name}  tag={tag}  N={N}  (매칭 대기)')

    def matched(self):
        # 내가 보낼 상대가 있고, 답을 보낼 상대도 보일 때
        return self.pub.get_subscription_count() > 0 and self.count_publishers('/pong') > 0

    def tick(self):
        if self.state == 'wait':
            self.cnt += 1
            if self.matched():
                self.get_logger().info(f'매칭 완료 ({self.cnt * TICK:.1f}s) — 안정화')
                self.state, self.cnt = 'settle', 0
            elif self.cnt >= TIMEOUT:
                print(f"\n[{self.tag}] qos={self.qos_name}  매칭 실패 (20초 초과)")
                rclpy.shutdown()
            return

        if self.state == 'settle':
            self.cnt += 1
            if self.cnt >= SETTLE:
                self.get_logger().info('발행 시작')
                self.state, self.cnt = 'send', 0
            return

        if self.state == 'send':
            # 한쪽 시계만 쓰므로 두 PC의 시계 차이가 결과에 섞이지 않는다
            self.pub.publish(String(data=f"{self.seq},{time.monotonic()}"))
            self.seq += 1
            if self.seq >= N:
                self.state, self.cnt = 'drain', 0
            return

        if self.state == 'drain':
            self.cnt += 1
            if self.cnt >= DRAIN:
                self.report()

    def on_pong(self, msg):
        seq, t0 = msg.data.split(',')
        self.rtts[int(seq)] = (time.monotonic() - float(t0)) * 1000.0

    def report(self):
        if self.done:
            return
        self.done = True
        v = sorted(self.rtts.values())
        if not v:
            print(f"\n[{self.tag}] qos={self.qos_name}  no reply  (매칭 실패 의심)")
            rclpy.shutdown(); return
        p95 = v[int(0.95 * (len(v) - 1))]
        p50 = v[len(v) // 2]
        mean = sum(v) / len(v)
        loss = 100.0 * (N - len(v)) / N
        print(f"\n[{self.tag}] qos={self.qos_name}  n={len(v)}/{N}  "
              f"loss={loss:.1f}%  mean={mean:.1f}ms  p50={p50:.1f}ms  "
              f"p95={p95:.1f}ms  max={v[-1]:.1f}ms")
        with open('results.csv', 'a') as f:
            f.write(f"{self.tag},{self.qos_name},{len(v)},{N},{loss:.2f},"
                    f"{mean:.2f},{p50:.2f},{p95:.2f},{v[-1]:.2f}\n")
        rclpy.shutdown()

qos_name = sys.argv[1] if len(sys.argv) > 1 else 'reliable'
tag      = sys.argv[2] if len(sys.argv) > 2 else 'loss0'
rclpy.init()
rclpy.spin(Ping(qos_name, tag))
