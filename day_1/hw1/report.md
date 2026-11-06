# ROS 2 미들웨어 Day 1 보고서

 **예비단원 김민찬**
 ### 결과

```
minchan@minchan-IdeaPad-Slim-3-15ABR8:~$ ros2 run robit_blackbox report --name "김민찬"
=== ROBIT 블랙박스 제출 요약 ===
이름: 김민찬 (id c03b8270)
  1단계 정찰                 통과  2026-11-05T21:47:23+09:00
  2단계 QoS                통과  2026-11-05T22:27:56+09:00
  3단계 Cyclone 설정         통과  2026-11-05T23:00:05+09:00
  4단계 고장 진단 (도전)         통과  2026-11-05T22:46:18+09:00
기록 검증: 정상
기록 해시: dbf18166f6a96141

```

## 1단계 정찰 — 통과 (2026-11-05T21:47:23+09:00)

### 목표

로봇이 떠 있는 Domain ID와 토픽을 찾아내고, 정찰 신호 안의 챌린지 문자열에 응답하기
도메인·토픽·QoS는 실행할 때마다 무작위로 정해지므로 사전 정보 없이 조사로만 알아내기

---

## 1-0. 조사 전 환경 점검 (교재 기초 3장)

조사를 시작하기 전에 **내 터미널 설정이 원인이 아님을 먼저 확인**해야 한다.
그렇지 않으면 "안 보임"이 로봇 탓인지 내 환경 탓인지 구분할 수 없다.

### 실행

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
env | grep -E "ROS|RMW|CYCLONE"
```

### 출력 (관련 부분 발췌)

```
ROS_VERSION=2
ROS_PYTHON_VERSION=3
ROS_DOMAIN_ID=99
ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ROS2_WS=/home/minchan/ros2_ws
ROS_DISTRO=jazzy
```

### 설정 확인, 수정

| 변수 | 값 | 판단 |
|---|---|---|
| `ROS_DOMAIN_ID` | **99** | `.bashrc`에 직접 설정해 둔 값. 이 상태로 스캔하면 **99번 방만** 보인다 → 해제 필요 |
| `ROS_AUTOMATIC_DISCOVERY_RANGE` | SUBNET | 기본값과 동일. 발견 범위를 좁히지 않으므로 무해 |
| `RMW_IMPLEMENTATION` | 없음 (미설정) | 기본값 Fast DDS 사용. 로봇 터미널과 동일하므로 1단계 조건에 맞음 |
| `CYCLONEDDS_URI` | 없음 | Cyclone 설정이 끼어들지 않음 |

**판단:** .bashrc로 도메인이 99로 고정되어 있음. 따라서 도메인을 해제하고 1단계를 진행함

```bash
unset ROS_DOMAIN_ID
ros2 daemon stop
```

- `unset`은 **이 터미널에만** 적용된다. `.bashrc`는 그대로 두었으므로 새 터미널을 열면 99가 다시 들어온다 → 스캔 스크립트 안에도 `unset`을 넣어 두었다.
- `ros2 daemon stop`은 도메인 99로 떠 있던 데몬이 옛 캐시 정보를 물고 있지 않게 하기 위함이다.


## 1-1. 도메인 스캔

### 접근 방법

로봇이 어느 도메인에 있는지 모르므로 권장 범위 0~101을 전부 돌면서
`bb_` 접두사를 가진 토픽이 보이는 도메인을 찾는다.

### 스크립트 (`scan_domains.sh`)

```bash
#!/usr/bin/env bash
# scan_domains.sh — bb_ 토픽이 있는 도메인을 찾는다
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
unset ROS_DOMAIN_ID

for d in $(seq 0 101); do
  out=$(ROS_DOMAIN_ID=$d ros2 topic list --no-daemon --spin-time 2 2>/dev/null | grep '^/bb_')
  if [ -n "$out" ]; then
    echo "=== domain $d ==="
    echo "$out"
  fi
