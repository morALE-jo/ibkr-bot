from ib_insync import IB
from dotenv import load_dotenv
import os


class IBKRClient:
    def __init__(self):
        load_dotenv()

        self.host = os.getenv("IB_HOST", "127.0.0.1")
        self.port = int(os.getenv("IB_PORT", "7497"))
        self.client_id = int(os.getenv("IB_CLIENT_ID", "1"))

        self.ib = IB()

    def connect(self):
        self.ib.connect(self.host, self.port, clientId=self.client_id)
        return self.ib.isConnected()

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()

    def account_summary(self):
        return self.ib.accountSummary()
