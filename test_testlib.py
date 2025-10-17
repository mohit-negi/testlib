# test_testlib.py - Basic validation tests

import pytest
from unittest.mock import Mock, patch
from testlib import ResourceManager, RollbackError
from testlib.adapters import RESTAdapter

class MockRESTAdapter:
    """Mock adapter for testing without real HTTP calls"""
    def __init__(self):
        self.created_resources = {}
        self.id_counter = 1
    
    def create(self, resource_type: str, data: dict) -> str:
        resource_id = f"{resource_type}_{self.id_counter}"
        self.created_resources[resource_id] = {
            "id": resource_id,
            "type": resource_type,
            **data
        }
        self.id_counter += 1
        return resource_id
    
    def read(self, resource_type: str, resource_id: str) -> dict:
        if resource_id not in self.created_resources:
            raise ValueError(f"Resource {resource_id} not found")
        return self.created_resources[resource_id]
    
    def update(self, resource_type: str, resource_id: str, data: dict) -> dict:
        if resource_id not in self.created_resources:
            raise ValueError(f"Resource {resource_id} not found")
        self.created_resources[resource_id].update(data)
        return self.created_resources[resource_id]
    
    def delete(self, resource_type: str, resource_id: str) -> bool:
        if resource_id in self.created_resources:
            del self.created_resources[resource_id]
            return True
        return False

def test_resource_manager_basic_operations():
    """Test basic CRUD operations"""
    rm = ResourceManager()
    mock_adapter = MockRESTAdapter()
    rm.register_adapter("mock", mock_adapter)
    
    # Test create
    tenant_id = rm.create("tenant", {"name": "TestCorp"}, adapter_name="mock")
    assert tenant_id == "tenant_1"
    
    # Test read
    tenant = rm.read("tenant", tenant_id, adapter_name="mock")
    assert tenant["name"] == "TestCorp"
    
    # Test update
    rm.update("tenant", tenant_id, {"plan": "premium"}, adapter_name="mock")
    updated_tenant = rm.read("tenant", tenant_id, adapter_name="mock")
    assert updated_tenant["plan"] == "premium"
    
    # Test resource tracking
    resources = rm.get_resources("tenant")
    assert len(resources) == 1
    assert resources[0]["id"] == tenant_id

def test_rollback_functionality():
    """Test rollback cleans up resources in correct order"""
    rm = ResourceManager()
    mock_adapter = MockRESTAdapter()
    rm.register_adapter("mock", mock_adapter)
    
    # Create resources
    tenant_id = rm.create("tenant", {"name": "TestCorp"}, adapter_name="mock")
    user_id = rm.create("user", {"tenant_id": tenant_id}, adapter_name="mock")
    
    # Verify resources exist
    assert len(mock_adapter.created_resources) == 2
    
    # Rollback
    rm.rollback()
    
    # Verify resources are cleaned up
    assert len(mock_adapter.created_resources) == 0
    assert len(rm.get_resources()) == 0

def test_rollback_with_errors():
    """Test rollback handles errors gracefully"""
    rm = ResourceManager()
    
    # Create a mock adapter that fails on delete
    failing_adapter = Mock()
    failing_adapter.create.return_value = "test_id"
    failing_adapter.delete.side_effect = Exception("Delete failed")
    
    rm.register_adapter("failing", failing_adapter)
    
    # Create a resource
    rm.create("tenant", {"name": "Test"}, adapter_name="failing")
    
    # Rollback should raise RollbackError but continue trying
    with pytest.raises(RollbackError) as exc_info:
        rm.rollback()
    
    assert "Delete failed" in str(exc_info.value)

def test_adapter_registration():
    """Test adapter registration and usage"""
    rm = ResourceManager()
    
    # Test registering multiple adapters
    rest_adapter = MockRESTAdapter()
    ocpp_adapter = Mock()
    
    rm.register_adapter("rest", rest_adapter)
    rm.register_adapter("ocpp", ocpp_adapter)
    
    # Test using different adapters
    ocpp_adapter.create.return_value = "txn_123"
    
    tenant_id = rm.create("tenant", {"name": "Test"}, adapter_name="rest")
    txn_id = rm.create("transaction", {"charger_id": "chg1"}, adapter_name="ocpp")
    
    assert tenant_id == "tenant_1"
    assert txn_id == "txn_123"
    
    ocpp_adapter.create.assert_called_once_with("transaction", {"charger_id": "chg1"})

if __name__ == "__main__":
    print("Running basic testlib validation...")
    
    test_resource_manager_basic_operations()
    print("✅ Basic operations test passed")
    
    test_rollback_functionality()
    print("✅ Rollback test passed")
    
    test_adapter_registration()
    print("✅ Adapter registration test passed")
    
    print("\n🎉 All tests passed! TestLib is working correctly.")
    print("\nTo run with pytest: pytest test_testlib.py -v")