done
```

### 스캔 옵션

- **`--no-daemon`**
  교육자료 1장의 내용에 따라, daemon은 rmw와 도메인별로 따로 뜨기 때문에 이 옵션이 없으면 스캔 과정에서 도메인마다
  daemon이 생겨 102개가 뜨게 되므로 daemon을 제외했다..

- **`--spin-time`**
  교육자료 2장의 내용대로 발견 단계는 "나 여기 있어요"를 주기적으로 알리는 과정이다. 참가자를 찿자마자 조회하면
  아직 아무 알림도 못 받은 상태라 있는 토픽도 안 보인다. 따라서 대기 시간을 설정하였다.

---

## 1-2. 1차 스캔 (spin-time 2초) — 부분 실패

### 출력

```
=== domain 48 ===
/bb_b7f2/cmd
/bb_b7f2/command
=== domain 89 ===
/bb_b7f2/answer
/bb_b7f2/config
/bb_b7f2/stream
```

### 판단

로봇 ID가 `bb_b7f2`라는 것, 그리고 도메인 48·89의 존재는 확인했다.
그러나 교육자료에 따르면 1단계 정찰 신호는 `/bb_xxxx/telemetry`인데
그 토픽이 어느 도메인에도 없었다.

토픽 이름으로 각 방의 용도를 추정했다.

| 도메인 | 토픽 | 추정 단계 |
|---|---|---|
| 48 | `/bb_b7f2/cmd`, `/bb_b7f2/command` | 4단계 진단 (`cmd`) |
| 89 | `/bb_b7f2/config`, `/bb_b7f2/stream`, `/bb_b7f2/answer` | 2단계 QoS |
| ? | `telemetry` 없음 | **1단계 누락** |

2단계·4단계 방은 찾았는데 1단계 방만 빠졌다는 점에서,
"그 도메인이 존재하지 않는다"보다 "스캔이 놓쳤다" 쪽을 먼저 의심했다.
근거는 SPDP가 주기적 알림이라 2초 창에 운 나쁘게 걸리면 놓칠 수 있다고 생각했다.

### 가설

`--spin-time 2`가 짧았다. 시간을 늘리면 잡힐 것이다.

---

## 1-3. 2차 스캔 (spin-time 5초) — 성공

`--spin-time` 값만 **2 → 5로 한 가지만** 바꿔 재실행했다.

### 출력

```
=== domain 48 ===
/bb_b7f2/cmd
/bb_b7f2/command
=== domain 72 ===
/bb_b7f2/ack
/bb_b7f2/telemetry
=== domain 89 ===
/bb_b7f2/answer
/bb_b7f2/config
/bb_b7f2/stream
```

### 결과 및 해석

**도메인 72가 새로 나타났고, 여기에 `/bb_b7f2/telemetry`가 있었다.**

같은 스크립트, 같은 로봇, 같은 PC인데 대기 시간만 늘렸더니 결과가 달라졌다.
발견은 SPDP 주기만큼 시간이 걸린다는 것을 확인할 수 있었다. 토픽 목록이 비어 있다고 해서 그 도메인에 아무도 없다고 확신해서는 안된다.


## 1-4. telemetry의 타입·QoS 확인

메시지를 읽기 전에 QoS를 먼저 확인했다.
바로 echo를 했다가 아무것도 안 나오면 "발견 실패"인지 "QoS 비호환"인지 구분할 수 없기 때문이다.

### 실행

```bash
ROS_DOMAIN_ID=72 ros2 topic info -v /bb_b7f2/telemetry
```

### 출력

```
Type: std_msgs/msg/String

Publisher count: 1

Node name: bb_s1
Node namespace: /
Topic type: std_msgs/msg/String
Topic type hash: RIHS01_df668c740482bbd48fb39d76a70dfd4bd59db1288021743503259e948f6b1a18
Endpoint type: PUBLISHER
GID: 01.0f.52.3d.40.32.75.07.00.00.00.00.00.00.13.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 0
```

## 1-5. 정찰 신호 수신

### 실행

```bash
ROS_DOMAIN_ID=72 ros2 topic echo /bb_b7f2/telemetry
```

### 출력 (발췌)

```
data: 'BB1 pos=(0.06,-2.23) | 챌린지: NEBULA-8925 | 이 단어를 그대로 /bb_b7f2/ack 로 보내라 | 다음 신호: 도메인 89'
---
data: 'BB1 pos=(0.06,-2.26) | 챌린지: NEBULA-8925 | 이 단어를 그대로 /bb_b7f2/ack 로 보내라 | 다음 신호: 도메인 89'
---
data: 'BB1 pos=(0.03,-2.35) | 챌린지: NEBULA-8925 | 이 단어를 그대로 /bb_b7f2/ack 로 보내라 | 다음 신호: 도메인 89'
---
(이하 같은 내용 반복, pos 값만 변함)
```

### 읽어낸 정보

| 항목 | 값 |
|---|---|
| 챌린지 문자열 | **`NEBULA-8925`** |
| 응답 토픽 | `/bb_b7f2/ack` (같은 도메인 72) |
| 다음 신호 | 도메인 89 → 2차 스캔에서 찾은 2단계 방과 일치 |

---

## 1-6. ack 구독자 확인

응답을 쏘기 전에 받는 쪽의 조건을 먼저 확인했다.

### 실행

```bash
ROS_DOMAIN_ID=72 ros2 topic info -v /bb_b7f2/ack
```

### 출력

```
Type: std_msgs/msg/String

Publisher count: 0

Subscription count: 1

