from abc import ABC, abstractmethod


class Client(ABC):
    """
    Abstract client class that defines the core interface for client wrappers.
    Subclasses should provide implementations for connection handling and
    reference to an underlying client.
    """

    def __init__(self, **kwargs):
        """
        Initialize the client with an optional config dictionary. Additional keyword
        arguments may be captured for flexibility in subclassing.
        """
        self._config = (
            kwargs | self._config.dump()
            if hasattr(self, '_config')
            else kwargs
            )

    @property
    @abstractmethod
    def client(self):
        """
        Return the underlying client instance.
        Must be implemented by subclasses.
        """
        pass

    @property
    @abstractmethod
    def status(self):
        """
        Return the current connection status.
        Subclasses may override to provide more detailed information.
        """
        pass

    @property
    @abstractmethod
    def host(self):
        """
        Return the host address from the client configuration if provided.
        """
        pass

    @abstractmethod
    def connect(self):
        """
        Establish a connection to the underlying service.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Terminate the connection to the underlying service.
        Must be implemented by subclasses.
        """
        pass
