from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessageInfo


logger: logging.Logger = logging.getLogger(__name__)


class MqttPublisher:
    def __init__(self, client_id: str, host: str, port: int, user: str | None = None, password: str | None = None,
                 connect_timeout_seconds: float = 5.0) -> None:
        self._client_id = client_id
        self._client = mqtt.Client(client_id=client_id, clean_session=True)
        if user is not None:
            self._client.username_pw_set(user, password)
        self._host = host
        self._port = port
        self._keepalive = int(max(1.0, connect_timeout_seconds))

    def ensure_connected(self) -> None:
        if not self._client.is_connected():
            self._client.reinitialise(client_id=self._client_id, clean_session=True)
            self._client.connect(self._host, self._port, keepalive=self._keepalive)
            self._client.loop_start()

    def publish_json(self, topic: str, payload: dict[str, Any]) -> int:
        message: str = json.dumps(payload, separators=(",", ":"))
        self.ensure_connected()
        info: MQTTMessageInfo = self._client.publish(topic, payload=message, qos=1, retain=False)
        return int(getattr(info, "rc", mqtt.MQTT_ERR_SUCCESS))