Node name: bb_s1
Node namespace: /
Topic type: std_msgs/msg/String
Topic type hash: RIHS01_df668c740482bbd48fb39d76a70dfd4bd59db1288021743503259e948f6b1a18
Endpoint type: SUBSCRIPTION
GID: 01.0f.52.3d.40.32.75.07.00.00.00.00.00.00.14.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite
```

### 판단

- **Subscription count: 1** — 로봇(`bb_s1`)이 이 토픽을 듣고 있다.
- **Publisher count: 0** — 아직 아무도 발행하지 않음. 이 토픽에 발행해야 한다.
- **요청 QoS: RELIABLE / VOLATILE** — 3장 호환 규칙에 따라
  내 publisher도 기본값(reliable)으로 쏘면 매칭된다.

---

## 1-7. 정답 제출

### 실행

```bash
ROS_DOMAIN_ID=72 ros2 topic pub /bb_b7f2/ack std_msgs/msg/String "{data: 'NEBULA-8925'}"
```

### 결과

로봇 터미널에 1단계 통과 메시지 출력 → 통과 시각 `2026-11-05T21:47:23+09:00`

---

## 1-8. 통과 확인

```bash
ros2 run robit_blackbox status --name "김민찬"
```

```
이름: 김민찬
  1단계 정찰                 통과  2026-11-05T21:47:23+09:00
  2단계 QoS                -
  3단계 Cyclone 설정         -
  4단계 고장 진단 (도전)         -
  5단계 자유 탐구        보고서로 제출
```

---

## 1-9. 1단계 시도 기록

| # | 시도한 것 | 결과 | 거기서 배운 것 |
|---|---|---|---|
| 1 | `env`로 환경변수 먼저 점검 | `ROS_DOMAIN_ID=99` 발견 | 스캔 전에 해제하지 않았다면 99번 방만 보고 "로봇이 없다"고 잘못 결론 내렸을 것 |
| 2 | `--spin-time 2`로 0~101 전수 스캔 | 도메인 48, 89만 발견. **telemetry 누락** | 토픽 목록이 비었다고 그 도메인이 비었다는 뜻이 아니다 |
| 3 | `--spin-time 5`로 재스캔 | **도메인 72 발견** | SPDP는 주기적 알림이므로 발견에는 시간이 필요하다. 대기 시간이 스캔 신뢰도를 좌우한다 |


---
## 2단계 QoS — 통과 (2026-11-05T22:27:56+09:00)

### 목표

도메인 89에서 QoS가 서로 다른 두 토픽(`config`, `stream`)의 값을 모두 수신하고,
직접 작성한 구독 노드로 두 값을 조합해 `/bb_b7f2/answer`로 응답한다.

---

## 2-1. topic info가 "Unknown topic"을 반환한 문제

### 증상

```bash
ROS_DOMAIN_ID=89 ros2 topic info -v /bb_b7f2/config
ROS_DOMAIN_ID=89 ros2 topic info -v /bb_b7f2/stream
ROS_DOMAIN_ID=89 ros2 topic info -v /bb_b7f2/answer
```

```
Unknown topic '/bb_b7f2/config'
Unknown topic '/bb_b7f2/stream'
Unknown topic '/bb_b7f2/answer'
```

1단계 스캔에서 분명히 존재를 확인한 토픽인데 조회가 실패했다.

### 교차 검증

같은 도메인을 `--no-daemon`으로 조회하면 정상적으로 나왔다.

```bash
ROS_DOMAIN_ID=89 ros2 topic list --no-daemon --spin-time 5
```

```
/bb_b7f2/answer
/bb_b7f2/config
/bb_b7f2/stream
/parameter_events
/rosout
```

**같은 도메인, 같은 시점인데 조회 방식에 따라 결과가 달랐다.**
따라서 로봇 문제가 아니라 조회 경로의 문제로 판단했다.

### 원인 분석

- `ros2 topic info`는 daemon을 거쳐 캐시된 정보를 읽는다. `--no-daemon` 옵션이 없다.
- `ros2 topic list --no-daemon`은 그 자리에서 직접 참가자를 띄워 조회하므로 daemon과 무관하다.
- 즉 도메인 89용 daemon이 아직 뜨지 않았거나 정보를 모으기 전이어서 캐시가 비어 있었다.
- 1장에 적힌 내용대로 daemon은 rmw와 도메인별로 따로 뜬다. 1단계에서 도메인 72를 다룰 때는
  이미 해당 daemon이 떠서 정보를 모아 둔 상태였기 때문에 바로 조회됐던 것이다.

### 시도한 조치와 그 결과

```bash
ros2 daemon stop
```
```
The daemon is not running
```

이 명령은 환경변수 없이 실행해 **도메인 99**(`.bashrc` 기본값) daemon을 대상으로 한 것이어서
도메인 89와는 무관했다. 여기서 "daemon은 도메인별로 독립"이라는 점을 재확인했다.

### 해결

`--no-daemon`을 **빼고** 목록을 조회해 도메인 89용 daemon을 먼저 띄우고 정보를 모으게 했다.

```bash
ROS_DOMAIN_ID=89 ros2 topic list --spin-time 5
```
```
/bb_b7f2/answer
/bb_b7f2/config
/bb_b7f2/stream
/parameter_events
/rosout
```

이후 `topic info -v`가 정상 동작했다.

---

## 2-2. 세 토픽의 QoS 확인

### `/bb_b7f2/config`

```
Type: std_msgs/msg/String
Publisher count: 1
Node name: bb_s2
Endpoint type: PUBLISHER
GID: 01.0f.52.3d.42.32.01.fb.00.00.00.00.00.00.13.03
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: TRANSIENT_LOCAL
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
Subscription count: 0
```

### `/bb_b7f2/stream`

```
Type: std_msgs/msg/String
Publisher count: 1
Node name: bb_s2
Endpoint type: PUBLISHER
GID: 01.0f.52.3d.42.32.01.fb.00.00.00.00.00.00.14.03
QoS profile:
  Reliability: BEST_EFFORT
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
Subscription count: 0
```

### `/bb_b7f2/answer`

```
Type: std_msgs/msg/String
Publisher count: 0
Subscription count: 1
Node name: bb_s2
Endpoint type: SUBSCRIPTION
GID: 01.0f.52.3d.42.32.01.fb.00.00.00.00.00.00.15.04
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
```

### 정리 및 요청 QoS 설계

| 토픽 | 역할 | 제공/요청 QoS | 내가 설정해야 할 값 |
|---|---|---|---|
| `config` | 발행자 | RELIABLE + **TRANSIENT_LOCAL** | reliable + **transient_local** |
| `stream` | 발행자 | **BEST_EFFORT** + VOLATILE | **best_effort** + volatile |
| `answer` | 로봇의 구독자 | **RELIABLE** 요청 + VOLATILE | 내 publisher는 **reliable** 제공 |


1. `config`를 volatile로 요청하면 -> 연결은 되지만 과거 값을 받지 못한다.
   설정성 토픽이라 이미 한 번 발행하고 멈췄을 가능성이 높아 영영 못 받는다.
2. `stream`을 reliable로 요청하면 -> 제공(best effort) < 요청(reliable)이라
   연결 자체가 성립하지 않는다. 에러 없이 조용하다.
3. `answer`에 best effort로 발행하면 → 로봇 구독자가 reliable을 요청하므로 매칭 실패.

즉 한 노드 안에서 토픽마다 QoS를 따로 지정해야 한다.

---

## 2-3. CLI로 값 선확인 — reliability 누락으로 실패

### 1차 시도 (실패)

```bash
ROS_DOMAIN_ID=89 ros2 topic echo --qos-durability transient_local /bb_b7f2/config
```

→ **아무 출력도 없었다.**

같은 시점에 stream은 정상 수신됐다.

```bash
ROS_DOMAIN_ID=89 ros2 topic echo --qos-reliability best_effort /bb_b7f2/stream
```
```
data: BB2-B word=ac42 n=44498
---
data: BB2-B word=ac42 n=44499
---
data: BB2-B word=ac42 n=44500
---
(이하 1씩 증가하며 반복)
```

### 원인

`--qos-durability`만 지정하면 reliability는 CLI 기본값이 적용된다.
durability만 맞춰 놓고 reliability가 어긋나면 두 정책 중 하나만 깨져도 매칭이 성립하지 않는다.
QoS 호환은 정책별로 각각 판정되며, 전부 만족해야 연결된다.

### 2차 시도 (성공)

두 정책을 모두 명시했다.

```bash
ROS_DOMAIN_ID=89 ros2 topic echo \
  --qos-durability transient_local \
  --qos-reliability reliable \
  --qos-depth 1 \
  /bb_b7f2/config
