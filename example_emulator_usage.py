# example_emulator_usage.py - Examples using real emulators

import time
from testlib import ResourceManager
from testlib.adapters import RESTAdapter, OCPPAdapter, MQTTEmulatorAdapter

def example_ocpp_emulator_integration():
    """Example using the real OCPP emulator"""
    print("🔌 OCPP Emulator Integration Example")
    print("=" * 50)
    
    rm = ResourceManager()
    
    # Register adapters
    rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
    rm.register_adapter("ocpp", OCPPAdapter())
    
    try:
        # Create tenant and user via REST
        tenant_id = rm.create("tenant", {"name": "OCPPTestCorp"})
        user_id = rm.create("user", {"tenant_id": tenant_id, "email": "ocpp@test.com"})
        
        # Create charger via OCPP (this will establish WebSocket connection)
        charger_id = rm.create("charger", {
            "charger_id": "ZTB00741001001I2500067",
            "tenant_id": tenant_id
        }, adapter_name="ocpp")
        
        print(f"✅ Created OCPP charger: {charger_id}")
        
        # Start a charging transaction
        txn_id = rm.create("transaction", {
            "charger_id": charger_id,
            "user_id": user_id,
            "id_tag": "5887d3"  # Using the default from your emulator
        }, adapter_name="ocpp")
        
        print(f"✅ Started transaction: {txn_id}")
        
        # Let it run for a bit
        print("⏳ Letting transaction run for 10 seconds...")
        time.sleep(10)
        
        # Read transaction status
        txn_status = rm.read("transaction", txn_id, adapter_name="ocpp")
        print(f"📊 Transaction status: {txn_status}")
        
        # Stop transaction
        rm.delete("transaction", txn_id, adapter_name="ocpp")
        print("✅ Transaction stopped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        rm.rollback()
        print("🧹 Cleanup completed")

def example_mqtt_emulator_integration():
    """Example using MQTT-based emulators"""
    print("\n📡 MQTT Emulator Integration Example")
    print("=" * 50)
    
    rm = ResourceManager()
    
    # Register adapters
    rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
    rm.register_adapter("mqtt_emulator", MQTTEmulatorAdapter())
    
    try:
        # Create tenant via REST
        tenant_id = rm.create("tenant", {"name": "MQTTTestCorp"})
        
        # Create inverter emulator
        inverter_emulator_id = rm.create("inverter_emulator", {
            "inverter_id": "INV001",
            "lat": 28.6139,  # Delhi coordinates
            "lon": 77.209,
            "timezone": "Asia/Kolkata",
            "fault_enabled": True,
            "mode": "inverter"
        }, adapter_name="mqtt_emulator")
        
        print(f"✅ Created inverter emulator: {inverter_emulator_id}")
        
        # Create charger emulator
        charger_emulator_id = rm.create("charger_emulator", {
            "charger_id": "CHG001",
            "tenant_id": tenant_id
        }, adapter_name="mqtt_emulator")
        
        print(f"✅ Created charger emulator: {charger_emulator_id}")
        
        # Read emulator status
        inverter_status = rm.read("inverter_emulator", inverter_emulator_id, adapter_name="mqtt_emulator")
        print(f"📊 Inverter emulator status: {inverter_status}")
        
        # Simulate some data publishing
        mqtt_adapter = rm._adapters["mqtt_emulator"]
        
        # Publish inverter data
        inverter_data = {
            "gridStatus": 1,
            "pvStatus": 1,
            "inverterOn": 1,
            "gridPower": 4500,
            "solarPower": 5000,
            "dailyEnergy": 25.5
        }
        
        success = mqtt_adapter.publish_message(
            inverter_emulator_id, 
            "InverterPeriodicData", 
            inverter_data
        )
        
        if success:
            print("✅ Published inverter data")
        else:
            print("❌ Failed to publish inverter data")
        
        # Let emulators run for a bit
        print("⏳ Letting emulators run for 5 seconds...")
        time.sleep(5)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        rm.rollback()
        print("🧹 Cleanup completed")

def example_combined_workflow():
    """Example combining REST, OCPP, and MQTT emulators"""
    print("\n🔄 Combined Workflow Example")
    print("=" * 50)
    
    rm = ResourceManager()
    
    # Register all adapters
    rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
    rm.register_adapter("ocpp", OCPPAdapter())
    rm.register_adapter("mqtt_emulator", MQTTEmulatorAdapter())
    
    try:
        # 1. Create infrastructure via REST
        tenant_id = rm.create("tenant", {"name": "CombinedTestCorp"})
        user_id = rm.create("user", {"tenant_id": tenant_id, "email": "combined@test.com"})
        
        # 2. Create physical charger via OCPP
        ocpp_charger_id = rm.create("charger", {
            "charger_id": "REAL_CHG_001",
            "tenant_id": tenant_id
        }, adapter_name="ocpp")
        
        # 3. Create emulated inverter via MQTT
        inverter_emulator_id = rm.create("inverter_emulator", {
            "inverter_id": "EMU_INV_001",
            "tenant_id": tenant_id,
            "mode": "inverter"
        }, adapter_name="mqtt_emulator")
        
        # 4. Create emulated charger via MQTT for comparison
        mqtt_charger_id = rm.create("charger_emulator", {
            "charger_id": "EMU_CHG_001",
            "tenant_id": tenant_id
        }, adapter_name="mqtt_emulator")
        
        print("✅ Created complete test environment:")
        print(f"   - Tenant: {tenant_id}")
        print(f"   - User: {user_id}")
        print(f"   - OCPP Charger: {ocpp_charger_id}")
        print(f"   - MQTT Inverter: {inverter_emulator_id}")
        print(f"   - MQTT Charger: {mqtt_charger_id}")
        
        # 5. Start a real charging session
        real_txn_id = rm.create("transaction", {
            "charger_id": ocpp_charger_id,
            "user_id": user_id
        }, adapter_name="ocpp")
        
        print(f"✅ Started real charging transaction: {real_txn_id}")
        
        # 6. Simulate emulated session
        emulated_session_id = rm.create("emulator_session", {
            "charger_id": mqtt_charger_id,
            "user_id": user_id,
            "session_type": "charging_simulation"
        }, adapter_name="mqtt_emulator")
        
        print(f"✅ Started emulated session: {emulated_session_id}")
        
        # 7. Let everything run
        print("⏳ Running combined workflow for 15 seconds...")
        time.sleep(15)
        
        # 8. Check status of all resources
        resources = rm.get_resources()
        print(f"📊 Total resources created: {sum(len(v) for v in resources.values())}")
        
        for resource_type, resource_list in resources.items():
            print(f"   - {resource_type}: {len(resource_list)} items")
        
    except Exception as e:
        print(f"❌ Error in combined workflow: {e}")
    finally:
        # Cleanup everything in correct order
        rm.rollback()
        print("🧹 Complete cleanup finished")

def example_locust_with_emulators():
    """Example Locust integration with emulators"""
    print("\n🏋️ Locust Integration with Emulators")
    print("=" * 50)
    
    # This would be used in a Locust file
    class EmulatorLoadTestUser:
        def on_start(self):
            self.rm = ResourceManager()
            self.rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
            self.rm.register_adapter("ocpp", OCPPAdapter())
            self.rm.register_adapter("mqtt_emulator", MQTTEmulatorAdapter())
            
            # Create test infrastructure
            self.tenant_id = self.rm.create("tenant", {"name": f"LoadTest_{time.time()}"})
            self.user_id = self.rm.create("user", {"tenant_id": self.tenant_id})
            
            # Create both real and emulated resources for load testing
            self.real_charger = self.rm.create("charger", {
                "charger_id": f"LOAD_CHG_{int(time.time())}",
                "tenant_id": self.tenant_id
            }, adapter_name="ocpp")
            
            self.emulated_inverter = self.rm.create("inverter_emulator", {
                "inverter_id": f"LOAD_INV_{int(time.time())}",
                "tenant_id": self.tenant_id
            }, adapter_name="mqtt_emulator")
        
        def charging_task(self):
            # Start real transaction
            txn_id = self.rm.create("transaction", {
                "charger_id": self.real_charger,
                "user_id": self.user_id
            }, adapter_name="ocpp")
            
            # Simulate charging time
            time.sleep(2)
            
            # Stop transaction
            self.rm.delete("transaction", txn_id, adapter_name="ocpp")
        
        def emulator_task(self):
            # Create emulated session
            session_id = self.rm.create("emulator_session", {
                "inverter_id": self.emulated_inverter,
                "data_type": "periodic_update"
            }, adapter_name="mqtt_emulator")
            
            # Simulate data collection
            time.sleep(1)
            
            # End session
            self.rm.delete("emulator_session", session_id, adapter_name="mqtt_emulator")
        
        def on_stop(self):
            self.rm.rollback()
    
    print("📝 Locust class example created (see code above)")
    print("   Use this pattern in your actual locustfile.py")

if __name__ == "__main__":
    print("🚀 TestLib Emulator Integration Examples")
    print("=" * 60)
    
    # Run examples (comment out as needed for testing)
    try:
        example_mqtt_emulator_integration()
        # example_ocpp_emulator_integration()  # Uncomment when OCPP server is available
        # example_combined_workflow()  # Uncomment for full integration test
        example_locust_with_emulators()
        
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
    
    print("\n✨ Examples completed!")
    print("💡 Tip: Modify the examples above to match your specific setup")