# testlib/adapters/emulator_adapter.py
import time
import json
from typing import Dict, Optional, List
import uuid
import sys
import os

# Add emulators to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'emulators'))

try:
    from inverter_emulator import InverterEmulator
    from charger_emulator import ChargerEmulator, ChargerStatus, TransactionStatus
    from charger_ocpp import ChargePoint, var as ocpp_var
except ImportError as e:
    print(f"Warning: Emulator imports failed: {e}")
    InverterEmulator = None
    ChargerEmulator = None
    ChargePoint = None

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Warning: paho-mqtt not available. Install with: pip install paho-mqtt")
    mqtt = None

class EmulatorAdapter:
    """
    Unified adapter for all emulator types (OCPP, MQTT, Python-based)
    Provides a single interface for managing different emulator implementations
    """
    
    def __init__(self, config: Dict = None):
        self.config = {
            "mqtt_broker_host": "13.127.194.179",
            "mqtt_broker_port": 8000,
            "mqtt_username": "vikash", 
            "mqtt_password": "password",
            "ocpp_websocket_url": "ws://a285870195a5d4f9da391367ccd284a7-2128649528.ap-south-1.elb.amazonaws.com:8080",
            **(config or {})
        }
        
        self._emulators = {}  # Store running emulators
        self._mqtt_client = None
        self._mqtt_connected = False
        
        # MQTT topics
        self.mqtt_topics = {
            "charger_publish": "inverterData234",
            "charger_subscribe": "serverToInverter234", 
            "inverter_publish": "inverterData",
            "inverter_subscribe": "serverToInverter"
        }
    
    def _ensure_mqtt_connected(self):
        """Ensure MQTT client is connected"""
        if mqtt is None:
            raise RuntimeError("paho-mqtt not available")
            
        if self._mqtt_client is None or not self._mqtt_connected:
            self._mqtt_client = mqtt.Client(f"emulator_adapter_{int(time.time())}")
            self._mqtt_client.username_pw_set(
                self.config["mqtt_username"], 
                self.config["mqtt_password"]
            )
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    self._mqtt_connected = True
                    print(f"MQTT connected to {self.config['mqtt_broker_host']}:{self.config['mqtt_broker_port']}")
                else:
                    print(f"MQTT connection failed: {rc}")
            
            def on_message(client, userdata, msg):
                self._handle_mqtt_message(msg.topic, msg.payload.decode())
            
            self._mqtt_client.on_connect = on_connect
            self._mqtt_client.on_message = on_message
            
            try:
                self._mqtt_client.connect(
                    self.config["mqtt_broker_host"], 
                    self.config["mqtt_broker_port"], 
                    60
                )
                self._mqtt_client.loop_start()
                
                # Wait for connection
                timeout = 10
                while not self._mqtt_connected and timeout > 0:
                    time.sleep(0.1)
                    timeout -= 0.1
                    
                if not self._mqtt_connected:
                    raise RuntimeError("MQTT connection timeout")
                    
            except Exception as e:
                raise RuntimeError(f"MQTT connection failed: {e}")
    
    def _handle_mqtt_message(self, topic: str, payload: str):
        """Handle incoming MQTT messages"""
        try:
            data = json.loads(payload)
            print(f"MQTT message received on {topic}: {data}")
            # Route to appropriate emulator based on topic
        except json.JSONDecodeError:
            print(f"Invalid JSON on topic {topic}: {payload}")
        except Exception as e:
            print(f"Error handling MQTT message: {e}")
    
    def create(self, resource_type: str, data: Dict) -> str:
        """Create/start an emulator resource"""
        if resource_type == "inverter_emulator":
            return self._create_inverter_emulator(data)
        elif resource_type == "charger_emulator":
            return self._create_charger_emulator(data)
        elif resource_type == "ocpp_charger":
            return self._create_ocpp_charger(data)
        elif resource_type == "transaction":
            return self._create_transaction(data)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def _create_inverter_emulator(self, data: Dict) -> str:
        """Create a Python-based inverter emulator"""
        if InverterEmulator is None:
            raise RuntimeError("InverterEmulator not available")
        
        inverter_id = data.get("inverter_id", f"INV_{uuid.uuid4().hex[:8]}")
        emulator_id = f"inverter_emulator_{inverter_id}"
        
        # Setup MQTT publishing for this emulator
        self._ensure_mqtt_connected()
        
        def on_inverter_data(emulator_data):
            """Handle data from inverter emulator"""
            # Format and publish to MQTT
            mqtt_message = self._format_mqtt_message("InverterPeriodicData", emulator_data)
            topic = f"{self.mqtt_topics['inverter_publish']}/{inverter_id}"
            
            try:
                self._mqtt_client.publish(topic, json.dumps(mqtt_message))
                print(f"Published inverter data to {topic}")
            except Exception as e:
                print(f"Failed to publish inverter data: {e}")
        
        # Create and configure emulator
        emulator_options = {
            "inverter_id": inverter_id,
            "lat": data.get("lat", 28.6139),
            "lon": data.get("lon", 77.209),
            "timezone": data.get("timezone", "Asia/Kolkata"),
            "fault_enabled": data.get("fault_enabled", True),
            "mode": data.get("mode", "inverter"),
            "on_data": on_inverter_data,
            "logger": lambda msg: print(f"[{inverter_id}] {msg}")
        }
        
        emulator = InverterEmulator(emulator_options)
        emulator.start()
        
        # Store emulator
        self._emulators[emulator_id] = {
            "type": "inverter",
            "emulator": emulator,
            "inverter_id": inverter_id,
            "status": "running",
            "created_at": time.time()
        }
        
        print(f"Created inverter emulator: {emulator_id}")
        return emulator_id
    
    def _create_charger_emulator(self, data: Dict) -> str:
        """Create a Python-based charger emulator"""
        if ChargerEmulator is None:
            raise RuntimeError("ChargerEmulator not available")
        
        charger_id = data.get("charger_id", f"CHG_{uuid.uuid4().hex[:8]}")
        emulator_id = f"charger_emulator_{charger_id}"
        
        # Setup MQTT publishing for this emulator
        self._ensure_mqtt_connected()
        
        def on_charger_data(emulator_data):
            """Handle data from charger emulator"""
            # Format and publish to MQTT
            mqtt_message = self._format_mqtt_message(
                emulator_data.get("messageType", "ChargerPeriodicData"), 
                emulator_data
            )
            topic = f"{self.mqtt_topics['charger_publish']}/{charger_id}"
            
            try:
                self._mqtt_client.publish(topic, json.dumps(mqtt_message))
                print(f"Published charger data to {topic}")
            except Exception as e:
                print(f"Failed to publish charger data: {e}")
        
        def on_status_change(status):
            """Handle charger status changes"""
            print(f"Charger {charger_id} status: {status}")
        
        # Create and configure emulator
        emulator_options = {
            "charger_id": charger_id,
            "tenant_id": data.get("tenant_id", 1),
            "model": data.get("model", "AC_22kW"),
            "max_power": data.get("max_power", 22000),
            "connectors": data.get("connectors", 2),
            "on_data": on_charger_data,
            "on_status_change": on_status_change,
            "logger": lambda msg: print(f"[{charger_id}] {msg}")
        }
        
        emulator = ChargerEmulator(emulator_options)
        emulator.start()
        
        # Store emulator
        self._emulators[emulator_id] = {
            "type": "charger",
            "emulator": emulator,
            "charger_id": charger_id,
            "status": "running",
            "created_at": time.time()
        }
        
        print(f"Created charger emulator: {emulator_id}")
        return emulator_id
    
    def _create_ocpp_charger(self, data: Dict) -> str:
        """Create an OCPP-based charger (using your existing implementation)"""
        if ChargePoint is None:
            raise RuntimeError("OCPP ChargePoint not available")
        
        charger_id = data.get("charger_id", f"OCPP_{uuid.uuid4().hex[:8]}")
        emulator_id = f"ocpp_charger_{charger_id}"
        
        # Note: OCPP implementation would need async handling
        # This is a placeholder for the integration
        
        self._emulators[emulator_id] = {
            "type": "ocpp_charger",
            "charger_id": charger_id,
            "status": "created",
            "created_at": time.time()
        }
        
        print(f"Created OCPP charger: {emulator_id}")
        return emulator_id
    
    def _create_transaction(self, data: Dict) -> str:
        """Create a charging transaction"""
        emulator_id = data.get("emulator_id")
        connector_id = data.get("connector_id", 1)
        id_tag = data.get("id_tag", "default_user")
        
        if not emulator_id or emulator_id not in self._emulators:
            raise ValueError(f"Emulator {emulator_id} not found")
        
        emulator_info = self._emulators[emulator_id]
        
        if emulator_info["type"] == "charger":
            # Use Python charger emulator
            emulator = emulator_info["emulator"]
            transaction_id = emulator.start_transaction(connector_id, id_tag)
            
            # Store transaction reference
            txn_emulator_id = f"transaction_{transaction_id}"
            self._emulators[txn_emulator_id] = {
                "type": "transaction",
                "transaction_id": transaction_id,
                "emulator_id": emulator_id,
                "connector_id": connector_id,
                "status": "active",
                "created_at": time.time()
            }
            
            return txn_emulator_id
        
        elif emulator_info["type"] == "ocpp_charger":
            # Use OCPP charger (would need async implementation)
            transaction_id = f"ocpp_txn_{uuid.uuid4().hex[:8]}"
            
            txn_emulator_id = f"transaction_{transaction_id}"
            self._emulators[txn_emulator_id] = {
                "type": "ocpp_transaction",
                "transaction_id": transaction_id,
                "emulator_id": emulator_id,
                "status": "active",
                "created_at": time.time()
            }
            
            return txn_emulator_id
        
        else:
            raise ValueError(f"Cannot create transaction for emulator type: {emulator_info['type']}")
    
    def read(self, resource_type: str, resource_id: str) -> Dict:
        """Read emulator status"""
        if resource_id not in self._emulators:
            raise ValueError(f"Emulator {resource_id} not found")
        
        emulator_info = self._emulators[resource_id]
        
        if emulator_info["type"] in ["inverter", "charger"]:
            # Get status from Python emulator
            emulator = emulator_info["emulator"]
            status = emulator.get_status()
            return {**emulator_info, "emulator_status": status}
        
        elif emulator_info["type"] == "transaction":
            # Get transaction status
            parent_emulator_id = emulator_info["emulator_id"]
            if parent_emulator_id in self._emulators:
                parent_emulator = self._emulators[parent_emulator_id]["emulator"]
                if hasattr(parent_emulator, 'get_transaction'):
                    txn_status = parent_emulator.get_transaction(emulator_info["transaction_id"])
                    return {**emulator_info, "transaction_status": txn_status}
            
            return emulator_info
        
        else:
            return emulator_info
    
    def update(self, resource_type: str, resource_id: str, data: Dict) -> Dict:
        """Update emulator configuration"""
        if resource_id not in self._emulators:
            raise ValueError(f"Emulator {resource_id} not found")
        
        emulator_info = self._emulators[resource_id]
        
        # Update basic info
        emulator_info.update(data)
        
        # Apply updates to actual emulator if supported
        if emulator_info["type"] in ["inverter", "charger"]:
            emulator = emulator_info["emulator"]
            
            # Update tick interval if provided
            if "tick_interval_ms" in data and hasattr(emulator, 'update_tick_interval'):
                emulator.update_tick_interval(data["tick_interval_ms"])
        
        return emulator_info
    
    def delete(self, resource_type: str, resource_id: str) -> bool:
        """Stop/delete an emulator"""
        if resource_id not in self._emulators:
            return False
        
        emulator_info = self._emulators[resource_id]
        
        try:
            if emulator_info["type"] in ["inverter", "charger"]:
                # Stop Python emulator
                emulator = emulator_info["emulator"]
                emulator.stop()
            
            elif emulator_info["type"] == "transaction":
                # Stop transaction
                parent_emulator_id = emulator_info["emulator_id"]
                if parent_emulator_id in self._emulators:
                    parent_emulator = self._emulators[parent_emulator_id]["emulator"]
                    if hasattr(parent_emulator, 'stop_transaction'):
                        parent_emulator.stop_transaction(emulator_info["transaction_id"])
            
            # Remove from tracking
            del self._emulators[resource_id]
            print(f"Deleted emulator: {resource_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting emulator {resource_id}: {e}")
            return False
    
    def _format_mqtt_message(self, message_type: str, data: Dict) -> List:
        """Format message for MQTT protocol"""
        message_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = timestamp
        
        # Format as [type, uuid, message_name, data]
        return [2, message_id, message_type, data]
    
    def get_active_emulators(self) -> Dict:
        """Get all active emulators"""
        return {
            k: v for k, v in self._emulators.items() 
            if v.get("status") in ["running", "active"]
        }
    
    def disconnect(self):
        """Disconnect and cleanup"""
        # Stop all emulators
        for emulator_id in list(self._emulators.keys()):
            self.delete("emulator", emulator_id)
        
        # Disconnect MQTT
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._mqtt_connected = False
            print("Disconnected from MQTT broker")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.disconnect()