# testlib/adapters/mqtt_adapter.py
import json
import time
from typing import Dict, Optional
# import paho.mqtt.client as mqtt  # uncomment when paho-mqtt is installed

class MQTTAdapter:
    """
    MQTT adapter for publishing/subscribing to MQTT topics
    Useful for testing IoT device communications
    """
    def __init__(self, broker_host: str, broker_port: int = 1883, client_id: Optional[str] = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id or f"testlib_{int(time.time())}"
        self._client = None
        self._published_messages = []

    def _ensure_connected(self):
        """Ensure MQTT client is connected"""
        if self._client is None:
            # Uncomment when paho-mqtt is available
            # self._client = mqtt.Client(self.client_id)
            # self._client.connect(self.broker_host, self.broker_port, 60)
            # self._client.loop_start()
            pass

    def create(self, resource_type: str, data: Dict) -> str:
        """Publish a message = 'create' a message resource"""
        if resource_type != "message":
            raise ValueError("MQTT adapter only supports 'message' resource type")
        
        self._ensure_connected()
        
        topic = data.get("topic")
        payload = data.get("payload", {})
        
        if not topic:
            raise ValueError("MQTT message requires 'topic' in data")
        
        message_id = f"msg_{topic.replace('/', '_')}_{int(time.time())}"
        
        # Uncomment when paho-mqtt is available
        # self._client.publish(topic, json.dumps(payload))
        
        # Track published message for potential cleanup
        self._published_messages.append({
            "id": message_id,
            "topic": topic,
            "payload": payload
        })
        
        return message_id

    def delete(self, resource_type: str, resource_id: str) -> bool:
        """Remove message from tracking (MQTT messages can't be 'deleted' once sent)"""
        if resource_type != "message":
            return False
        
        self._published_messages = [
            msg for msg in self._published_messages 
            if msg["id"] != resource_id
        ]
        return True

    def read(self, resource_type: str, resource_id: str) -> Dict:
        """Get published message info"""
        if resource_type != "message":
            raise NotImplementedError("MQTT adapter only supports 'message' resource type")
        
        for msg in self._published_messages:
            if msg["id"] == resource_id:
                return msg
        
        raise ValueError(f"Message {resource_id} not found")

    def update(self, *args, **kwargs):
        raise NotImplementedError("MQTT messages cannot be updated once published")

    def disconnect(self):
        """Disconnect MQTT client"""
        if self._client:
            # self._client.loop_stop()
            # self._client.disconnect()
            self._client = None