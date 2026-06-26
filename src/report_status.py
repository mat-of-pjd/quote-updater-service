import requests
from config import getStatusToken, getHeartbeatIP

def report_status(service_name, status="ok", message="", expected_interval="1m", tolerance=2.0):
    try:
        payload = {
        "token": getStatusToken(),
        "service": service_name,
        "status": status,
        "message": message,
        "expected_interval": expected_interval,
        "tolerance": tolerance
        }
        response = requests.post(getHeartbeatIP(), json=payload, timeout=2)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to report status for {service_name}: {e}")