```

```
data: BB2-A word=e4c2 | 스트림은 /bb_b7f2/stream | 각 메시지의 word= 뒤 값 두 개를 A-B 순서로 "-" 로 이어 /bb_b7f2/answer 로 보내라 (구독 노드가 켜져 있는 동안) | 다음 신호:...
---
```

---

## 2-4. 수신 내용 해석

| 출처 | 메시지 | 추출값 |
|---|---|---|
| `config` (A) | `BB2-A word=e4c2 \| ...` | **`e4c2`** |
| `stream` (B) | `BB2-B word=ac42 n=44518` | **`ac42`** |

### 지시사항 해석

- 조합 규칙: word= 뒤 값 두 개를 **A-B 순서로 `-`로 연결** → **`e4c2-ac42`**
- `n=` 값은 1씩 증가하는 카운터일 뿐 조합에 쓰이지 않는다 → 무시
- **"(구독 노드가 켜져 있는 동안)"** 이라는 단서가 중요하다.
  두 토픽을 구독한 상태를 유지하면서 answer를 발행해야 한다는 뜻으로 읽었다.
  따라서 `ros2 topic pub`으로 문자열만 쏘는 방식은 통과 조건을 만족하지 못할 것으로 판단하고
  구독 노드에서 직접 발행하도록 구현했다. (과제 명세의 "직접 만든 구독 노드로"와도 일치)
- CLI 출력에서 잘린 "다음 신호:..." 부분은 노드 로그에서 전문을 확보했다 (2-6 참조)

---

## 2-5. 구독 노드 (`stage2_node.py`)

```python
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

        # answer: 로봇 구독자가 RELIABLE을 요청
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
        self.get_logger().info(f'[config] {msg.data}')

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
```

---

## 2-6. 실행과 결과

### 실행

```bash
cd ~/ros2_ws/mission_day1
ROS_DOMAIN_ID=89 python3 stage2_node.py
```

### 출력

```
[INFO] [1793885274.016605464] [stage2_solver]: 대기 중 A=None B=None
[INFO] [1793885275.005562244] [stage2_solver]: 대기 중 A=None B=None
[INFO] [1793885275.452495472] [stage2_solver]: [config] BB2-A word=e4c2 | 스트림은 /bb_b7f2/stream | 각 메시지의 word= 뒤 값 두 개를 A-B 순서로 "-" 로 이어 /bb_b7f2/answer 로 보내라 (구독 노드가 켜져 있는 동안) | 다음 신호: 도메인 48의 /bb_b7f2/cmd
[INFO] [1793885276.005552242] [stage2_solver]: [answer] e4c2-ac42
```


### 통과 확인

```bash
ros2 run robit_blackbox status --name "김민찬"
```

```
이름: 김민찬
  1단계 정찰                 통과  2026-11-05T21:47:23+09:00
  2단계 QoS                통과  2026-11-05T22:27:56+09:00
  3단계 Cyclone 설정         -
  4단계 고장 진단 (도전)         -
  5단계 자유 탐구        보고서로 제출
