#!/usr/bin/env bash
# 사용법: ./run_all.sh <인터페이스> <reliable|best_effort>
# 주의: [W] 쪽 pong.py 를 같은 QoS 로 먼저 띄워 둘 것
set -u
IF="$1"; QOS="$2"
export ROS_DOMAIN_ID=5
mkdir -p evidence

run() {   # run <loss%> <tag>
  local L="$1" TAG="$2"
  if [ "$L" = "0" ]; then
    sudo tc qdisc del dev "$IF" root 2>/dev/null
  elif tc qdisc show dev "$IF" | grep -q netem; then
    sudo tc qdisc change dev "$IF" root netem loss "${L}%"
  else
    sudo tc qdisc add dev "$IF" root netem loss "${L}%"
  fi
  echo "=== $QOS / netem loss ${L}% ==="
  tc qdisc show dev "$IF" | tee "evidence/tc_${TAG}.txt"
  sleep 2
  python3 ping.py "$QOS" "$TAG" | tee "evidence/run_${QOS}_${TAG}.txt"
  sleep 2
}

sudo -v
run 0  loss0
run 1  loss1
run 5  loss5
run 10 loss10

sudo tc qdisc del dev "$IF" root 2>/dev/null
echo "=== netem 해제 ==="
tc qdisc show dev "$IF" | tee evidence/tc_removed.txt
