# ACI Health Check Tool

Cisco ACI Fabric 상태를 모니터링하는 Python 도구입니다.

## 기능

- Fault 요약 (심각도별 카운트)
- Critical/Major Fault 상세 출력
- 노드 상태 확인 (Spine, Leaf, APIC)

## 설치
```
pip install -r requirements.txt
```

## 사용법

1. `health_check.py`에서 APIC 정보 수정
2. 실행: `python health_check.py`

## 출력 예시
```
==================================================
ACI Health Check Report
==================================================

Total Faults: 27
  - Critical: 2
  - Major: 3
  - Minor: 1
  - Warning: 21
```

## 환경

- Python 3.12.2
- Cisco ACI APIC