```

---

## 2-7. 2단계 시도 기록

| # | 시도한 것 | 결과 | 거기서 배운 것 |
|---|---|---|---|
| 1 | `topic info -v` 세 개를 연속 실행 | 전부 `Unknown topic` | `topic info`는 daemon 경유라 캐시가 비면 "없다"고 답한다. 토픽이 없는 것과 구분되지 않는다 |
| 2 | `topic list --no-daemon`으로 교차 검증 | 토픽 정상 출력 | 조회 방식에 따라 결과가 달라진다 → 로봇이 아니라 조회 경로의 문제로 범위를 좁혔다 |
| 3 | `ros2 daemon stop` | `The daemon is not running` | 환경변수 없이 실행해 도메인 99 daemon을 본 것. **daemon은 도메인별로 독립**임을 재확인 |
| 4 | `topic list`(daemon 사용)로 캐시 생성 후 `info` | 정상 조회 | daemon을 먼저 깨워 정보를 모으게 하는 순서가 필요하다 |
| 5 | `echo --qos-durability transient_local`만 지정 | **수신 없음** | durability만 맞추면 부족하다. reliability가 어긋나면 매칭 자체가 안 된다 |
| 6 | `--qos-reliability reliable`까지 추가 | **수신 성공** | QoS 호환은 정책별로 각각 판정된다. **전부** 만족해야 연결된다 |

---

## 4단계 고장 진단 (도전) — 통과 (2026-11-05T22:46:18+09:00)

### 목표

도메인 48에서 talker는 정상 동작하지만 listener가 신호를 받지 못하는 상태다.
listener 설정 파일의 틀린 값을 조사로 찾아 고친다.

1단계(발견)와 2단계(매칭)에서 쓴 도구를 모두 동원해, 이번에는
talker와 listener 양쪽을 대조해 불일치 지점을 특정하는 것이 과제다.

진입 경로: 2단계 `config` 메시지가 알려 준 "다음 신호: 도메인 48의 `/bb_b7f2/cmd`"

---

## 4-1. 도메인 48 조사

2단계에서 겪은 `Unknown topic` 문제를 피하기 위해, daemon을 거치는 목록 조회로 캐시를 먼저 채웠다.

```bash
ROS_DOMAIN_ID=48 ros2 topic list --spin-time 5
```
```
/bb_b7f2/cmd
/bb_b7f2/command
/parameter_events
/rosout
```

### `/bb_b7f2/cmd`

```
Type: std_msgs/msg/Int32

Publisher count: 1

Node name: bb_talker4
Topic type: std_msgs/msg/Int32
Topic type hash: RIHS01_b6578ded3c58c626cfe8d1a6fb6e04f706f97e9f03d2727c9ff4e74b1cef0deb
Endpoint type: PUBLISHER
GID: 01.0f.52.3d.44.32.66.a9.00.00.00.00.00.00.13.03
QoS profile:
  Reliability: BEST_EFFORT
  Durability: VOLATILE
  ...

Subscription count: 0
```

### `/bb_b7f2/command`

```
Type: std_msgs/msg/Int32

Publisher count: 0

Subscription count: 1

Node name: bb_listener4
Topic type: std_msgs/msg/Int32
Topic type hash: RIHS01_b6578ded3c58c626cfe8d1a6fb6e04f706f97e9f03d2727c9ff4e74b1cef0deb
Endpoint type: SUBSCRIPTION
GID: 01.0f.52.3d.46.32.6a.1f.00.00.00.00.00.00.13.04
QoS profile:
  Reliability: RELIABLE
  Durability: VOLATILE
  ...
