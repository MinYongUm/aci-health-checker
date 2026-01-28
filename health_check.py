# ============================================
# ACI Health Check Tool
# 작성자: 엄민용
# 목적: ACI Fabric 상태 모니터링 및 Fault 조회
# ============================================

import requests
import sys
import yaml

# 한글 출력 깨짐 방지 (Windows 환경)
sys.stdout.reconfigure(encoding='utf-8')

# SSL 인증서 경고 메시지 비활성화
requests.packages.urllib3.disable_warnings()


# ============================================
# 설정 파일 로드
# ============================================
def load_config(config_path="config.yaml"):
    """
    config.yaml 파일에서 설정값 로드
    - APIC 주소, 계정 정보 등 민감한 정보 분리
    
    Args:
        config_path: 설정 파일 경로 (기본값: config.yaml)
    Returns:
        dict: 설정값 딕셔너리
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# ============================================
# 함수 정의
# ============================================

def login(session, config):
    """
    APIC 로그인 함수
    - ACI REST API는 세션 기반 인증 사용
    - aaaUser: ACI 인증 클래스 (고정값)
    - 로그인 성공 시 세션에 토큰 자동 저장됨
    
    Args:
        session: requests.Session 객체
        config: 설정값 딕셔너리
    Returns:
        bool: 로그인 성공 여부
    """
    apic = config["apic"]["host"]
    auth = {
        "aaaUser": {
            "attributes": {
                "name": config["apic"]["username"],
                "pwd": config["apic"]["password"]
            }
        }
    }
    resp = session.post(f"{apic}/api/aaaLogin.json", json=auth, verify=False)
    return resp.ok


def get_faults(session, config):
    """
    전체 Fault 목록 조회
    - faultInst: ACI Fault 클래스 (고정값)
    - 모든 Fault 정보를 JSON으로 반환
    
    Args:
        session: 로그인된 세션 객체
        config: 설정값 딕셔너리
    Returns:
        list: Fault 목록 (dict 배열)
    """
    apic = config["apic"]["host"]
    resp = session.get(f"{apic}/api/class/faultInst.json", verify=False)
    return resp.json()["imdata"]


def print_fault_summary(faults):
    """
    Fault 요약 리포트 출력
    - 심각도별 카운트 집계
    - Critical, Major는 상세 내용 출력
    
    Args:
        faults: get_faults()에서 반환된 Fault 목록
    """
    # 심각도별 카운트 초기화
    severity_count = {"critical": 0, "major": 0, "minor": 0, "warning": 0}
    
    # Fault 순회하며 심각도별 집계
    for fault in faults:
        sev = fault["faultInst"]["attributes"]["severity"]
        if sev in severity_count:
            severity_count[sev] += 1
    
    # 요약 출력
    print("=" * 50)
    print("ACI Health Check Report")
    print("=" * 50)
    print(f"\nTotal Faults: {len(faults)}")
    print(f"  - Critical: {severity_count['critical']}")
    print(f"  - Major: {severity_count['major']}")
    print(f"  - Minor: {severity_count['minor']}")
    print(f"  - Warning: {severity_count['warning']}")
    
    # Critical, Major만 필터링
    critical_major = [f for f in faults 
                      if f["faultInst"]["attributes"]["severity"] in ["critical", "major"]]
    
    # 상세 내용 출력
    if critical_major:
        print(f"\n[Critical & Major Faults]")
        print("-" * 50)
        for fault in critical_major:
            attr = fault["faultInst"]["attributes"]
            print(f"[{attr['severity'].upper()}] {attr['descr'][:70]}")


def get_node_status(session, config):
    """
    Fabric 노드 상태 조회
    - fabricNode: ACI 노드 클래스 (고정값)
    - Spine, Leaf: fabricSt 값으로 판단
    - Controller: 별도 API(infraWiNode)로 상태 확인
    
    Args:
        session: 로그인된 세션 객체
        config: 설정값 딕셔너리
    """
    apic = config["apic"]["host"]
    
    # Spine, Leaf 상태 조회
    resp = session.get(f"{apic}/api/class/fabricNode.json", verify=False)
    nodes = resp.json()["imdata"]
    
    # Controller 상태 조회 (별도 API)
    ctrl_resp = session.get(f"{apic}/api/class/infraWiNode.json", verify=False)
    controllers = ctrl_resp.json()["imdata"]
    
    # Controller 상태를 dict로 저장 (nodeName -> health)
    ctrl_status = {}
    for ctrl in controllers:
        attr = ctrl["infraWiNode"]["attributes"]
        ctrl_status[attr["nodeName"]] = attr["health"]
    
    print("\n[Node Status]")
    print("-" * 50)
    
    for node in nodes:
        attr = node["fabricNode"]["attributes"]
        name = attr["name"]
        role = attr["role"]
        
        if role == "controller":
            # Controller는 infraWiNode의 health 값 사용
            health = ctrl_status.get(name, "unknown")
            status = "OK" if health == "fully-fit" else health.upper()
        else:
            # Spine, Leaf는 fabricSt 값 사용
            status = "OK" if attr["fabricSt"] == "active" else "DOWN"
        
        print(f"{name:15} | {role:10} | {status}")


# ============================================
# 메인 실행부
# ============================================
if __name__ == "__main__":
    # 설정 파일 로드
    config = load_config()
    
    # 세션 생성 (쿠키, 인증 토큰 자동 관리)
    session = requests.Session()
    
    # 로그인 시도
    if login(session, config):
        print("Login Success\n")
        
        # 1. Fault 조회 및 요약 출력
        faults = get_faults(session, config)
        print_fault_summary(faults)
        
        # 2. 노드 상태 조회
        get_node_status(session, config)
    else:
        print("Login Failed")
