# TestLib - Stateful Test Orchestration Library

A reusable library for managing test resources with automatic rollback, dependency tracking, and multi-protocol support.

## 🎯 Vision

Instead of hardcoding REST calls, simulators, and rollback logic directly into test frameworks, TestLib provides:

- **Decoupled concerns** - Separate resource management from test logic
- **Reusable state management** - Works with Locust, pytest, CLI, or any Python code
- **Protocol adapters** - REST, OCPP, MQTT support with extensible architecture
- **Intelligent rollback** - Dependency-aware cleanup in correct order
- **Auditable workflows** - Track all created resources and operations

## 🏗️ Architecture

```
testlib/
├── __init__.py              # Main exports
├── state_manager.py         # Core ResourceManager
├── exceptions.py            # Custom exceptions
└── adapters/
    ├── __init__.py
    ├── rest_adapter.py      # HTTP/REST CRUD operations
    ├── ocpp_adapter.py      # OCPP simulator integration
    └── mqtt_adapter.py      # MQTT pub/sub operations
```

## 🚀 Quick Start

### Basic Usage

```python
from testlib import ResourceManager
from testlib.adapters import RESTAdapter, OCPPAdapter

# Initialize
rm = ResourceManager()
rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
rm.register_adapter("ocpp", OCPPAdapter())

try:
    # Create resources (tracked automatically)
    tenant_id = rm.create("tenant", {"name": "TestCorp"})
    user_id = rm.create("user", {"tenant_id": tenant_id, "email": "test@example.com"})
    charger_id = rm.create("charger", {"tenant_id": tenant_id, "model": "AC01"})
    
    # Start OCPP transaction
    txn_id = rm.create("transaction", {
        "charger_id": charger_id,
        "user_id": user_id
    }, adapter_name="ocpp")
    
    # Verify creation
    tenant = rm.read("tenant", tenant_id)
    assert tenant["name"] == "TestCorp"
    
finally:
    # Automatic cleanup in dependency order
    rm.rollback()  # Deletes: transaction → charger → user → tenant
```

### Locust Integration

```python
from locust import HttpUser, task
from testlib import ResourceManager
from testlib.adapters import RESTAdapter, OCPPAdapter

class StatefulChargingUser(HttpUser):
    def on_start(self):
        self.rm = ResourceManager()
        self.rm.register_adapter("rest", RESTAdapter(self.host + "/api"))
        self.rm.register_adapter("ocpp", OCPPAdapter())
        
        # Setup test data
        self.tenant_id = self.rm.create("tenant", {"name": "LoadTestCorp"})
        self.user_id = self.rm.create("user", {"tenant_id": self.tenant_id})
        self.charger_id = self.rm.create("charger", {"tenant_id": self.tenant_id})

    @task
    def charging_session(self):
        # Start transaction
        txn_id = self.rm.create("transaction", {
            "charger_id": self.charger_id,
            "user_id": self.user_id
        }, adapter_name="ocpp")
        
        # Simulate charging
        time.sleep(2)
        
        # Stop transaction
        self.rm.delete("transaction", txn_id, adapter_name="ocpp")

    def on_stop(self):
        self.rm.rollback()
```

### Pytest Integration

```python
import pytest
from testlib import ResourceManager
from testlib.adapters import RESTAdapter

@pytest.fixture
def resource_manager():
    rm = ResourceManager()
    rm.register_adapter("rest", RESTAdapter("http://test-api:8000"))
    yield rm
    rm.rollback()  # Automatic cleanup

def test_charging_flow(resource_manager):
    rm = resource_manager
    
    tenant_id = rm.create("tenant", {"name": "PytestCorp"})
    charger_id = rm.create("charger", {"tenant_id": tenant_id})
    
    # Your test logic here
    assert rm.read("tenant", tenant_id)["name"] == "PytestCorp"
```

## 🔧 Adapters

### REST Adapter

Handles HTTP CRUD operations:

```python
from testlib.adapters import RESTAdapter

adapter = RESTAdapter("http://api.example.com")
# Automatically handles:
# POST /tenant (create)
# GET /tenant/{id} (read)  
# PUT /tenant/{id} (update)
# DELETE /tenant/{id} (delete)
```

### OCPP Adapter

Manages OCPP simulator connections:

```python
from testlib.adapters import OCPPAdapter

adapter = OCPPAdapter()
# Handles transaction lifecycle:
# create("transaction", data) -> start_transaction()
# delete("transaction", id) -> stop_transaction()
```

### MQTT Adapter

Publishes messages to MQTT broker:

```python
from testlib.adapters import MQTTAdapter

adapter = MQTTAdapter("mqtt.example.com")
# Publishes messages:
# create("message", {"topic": "test/topic", "payload": {...}})
```

## 🛡️ Error Handling

TestLib provides specific exceptions for different failure scenarios:

```python
from testlib import RollbackError, AdapterError, ResourceNotFoundError

try:
    rm.rollback()
except RollbackError as e:
    print(f"Some resources couldn't be cleaned up: {e}")
    # Handle partial rollback
```

## 🔍 Resource Tracking

Monitor and inspect created resources:

```python
# Get all tracked resources
all_resources = rm.get_resources()

# Get specific resource type
tenants = rm.get_resources("tenant")

# Clear tracking without deletion (use with caution)
rm.clear_resources()
```

## 🎛️ Advanced Features

### Custom Adapters

Create adapters for any protocol:

```python
class CustomAdapter:
    def create(self, resource_type: str, data: dict) -> str:
        # Your creation logic
        return resource_id
    
    def read(self, resource_type: str, resource_id: str) -> dict:
        # Your read logic
        return resource_data
    
    def update(self, resource_type: str, resource_id: str, data: dict):
        # Your update logic
        pass
    
    def delete(self, resource_type: str, resource_id: str) -> bool:
        # Your deletion logic
        return success

rm.register_adapter("custom", CustomAdapter())
```

### Dependency-Aware Rollback

Resources are deleted in reverse dependency order:

1. `transaction` (via OCPP)
2. `charger` (via REST)
3. `inverter` (via REST)  
4. `user` (via REST)
5. `tenant` (via REST)

This ensures referential integrity during cleanup.

## 📦 Installation

```bash
pip install -r requirements.txt
```

Optional dependencies:
- `locust>=2.0.0` for Locust integration
- `pytest>=7.0.0` for pytest fixtures
- `paho-mqtt>=1.6.0` for MQTT adapter

## 🧪 Testing

Run the validation tests:

```bash
python test_testlib.py
# or
pytest test_testlib.py -v
```

## 📋 Examples

See `example_usage.py` for complete examples of:
- Locust integration
- Pytest fixtures
- CLI usage
- Verification patterns

## 🤝 Contributing

TestLib is designed to be extensible. Add new adapters by implementing the four core methods: `create`, `read`, `update`, `delete`.

## 📄 License

MIT License - see LICENSE file for details.