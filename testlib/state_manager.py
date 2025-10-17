# testlib/state_manager.py
from typing import Dict, List, Any, Optional
from .exceptions import RollbackError

class ResourceManager:
    """
    Tracks created resources and enables safe rollback.
    Resources are stored as: {type: [{id, data, adapter_name}]}
    """
    def __init__(self):
        self._resources: Dict[str, List[Dict]] = {}
        self._adapters = {}

    def register_adapter(self, name: str, adapter):
        """Register an adapter (e.g., 'rest', 'ocpp')"""
        self._adapters[name] = adapter

    def create(self, resource_type: str, data: Dict, adapter_name: str = "rest") -> str:
        """Create resource via adapter, store for rollback"""
        adapter = self._adapters[adapter_name]
        resource_id = adapter.create(resource_type, data)
        if resource_type not in self._resources:
            self._resources[resource_type] = []
        self._resources[resource_type].append({
            "id": resource_id,
            "data": data,
            "adapter": adapter_name
        })
        return resource_id

    def read(self, resource_type: str, resource_id: str, adapter_name: str = "rest") -> Dict:
        adapter = self._adapters[adapter_name]
        return adapter.read(resource_type, resource_id)

    def update(self, resource_type: str, resource_id: str, data: Dict, adapter_name: str = "rest"):
        adapter = self._adapters[adapter_name]
        return adapter.update(resource_type, resource_id, data)

    def delete(self, resource_type: str, resource_id: str, adapter_name: str = "rest"):
        adapter = self._adapters[adapter_name]
        return adapter.delete(resource_type, resource_id)

    def rollback(self):
        """Rollback in reverse creation order (LIFO)"""
        deletion_order = [
            ("transaction", "emulator"),  # Unified emulator transactions
            ("transaction", "ocpp"),      # Legacy OCPP transactions
            ("emulator_session", "mqtt_emulator"),  # Legacy MQTT sessions
            ("ocpp_charger", "emulator"), # OCPP chargers via unified adapter
            ("charger_emulator", "emulator"),  # Python charger emulators
            ("charger_emulator", "mqtt_emulator"),  # Legacy MQTT chargers
            ("inverter_emulator", "emulator"),  # Python inverter emulators
            ("inverter_emulator", "mqtt_emulator"),  # Legacy MQTT inverters
            ("charger", "ocpp"),          # Legacy OCPP chargers
            ("charger", "rest"),          # REST API chargers
            ("inverter", "rest"),         # REST API inverters
            ("user", "rest"),
            ("tenant", "rest"),
        ]

        errors = []
        for res_type, adapter_name in deletion_order:
            if res_type in self._resources:
                for item in reversed(self._resources[res_type]):
                    try:
                        self.delete(res_type, item["id"], adapter_name)
                        # Remove from tracking after successful deletion
                        self._resources[res_type].remove(item)
                    except Exception as e:
                        errors.append(f"Failed to delete {res_type} {item['id']}: {e}")
        
        if errors:
            raise RollbackError("Rollback incomplete:\n" + "\n".join(errors))
        
        # Clear all resources if rollback was successful
        self._resources.clear()

    def get_resources(self, resource_type: Optional[str] = None) -> Dict:
        """Get tracked resources, optionally filtered by type"""
        if resource_type:
            return self._resources.get(resource_type, [])
        return self._resources.copy()

    def clear_resources(self):
        """Clear all tracked resources without deletion (use with caution)"""
        self._resources.clear()