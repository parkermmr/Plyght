import time
import socket
from confluent_kafka import Consumer, Producer, KafkaException, KafkaError

from plyght.config.auto import get_kwargs
from plyght.config.clients.client import Client
from plyght.config.clients.exceptions import ConnectionException
from plyght.util.logging.logger import Logger, log_exceptions


class KafkaClient(Client):
    """
    Wrapper class for the Kafka Python client. Provides additional logging
    and exception handling and can be decorated for automatic configuration
    using Plyght's configuration system.

    For more information on Plyght configurations see:
        https://plyght.teampixl.info/config/intro,
        https://plyght.teampixl.info/config/clients/kafka
    """

    MODES: list[str] = ["produce", "consume"]

    def __init__(self, topics: str | list[str], **kwargs) -> None:
        """
        Initialize the KafkaClient, optionally with a uri and auth tuple.
        Other keyword arguments are merged with existing configuration if present.
        """
        super().__init__(**get_kwargs())
        self.logger = Logger(self.__class__.__name__)
        self._client = None
        self.topics = topics

    def allocate(self, mode: str) -> None:
        """
        Sets the connection mode for the client.
        """
        if mode not in self.MODES:
            raise Exception

        self.mode = mode

    @property
    @log_exceptions
    def client(self):
        """
        Declaritively returns the kafka client instance.
        """
        if not self._client:
            raise ConnectionException(
                404,
                "NoConnectionFound",
                "Connection to Kafka not yet established, try"
                " KafkaClient.connect().",
            )
        return self._client

    @property
    def status(self) -> bool:
        """
        Return a boolean based on the connection instantiation status of Kafka.
        I.e. if client is connected return True else False.

        @returns bool: Connection state.
        """
        if not self._client:
            self.logger.warning("No active connection to Kafka is established.")
            return False

        return True

    @property
    def host(self) -> str | None:
        """
        Return a string of URLs. E.g. "https://localhost:9092"

        @returns str: Gost URLs or None if no hosts are configured.
        """
        uri = self._config.get("uri", "")

        if not uri:
            self.logger.warning("No hosts found for Kafka client.")
            return None

        return uri

    @log_exceptions
    def connect(self) -> None:
        """
        Explicit connection method for Kafka rather than implicitly through the
        constructor itself.
        """
        if self._client is not None:
            return

        if not self.mode:
            raise RuntimeError(
                "Mode not set, use KafkaClient.allocate() to set kafka mode."
            )

        self.logger.info(f"Attempting to establish connection to clients: {self.host}")

        if self.mode == "produce":
            self._client = Producer(**self._config)
            health = self.health(self._client, self._delivery_report)
            if not health:
                raise ConnectionError(
                    503,
                    "Unhealthy",
                    "Cannot connect to producer at this stage."
                    " Caused by unreachable server."
                )

        if self.mode == "consume":
            self._client = Consumer(**self._config)
            self._client.subscribe(
                self.topics if isinstance(self.topics, list) else [self.topics]
            )
            try:
                _ = self._client.list_topics(timeout=5)
                return
            except KafkaException:
                raise ConnectionException(
                    503,
                    "ConnectionFailed",
                    "Connection to Kafka client cannot be established"
                    " caused by either an invalid configuration or unreachable host.",
                )

        instance = self._client
        if not instance:
            raise ConnectionException(
                500,
                "InvalidConfiguration",
                "Connection to Kafka client cannot be established"
                " caused by either an invalid configuration or unreachable host.",
            )

    def disconnect(self) -> None:
        """
        Terminate the connection to Kafka.
        """
        self._client = None

    def reconnect(self) -> None:
        """
        Restablishes connection to kafka client after an instance has been closed.
        """
        if self.mode == "consume":
            self._client = Consumer(**self._config)
            self._client.subscribe(
                self.topics if isinstance(self.topics, list) else [self.topics]
            )
            return

        self._client = Producer(**self._config)
        return

    @staticmethod
    def health(client: Producer, delivery_report: callable) -> bool:
        """
        Simple check to detect if a producer is connected and ready to produce
        to the kafka client.

        @param client (Producer): The confluent kafka producer to use.
        @param delivery_report(callable): The function to handle delivery results.
        @returns bool: True if client is healthy, False otherwise
        """
        try:
            client.produce(
                '__health__',
                key='status',
                value=f"health-check-{socket.gethostname()}-{int(time.time())}",
                callback=delivery_report
            )
            client.poll(0)
            client.flush(timeout=5)
            return True
        except KafkaException:
            return False

    @staticmethod
    def decode_header(headers: dict) -> dict:
        """
        Decodes a set of kafka headers into a dictionary.

        @param headers (dict): A bytes dictionary of kafka headers
        @returns dict: A simple dictionary of decoded string headers.
        """
        return {
            k: v.decode()
            if isinstance(v, bytes) else v
            for k, v in headers
        }

    def _delivery_report(self, err, msg) -> None:
        """
        Tests producer delivery and logs result to output.
        """
        if err is not None:
            self.delivery_failed = True
            self.logger.error(f"Delivery failed: {err}")
            return

        self.logger.info(
            f"Message delivered to {msg.topic()} [{msg.partition()}]"
            f" at offset {msg.offset()}"
        )

    def ping(self) -> None:
        """
        Attempts to ping kafka client. Client agnostic, works for producer and consumer.

        @raises RuntimeError: If no brokers are available or for generic exceptions.
        @raises ConnectionException: If self.connect() has not been called.
        """
        if not self.client:
            return

        try:
            metadata = self.client.list_topics(timeout=5.0)
            if not metadata.brokers:
                raise RuntimeError("No brokers available in metadata")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Kafka broker: {e}")

    def find(self, key, value, timeout_seconds=15, poll_timeout=1.0):
        """
        Finds a message in subscribed topics based on a key, value pair.
        """
        start_time = time.time()

        try:
            while True:
                if time.time() - start_time > timeout_seconds:
                    return None

                msg = self._client.poll(timeout=poll_timeout)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    raise KafkaException(msg.error())

                headers = msg.headers()
                if headers:
                    for k, v in headers:
                        if k == key and v.decode() == value:
                            return {
                                'topic': msg.topic(),
                                'key': msg.key(),
                                'value': msg.value(),
                                'headers': headers
                            }
        finally:
            self._client.close()