```

### 결정적 단서

두 토픽에서 노드가 서로 갈려 있었다.

- `/bb_b7f2/cmd` → `bb_talker4`만 있고 **Subscription count: 0** (듣는 사람이 없음)
- `/bb_b7f2/command` → `bb_listener4`만 있고 **Publisher count: 0** (말하는 사람이 없음)

이것으로 `/bb_b7f2/command`가 listener가 잘못된 이름으로 구독 중인 토픽임이 확인했다.

---

## 4-2. 네 항목 대조표


| 항목 | talker 값 (`bb_talker4`) | listener 값 (`bb_listener4`) | 증명 명령 | 판정 |
|---|---|---|---|---|
| DOMAIN | 48 | 48 | `ROS_DOMAIN_ID=48 ros2 topic list --spin-time 5` 에 양쪽 노드가 모두 보임 | 일치 |
| **TOPIC** | `/bb_b7f2/cmd` | `/bb_b7f2/command` | `ros2 topic info -v` 각각 | **불일치** |
| TYPE | `std_msgs/msg/Int32` | `std_msgs/msg/Int32` | `Topic type hash` 까지 동일 (`RIHS01_b6578ded…`) | 일치 |
| **RELIABILITY** | **BEST_EFFORT** (제공) | **RELIABLE** (요청) | `ros2 topic info -v` 의 QoS profile | **불일치** |

**TOPIC 불일치** — 이름이 다르면 애초에 같은 주제가 아니다.
양쪽의 `Subscription count: 0` / `Publisher count: 0`이 증거.

**RELIABILITY 불일치** — 토픽 이름을 고쳐도 이것이 남으면 여전히 연결되지 않는다.
제공(best effort) < 요청(reliable) 이므로 매칭이 성립하지 않는다.

---

## 4-3. 설정 파일 확인

파일 위치: `~/.ros/robit_blackbox/<id>/listener.env`

### id 확인

```bash
ros2 run robit_blackbox report --name "김민찬"
```
```
이름: 김민찬 (id c03b8270)
```

```bash
ls ~/.ros/robit_blackbox/
```
```
57bb0bcb  9c6b9b1b  c03b8270
```

### 수정 전 파일 내용

```bash
cat ~/.ros/robit_blackbox/c03b8270/listener.env
```
```
# 로봇 listener 의 설정. 이 파일을 고치면 listener 가 자동으로 다시 시작된다.
# 값 중 일부가 틀려 있다. 로봇이 보내는 신호를 조사해서 고쳐라.
LISTENER_DOMAIN=48
LISTENER_TOPIC=/bb_b7f2/command
LISTENER_TYPE=Int32
LISTENER_RELIABILITY=reliable
```

## 4-4. 1차 수정 — TOPIC만 변경

두 값을 한 번에 고치면 "둘 다 필요했는지"를 증명할 수 없다.
교재 4장의 "한 번에 하나만 바꾸고 결과를 기록한다"에 따라 TOPIC만 먼저 고쳤다.

```
LISTENER_TOPIC=/bb_b7f2/cmd
```

### 결과

```bash
ROS_DOMAIN_ID=48 ros2 topic info -v /bb_b7f2/cmd
```
```
Type: std_msgs/msg/Int32

Publisher count: 1

Node name: bb_talker4
Endpoint type: PUBLISHER
GID: 01.0f.52.3d.44.32.66.a9.00.00.00.00.00.00.13.03
QoS profile:
  Reliability: BEST_EFFORT
  Durability: VOLATILE

Subscription count: 1

Node name: bb_listener4
Endpoint type: SUBSCRIPTION
GID: 01.0f.52.3d.7f.52.ad.a2.00.00.00.00.00.00.13.04
QoS profile:
  Reliability: RELIABLE
  Durability: VOLATILE
```

-> **통과되지 않음.**

### 이 출력이 보여주는 것 (4단계 핵심 증거)

같은 토픽 하나에 talker와 listener가 모두 모였는데도 연결되지 않는 상태가 한 화면에 잡혔다.

```
Publisher    bb_talker4    Reliability: BEST_EFFORT   <- 제공
Subscription bb_listener4  Reliability: RELIABLE      <- 요청
```

- `Subscription count`가 0 → 1로 바뀌었다 = 토픽 이름 수정은 제대로 반영됐다
- 에러도, 경고도 없이 조용하다

---

## 4-5. 2차 수정 — RELIABILITY 변경

```
LISTENER_RELIABILITY=best_effort
```

### 수정 후 최종 파일

```
# 로봇 listener 의 설정. 이 파일을 고치면 listener 가 자동으로 다시 시작된다.
# 값 중 일부가 틀려 있다. 로봇이 보내는 신호를 조사해서 고쳐라.
LISTENER_DOMAIN=48
LISTENER_TOPIC=/bb_b7f2/cmd
LISTENER_TYPE=Int32
LISTENER_RELIABILITY=best_effort
```

### 결과

```bash
ROS_DOMAIN_ID=48 ros2 topic info -v /bb_b7f2/cmd
```
```
Type: std_msgs/msg/Int32

