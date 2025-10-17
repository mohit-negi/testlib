# testlib/adapters/mqtt_emulator_adapter.py
import json
import time
import subprocess
import threading
from typing import Dict, Optional, List
import uuid
from pathlib import Path

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Warning: paho-mqtt not available. Install with: pip install paho-mqtt")
    mqtt = None

class MQTTEmulatorAdapter:
    """
    Adapter for managing MQTT-based emulators (charger and inverter)
    Integrates with your existing JavaScript emulator implementations
    """
    
    def __init__(self, broker_host: str = "13.127.194.179", broker_port: int = 8000, 
                 username: str = "vikash", password: str = "password"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        
        self._client = None
        self._connected = False
        self._emulator_processes = {}  # Track running emulator processes
        self._emulator_sessions = {}   # Track emulator sessions
        self._message_handlers = {}    # Message handlers for different emulators
        
        # Topics for different emulators
        self.topics = {
            "charger_publish": "inverterData234",
            "charger_subscribe": "serverToInverter234",
            "inverter_publish": "inverterData",
            "inverter_subscribe": "serverToInverter"
        }
        
    def _ensure_connected(self):
        """Ensure MQTT client is connected"""
        if mqtt is None:
            raise RuntimeError("paho-mqtt not available")
            
        if self._client is None or not self._connected:
            self._client = mqtt.Client(f"testlib_adapter_{int(time.time())}")
            self._client.username_pw_set(self.username, self.password)
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    self._connected = True
                    print(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
                else:
                    print(f"Failed to connect to MQTT broker: {rc}")
            
            def on_message(client, userdata, msg):
                self._handle_message(msg.topic, msg.payload.decode())
            
            self._client.on_connect = on_connect
            self._client.on_message = on_message
            
            try:
                self._client.connect(self.broker_host, self.broker_port, 60)
                self._client.loop_start()
                
                # Wait for connection
                timeout = 10
                while not self._connected and timeout > 0:
                    time.sleep(0.1)
                    timeout -= 0.1
                    
                if not self._connected:
                    raise RuntimeError("Failed to connect to MQTT broker within timeout")
                    
            except Exception as e:
                raise RuntimeError(f"MQTT connection failed: {e}")
    
    def _handle_message(self, topic: str, payload: str):
        """Handle incoming MQTT messages"""
        try:
            data = json.loads(payload)
            # Route message to appropriate handler based on topic
            for emulator_id, handler in self._message_handlers.items():
                if handler and callable(handler):
                    handler(topic, data)
        except json.JSONDecodeError:
            print(f"Invalid JSON received on topic {topic}: {payload}")
        except Exception as e:
            print(f"Error handling message on topic {topic}: {e}")
    
    def create(self, resource_type: str, data: Dict) -> str:
        """Create/start an emulator resource"""
        if resource_type == "charger_emulator":
            return self._create_charger_emulator(data)
        elif resource_type == "inverter_emulator":
            return self._create_inverter_emulator(data)
        elif resource_type == "emulator_session":
            return self._create_emulator_session(data)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def _create_charger_emulator(self, data: Dict) -> str:
        """Start a charger MQTT emulator"""
        self._ensure_connected()
        
        charger_id = data.get("charger_id", f"CHG_{uuid.uuid4().hex[:8]}")
        emulator_id = f"charger_emulator_{charger_id}"
        
        # Subscribe to charger topics
        subscribe_topic = f"{self.topics['charger_subscribe']}/{charger_id}"
        self._client.subscribe(subscribe_topic)
        
        # Store emulator session info
        self._emulator_sessions[emulator_id] = {
            "type": "charger",
            "charger_id": charger_id,
            "status": "active",
            "publish_topic": f"{self.topics['charger_publish']}/{charger_id}",
            "subscribe_topic": subscribe_topic,
            "created_at": time.time()
        }
        
        # Set up message handler for this emulator
        def charger_message_handler(topic, message_data):
            if topic == subscribe_topic:
                print(f"Charger {charger_id} received: {message_data}")
        
        self._message_handlers[emulator_id] = charger_message_handler
        
        return emulator_id
    
    def _create_inverter_emulator(self, data: Dict) -> str:
        """Start an inverter MQTT emulator"""
        self._ensure_connected()
        
        inverter_id = data.get("inverter_id", f"INV_{uuid.uuid4().hex[:8]}")
        emulator_id = f"inverter_emulator_{inverter_id}"
        
        # Configuration for the inverter emulator
        config = {
            "inverterId": inverter_id,
            "lat": data.get("lat", 28.6139),  # Default to Delhi
            "lon": data.get("lon", 77.209),
            "timezone": data.get("timezone", "Asia/Kolkata"),
            "startTime": data.get("start_time", time.strftime("%Y-%m-%dT%H:%M:%S.000Z")),
            "faultEnabled": data.get("fault_enabled", True),
            "mode": data.get("mode", "inverter")  # 'inverter' or 'gridPower'
        }
        
        # Subscribe to inverter topics
        subscribe_topic = f"{self.topics['inverter_subscribe']}/{inverter_id}"
        self._client.subscribe(subscribe_topic)
        
        # Store emulator session info
        self._emulator_sessions[emulator_id] = {
            "type": "inverter",
            "inverter_id": inverter_id,
            "status": "active",
            "config": config,
            "publish_topic": f"{self.topics['inverter_publish']}/{inverter_id}",
            "subscribe_topic": subscribe_topic,
            "created_at": time.time()
        }
        
        # Set up message handler for this emulator
        def inverter_message_handler(topic, message_data):
            if topic == subscribe_topic:
                print(f"Inverter {inverter_id} received: {message_data}")
        
        self._message_handlers[emulator_id] = inverter_message_handler
        
        return emulator_id
    
    def _create_emulator_session(self, data: Dict) -> str:
        """Create a generic emulator session for testing"""
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        self._emulator_sessions[session_id] = {
            "type": "session",
            "session_id": session_id,
            "status": "active",
            "data": data,
            "created_at": time.time()
        }
        
        return session_id
    
    def read(self, resource_type: str, resource_id: str) -> Dict:
        """Read emulator status"""
        if resource_id in self._emulator_sessions:
            return self._emulator_sessions[resource_id]
        else:
            raise ValueError(f"Emulator {resource_id} not found")
    
    def update(self, resource_type: str, resource_id: str, data: Dict) -> Dict:
        """Update emulator configuration"""
        if resource_id in self._emulator_sessions:
            self._emulator_sessions[resource_id].update(data)
            return self._emulator_sessions[resource_id]
        else:
            raise ValueError(f"Emulator {resource_id} not found")
    
    def delete(self, resource_type: str, resource_id: str) -> bool:
        """Stop/delete an emulator"""
        if resource_id not in self._emulator_sessions:
            return False
        
        session = self._emulator_sessions[resource_id]
        
        # Unsubscribe from topics if applicable
        if "subscribe_topic" in session:
            try:
                self._client.unsubscribe(session["subscribe_topic"])
            except:
                pass
        
        # Remove message handler
        if resource_id in self._message_handlers:
            del self._message_handlers[resource_id]
        
        # Mark as stopped
        session["status"] = "stopped"
        session["stopped_at"] = time.time()
        
        # Remove from active sessions
        del self._emulator_sessions[resource_id]
        
        return True
    
    def publish_message(self, emulator_id: str, message_type: str, data: Dict) -> bool:
        """Publish a message from an emulator"""
        if emulator_id not in self._emulator_sessions:
            raise ValueError(f"Emulator {emulator_id} not found")
        
        session = self._emulator_sessions[emulator_id]
        if "publish_topic" not in session:
            raise ValueError(f"Emulator {emulator_id} has no publish topic")
        
        # Format message according to your protocol
        message = self._format_message(message_type, data)
        
        try:
            self._client.publish(session["publish_topic"], json.dumps(message))
            return True
        except Exception as e:
            print(f"Failed to publish message: {e}")
            return False
    
    def _format_message(self, message_type: str, data: Dict) -> List:
        """Format message according to your MQTT protocol"""
        message_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        # Add timestamp to data if not present
        if "timestamp" not in data:
            data["timestamp"] = timestamp
        
        # Format as [type, uuid, message_name, data]
        return [2, message_id, message_type, data]
    
    def get_active_emulators(self) -> Dict:
        """Get all active emulators"""
        return {k: v for k, v in self._emulator_sessions.items() if v["status"] == "active"}
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            print("Disconnected from MQTT broker")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.disconnect()