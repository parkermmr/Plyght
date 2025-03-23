from config.auto import get_kwargs
from config.clients.client import Client


class OpensearchClient(Client):

    def __init__(
            self,
            user: str = None,
            password: str = None,
            **kwargs
            ):
        super().__init__(**get_kwargs())
        self._client = None

    @property
    def client(self):
        return self._client

    @property
    def status(self):
        return True if self._client else False

    @property
    def host(self):
        """
        Return the first host in the config, if any.
        """
        if "hosts" in self._config and len(self._config["hosts"]) > 0:
            return self._config["hosts"][0]["host"]
        return None

    def connect(self):
        """
        In a real scenario, this is where you'd create an actual OpenSearch
        client object and store it in self._client.
        """
        self._client = f"Connected to {self.host}"

    def disconnect(self):
        """
        Terminate the connection to OpenSearch.
        """
        self._client = None