Publisher count: 1

Node name: bb_talker4
Endpoint type: PUBLISHER
GID: 01.0f.52.3d.44.32.66.a9.00.00.00.00.00.00.13.03
QoS profile:
  Reliability: BEST_EFFORT
  Durability: VOLATILE

Subscription count: 1

Node name: bb_listener4
Endpoint type: SUBSCRIPTION
GID: 01.0f.52.3d.be.52.78.3b.00.00.00.00.00.00.13.04
QoS profile:
  Reliability: BEST_EFFORT
  Durability: VOLATILE
```

양쪽 Reliability가 모두 `BEST_EFFORT`로 일치 → 매칭 성립.
GID가 다시 바뀐 것(`…7f.52.ad.a2` → `…be.52.78.3b`)으로 두 번째 재시작도 확인된다.

### 통과 확인

```bash
ros2 run robit_blackbox status --name "김민찬"
```
```
이름: 김민찬
  1단계 정찰                 통과  2026-11-05T21:47:23+09:00
  2단계 QoS                통과  2026-11-05T22:27:56+09:00
  3단계 Cyclone 설정         -
  4단계 고장 진단 (도전)         통과  2026-11-05T22:46:18+09:00
  5단계 자유 탐구        보고서로 제출
```

---

## 4-6. 수정 내역 요약

| 항목 | 수정 전 | 수정 후 | 수정 이유 |
|---|---|---|---|
| `LISTENER_DOMAIN` | 48 | 48 (변경 없음) | talker와 일치 |
| `LISTENER_TOPIC` | `/bb_b7f2/command` | **`/bb_b7f2/cmd`** | talker가 발행하는 토픽 이름과 달랐다 |
| `LISTENER_TYPE` | Int32 | Int32 (변경 없음) | 타입 해시까지 동일 |
| `LISTENER_RELIABILITY` | `reliable` | **`best_effort`** | 제공(best effort) < 요청(reliable) 이라 매칭 불가 조합이었다 |

---

## 4-7. 4단계 시도 기록

| # | 시도한 것 | 결과 | 거기서 배운 것 |
|---|---|---|---|
| 1 | `cmd`/`command` 양쪽 `topic info -v` 비교 | 노드가 갈려 있음을 확인 | `Publisher count`/`Subscription count`만 봐도 "둘이 다른 토픽에 붙어 있다"를 알 수 있다 |
| 2 | 네 항목 전부 대조 | 불일치 2개 발견 | 하나를 찾았다고 멈추면 안 된다. |
| 3 | **TOPIC만 먼저 수정** | `Subscription count` 0->1, 그러나 **통과 안 됨** | 같은 토픽에 모였는데도 QoS 때문에 연결되지 않는 상태를 직접 관측 |
| 4 | RELIABILITY 추가 수정 | 통과 | 두 조건이 모두 충족돼야 매칭된다 |

---

---

## 3단계 Cyclone 설정 — 통과 (2026-11-05T23:00:05+09:00)

### 목표

주어진 요구사항대로 CycloneDDS XML 설정 파일을 작성하고 `check3`를 통과한다.

---

## 3-1. 요구사항 확보

```bash
ros2 run robit_blackbox check3 --name "김민찬"
```

```
[김민찬] 3단계 요구사항
  - 검사는 ROS_DOMAIN_ID=28 에서 실행된다 (도구가 알아서 설정)
  - Peers 에 127.0.0.1 이 있다
  - AllowMulticast 는 false 또는 spdp
  - MaxAutoParticipantIndex 는 6
  - Tracing 의 Verbosity 를 지정하고 OutputFile 은 /tmp/bb3_c03b8270.log

[NG] 설정 파일이 없습니다: /home/minchan/cyclonedds_bb.xml
```

### 요구사항 정리

| 항목 | 요구값 | XML 상 위치 |
|---|---|---|
| Peers | `127.0.0.1` 포함 | `Discovery` |
| AllowMulticast | `false` 또는 `spdp` | `General` |
| MaxAutoParticipantIndex | `6` | `Discovery` |
| Tracing Verbosity | 지정 (값 자유) | `Tracing` |
| Tracing OutputFile | `/tmp/bb3_c03b8270.log` | `Tracing` |

---

## 3-2. 작성한 XML (`~/cyclonedds_bb.xml`)

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config">
  <Domain Id="any">
    <General>
      <AllowMulticast>spdp</AllowMulticast>
    </General>
    <Discovery>
      <Peers>
        <Peer address="127.0.0.1"/>
      </Peers>
      <MaxAutoParticipantIndex>6</MaxAutoParticipantIndex>
    </Discovery>
    <Tracing>
      <Verbosity>config</Verbosity>
      <OutputFile>/tmp/bb3_c03b8270.log</OutputFile>
    </Tracing>
  </Domain>
</CycloneDDS>
```

