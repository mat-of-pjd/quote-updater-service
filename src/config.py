from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DRIVER_NAME: str
    SERVER_NAME: str
    DATABASE_NAME: str

    poll_interval: int = 1
    checkpoint_file: str = "checkpoint.json"

    SENDER1: str
    SENDER_PASSWORD1: str

    SENDER2: str
    SENDER_PASSWORD2: str

    STATUS_TOKEN:str
    HEARTBEAT_IP:str

    class Config:
        env_file = ".env"


settings = Settings()


def get_connection_string() -> str:
    return (
        f"DRIVER={{{settings.DRIVER_NAME}}};"
        f"SERVER={settings.SERVER_NAME};"
        f"DATABASE={settings.DATABASE_NAME};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

def getEmailer():
    return settings.SENDER2

def getEmailerPassword():
    return settings.SENDER_PASSWORD2

def getStatusToken():
    return settings.STATUS_TOKEN

def getHeartbeatIP():
    return settings.HEARTBEAT_IP