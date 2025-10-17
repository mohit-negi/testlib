# example_usage.py - Complete usage examples

import time
from testlib import ResourceManager
from testlib.adapters import RESTAdapter, OCPPAdapter
# from testlib.adapters.mqtt_adapter import MQTTAdapter

def example_locust_integration():
    """Example of how to use testlib in Locust"""
    from locust import HttpUser, task
    
    class StatefulChargingUser(HttpUser):
        def on_start(self):
            # Initialize state manager per user
            self.rm = ResourceManager()
            self.rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
            self.rm.register_adapter("ocpp", OCPPAdapter())
            
            # Create resources in dependency order
            self.tenant_id = self.rm.create("tenant", {"name": "TestCo"})
            self.user_id = self.rm.create("user", {
                "tenant_id": self.tenant_id, 
                "email": "test@example.com"
            })
            self.charger_id = self.rm.create("charger", {
                "tenant_id": self.tenant_id, 
                "model": "AC01"
            })
            
            # Verify creation with read-after-write
            tenant = self.rm.read("tenant", self.tenant_id)
            assert tenant["name"] == "TestCo"
            print(f"✅ Created tenant: {tenant}")

        @task
        def run_charging_session(self):
            # Start transaction via OCPP
            txn_id = self.rm.create("transaction", {
                "charger_id": self.charger_id,
                "user_id": self.user_id
            }, adapter_name="ocpp")
            
            # Simulate charging delay
            time.sleep(2)
            
            # Stop transaction
            self.rm.delete("transaction", txn_id, adapter_name="ocpp")
            print(f"✅ Completed charging session: {txn_id}")

        def on_stop(self):
            # Guaranteed cleanup
            try:
                self.rm.rollback()
                print("✅ Rollback completed successfully")
            except Exception as e:
                print(f"❌ Rollback failed: {e}")

def example_pytest_integration():
    """Example of how to use testlib in pytest"""
    import pytest
    
    @pytest.fixture
    def resource_manager():
        rm = ResourceManager()
        rm.register_adapter("rest", RESTAdapter("http://dev-api:8000"))
        rm.register_adapter("ocpp", OCPPAdapter())
        yield rm
        # Automatic cleanup after test
        rm.rollback()

    def test_charging_flow(resource_manager):
        rm = resource_manager
        
        # Create test data
        tenant_id = rm.create("tenant", {"name": "PytestCo"})
        user_id = rm.create("user", {"tenant_id": tenant_id, "email": "pytest@test.com"})
        charger_id = rm.create("charger", {"tenant_id": tenant_id, "model": "DC01"})
        
        # Test transaction flow
        txn_id = rm.create("transaction", {
            "charger_id": charger_id,
            "user_id": user_id
        }, adapter_name="ocpp")
        
        # Verify transaction was created
        assert txn_id.startswith("txn_")
        
        # Clean up transaction
        success = rm.delete("transaction", txn_id, adapter_name="ocpp")
        assert success
        
        print("✅ E2E charging flow test passed")

def example_cli_usage():
    """Example of standalone CLI usage"""
    rm = ResourceManager()
    rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
    
    try:
        # Create resources
        tenant_id = rm.create("tenant", {"name": "CLICorp"})
        print(f"Created tenant: {tenant_id}")
        
        # Read back
        tenant = rm.read("tenant", tenant_id)
        print(f"Tenant details: {tenant}")
        
        # Show tracked resources
        resources = rm.get_resources()
        print(f"Tracked resources: {resources}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Always clean up
        rm.rollback()
        print("Cleanup completed")

def example_with_verification():
    """Example showing verification patterns"""
    rm = ResourceManager()
    rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
    
    try:
        # Create with verification
        tenant_data = {"name": "VerifyCorp", "plan": "premium"}
        tenant_id = rm.create("tenant", tenant_data)
        
        # Read-after-write verification
        created_tenant = rm.read("tenant", tenant_id)
        assert created_tenant["name"] == tenant_data["name"]
        assert created_tenant["plan"] == tenant_data["plan"]
        print("✅ Create verification passed")
        
        # Update with verification
        update_data = {"plan": "enterprise"}
        rm.update("tenant", tenant_id, update_data)
        
        updated_tenant = rm.read("tenant", tenant_id)
        assert updated_tenant["plan"] == "enterprise"
        print("✅ Update verification passed")
        
    except Exception as e:
        print(f"Verification failed: {e}")
    finally:
        rm.rollback()

if __name__ == "__main__":
    print("🚀 TestLib Usage Examples")
    print("=" * 50)
    
    print("\n1. CLI Usage Example:")
    example_cli_usage()
    
    print("\n2. Verification Example:")
    example_with_verification()
    
    print("\n3. For Locust integration, see example_locust_integration()")
    print("4. For pytest integration, see example_pytest_integration()")