### 값을 그렇게 고른 이유

- **`Domain Id="any"`** — 검사가 도메인 28에서 돌아가지만, `any`로 두면 도메인에 관계없이 설정이 적용된다.
  특정 번호를 박으면 다른 도메인에서는 설정이 무시된다.

- **`AllowMulticast`는 `spdp`** (`false`도 허용되지만 선택하지 않음)
  `spdp`는 발견(SPDP)에만 멀티캐스트를 쓰고 데이터는 유니캐스트로 보낸다.
  `false`는 멀티캐스트를 완전히 끄므로 Peers에 적힌 주소에만 전적으로 의존하게 된다.
  교재 4장이 "Wi-Fi처럼 멀티캐스트가 불안정한 구간은 spdp 또는 false + Peers"라고 한 조합 중
  발견 경로를 하나 더 남겨 두는 쪽을 택했다.

- **`MaxAutoParticipantIndex`의 위치는 `Discovery` 아래** — `ParticipantIndex`가 `auto`일 때
  0번부터 빈 번호를 찾는 그 **탐색의 상한**이다. `General`이 아니라 `Discovery`에 들어간다.

---

## 3-3. 검사 결과

```bash
ros2 run robit_blackbox check3 --name "김민찬"
```

```
[OK] XML 형식이 올바르다
[OK] AllowMulticast 가 false 또는 spdp (현재 spdp)
[OK] Peers 에 127.0.0.1 이 있다
[OK] MaxAutoParticipantIndex = 6 (현재 6)
[OK] Tracing OutputFile = /tmp/bb3_c03b8270.log
[OK] Tracing Verbosity 가 있다

Cyclone + 당신의 XML 로 talker/listener 를 최대 25초간 돌려 봅니다...
[OK] listener 가 talker 메시지를 받았다
[OK] Tracing 로그 파일이 생겼다

★ 3단계 통과! 기록되었습니다.
```

---

## 3-4. Tracing 로그에서 찾은 근거

```bash
ls -l /tmp/bb3_c03b8270.log
```
```
-rw-rw-r-- 1 minchan minchan 12858 11월  5 23:00 /tmp/bb3_c03b8270.log
```

```bash
head -60 /tmp/bb3_c03b8270.log
```

### 근거 1 — 내가 쓴 값이 그대로 반영됐다

```
1793887203.454853 [28]   listener: config: Domain/General/AllowMulticast/#text: spdp {2}
1793887203.454944 [28]   listener: config: Domain/Discovery/Peers/Peer[@Address]: 127.0.0.1 {2}
1793887203.454954 [28]   listener: config: Domain/Discovery/MaxAutoParticipantIndex/#text: 6 {0,2}
1793887203.455038 [28]     talker: config: Domain/Tracing/OutputFile/#text: /tmp/bb3_c03b8270.log {2}
1793887203.455032 [28]     talker: config: Domain/Tracing/Category/#text: fatal,error,warning,info,config {2}
```

XML에 적은 값이 **Cyclone 내부에서 실제로 읽힌 설정값으로 출력됐다.**
이것이 "적었다"와 "적용됐다"를 가르는 증거다.

`Verbosity: config`는 로그에서 `Tracing/Category`로 전개돼 있다


### 근거 2 — 도메인 28에서 돌았다

```
1793887203.454936 [28]   listener: config: Domain/Discovery/ExternalDomainId/#text: 28 {}
```

모든 로그 줄 앞의 `[28]`도 같은 사실을 가리킨다.
요구사항의 "검사는 ROS_DOMAIN_ID=28 에서 실행된다"가 실제로 지켜졌음을 확인할 수 있다.


---

## 3-6. 3단계 시도 기록

| # | 시도한 것 | 결과 | 거기서 배운 것 |
|---|---|---|---|
| 1 | XML 없이 `check3` 실행 | 요구사항 + `[NG] 설정 파일이 없습니다` | 검사 도구 자체가 요구사항 전달 수단이었다. 경로까지 지정돼 있었다 |
| 2 | `AllowMulticast`를 `false` 대신 `spdp`로 | 통과 | 둘 다 허용되지만 의미가 다르다. 발견 경로를 남기는 쪽을 선택 |

---

## 아직 이해하지 못한 것

- `topic info -v` 출력의 **History (Depth)가 `UNKNOWN`**으로 나오는 이유.
  교재에는 Depth가 QoS 정책의 하나로 나오는데, 왜 다른 항목과 달리 조회되지 않는지 모르겠다.
  rmw 구현체가 이 값을 노출하지 않는 것인지, CLI의 한계인지 확인이 필요하다.
- QoS 비호환이 발생했을 때 교재는 "incompatible QoS 경고가 노드 로그에 남는다"고 하는데,
  4-4의 상태에서 그 경고를 직접 확인하지 못했다.
  로봇 노드의 로그를 볼 수 없어서인지, `/rosout`을 구독해야 보이는 것인지 확인이 필요하다.

---
