import threading


class RetryWorker:
    """class for implementation of retry worker"""

    def __init__(self, hydroserver_publisher, pending_observation):
        self.database = pending_observation
        self.hydroserver_publisher = hydroserver_publisher
        self._thread = None

    def start(self):
        self._thread = threading.Thread(
            target=self.run,
            name="hydroserver-retry-worker",
            daemon=True,
        )
        self._thread.start()
