# example_unified_emulators.py - Unified emulator examples

import time
from testlib import ResourceManager
from testlib.adapters import RESTAdapter, EmulatorAdapter

def example_unified_python_emulators():
    """Example using unified Python-based emulators"""
    print("🐍 Unified Python Emulators Example")
    print("=" * 50)
    
    rm = ResourceManager()
    
    # Register adapters
    rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
    rm.register_adapter("emulator", EmulatorAdapter())
    
    try:
        # Create tenant via REST
        tenant_id = rm.create("tenant", {"name": "UnifiedTestCorp"})
        user_id = rm.create("user", {"tenant_id": tenant_id, "email": "unified@test.com"})
        
        print(f"✅ Created infrastructure: tenant={tenant_id}, user={user_id}")
        
        # Create Python-based inverter emulator
        inverter_id = rm.create("inverter_emulator", {
            "inverter_id": "PY_INV_001",
            "lat": 28.6139,  # Delhi coordinates
            "lon": 77.209,
            "timezone": "Asia/Kolkata",
            "fault_enabled": True,
            "mode": "inverter"
        }, adapter_name="emulator")
        
        print(f"✅ Created Python inverter emulator: {inverter_id}")
        
        # Create Python-based charger emulator
        charger_id = rm.create("charger_emulator", {
            "charger_id": "PY_CHG_001",
            "tenant_id": tenant_id,
            "model": "AC_22kW",
            "max_power": 22000,
            "connectors": 2
        }, adapter_name="emulator")
        
        print(f"✅ Created Python charger emulator: {charger_id}")
        
        # Let emulators initialize and start generating data
        print("⏳ Letting emulators initialize for 5 seconds...")
        time.sleep(5)
        
        # Start a charging transaction
        transaction_id = rm.create("transaction", {
            "emulator_id": charger_id,
            "connector_id": 1,
            "id_tag": "test_user_001"
        }, adapter_name="emulator")
        
        print(f"✅ Started charging transaction: {transaction_id}")
        
        # Let transaction run
        print("⏳ Letting transaction run for 15 seconds...")
        time.sleep(15)
        
        # Check emulator statuses
        inverter_status = rm.read("inverter_emulator", inverter_id, adapter_name="emulator")
        charger_status = rm.read("charger_emulator", charger_id, adapter_name="emulator")
        transaction_status = rm.read("transaction", transaction_id, adapter_name="emulator")
        
        print("📊 Emulator Statuses:")
        print(f"   Inverter: {inverter_status.get('status', 'unknown')}")
        print(f"   Charger: {charger_status.get('status', 'unknown')}")
        print(f"   Transaction: {transaction_status.get('status', 'unknown')}")
        
        # Show energy data if available
        if 'emulator_status' in inverter_status:
            energy = inverter_status['emulator_status'].get('energy_counters', {})
            print(f"   Daily Energy: {energy.get('daily', 0):.2f} kWh")
        
        if 'emulator_status' in charger_status:
            total_energy = charger_status['emulator_status'].get('total_energy_delivered', 0)
            print(f"   Charger Energy Delivered: {total_energy:.2f} kWh")
        
        # Stop transaction
        rm.delete("transaction", transaction_id, adapter_name="emulator")
        print("✅ Transaction stopped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        rm.rollback()
        print("🧹 Cleanup completed")

def example_mixed_emulator_environment():
    """Example mixing different emulator types"""
    print("\n🔄 Mixed Emulator Environment Example")
    print("=" * 50)
    
    rm = ResourceManager()
    
    # Register all adapters
    rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
    rm.register_adapter("emulator", EmulatorAdapter())
    
    try:
        # Create infrastructure
        tenant_id = rm.create("tenant", {"name": "MixedTestCorp"})
        user_id = rm.create("user", {"tenant_id": tenant_id, "email": "mixed@test.com"})
        
        # Create multiple emulator types
        emulators = []
        
        # Python inverter emulator (solar simulation)
        inv_emulator_id = rm.create("inverter_emulator", {
            "inverter_id": "SOLAR_INV_001",
            "lat": 28.6139,
            "lon": 77.209,
            "fault_enabled": True,
            "mode": "inverter"
        }, adapter_name="emulator")
        emulators.append(("Inverter", inv_emulator_id))
        
        # Python charger emulator (AC charging)
        ac_charger_id = rm.create("charger_emulator", {
            "charger_id": "AC_CHG_001", 
            "model": "AC_22kW",
            "max_power": 22000,
            "connectors": 2
        }, adapter_name="emulator")
        emulators.append(("AC Charger", ac_charger_id))
        
        # Another charger emulator (DC fast charging)
        dc_charger_id = rm.create("charger_emulator", {
            "charger_id": "DC_CHG_001",
            "model": "DC_150kW", 
            "max_power": 150000,
            "connectors": 1
        }, adapter_name="emulator")
        emulators.append(("DC Charger", dc_charger_id))
        
        print(f"✅ Created {len(emulators)} emulators:")
        for name, emu_id in emulators:
            print(f"   - {name}: {emu_id}")
        
        # Let all emulators start up
        print("⏳ Initializing emulators for 3 seconds...")
        time.sleep(3)
        
        # Start multiple transactions
        transactions = []
        
        # AC charging session
        ac_txn_id = rm.create("transaction", {
            "emulator_id": ac_charger_id,
            "connector_id": 1,
            "id_tag": "user_ac_001"
        }, adapter_name="emulator")
        transactions.append(("AC Transaction", ac_txn_id))
        
        # DC fast charging session
        dc_txn_id = rm.create("transaction", {
            "emulator_id": dc_charger_id,
            "connector_id": 1, 
            "id_tag": "user_dc_001"
        }, adapter_name="emulator")
        transactions.append(("DC Transaction", dc_txn_id))
        
        print(f"✅ Started {len(transactions)} transactions:")
        for name, txn_id in transactions:
            print(f"   - {name}: {txn_id}")
        
        # Monitor for a while
        print("⏳ Running mixed environment for 20 seconds...")
        for i in range(4):
            time.sleep(5)
            print(f"   ... {(i+1)*5} seconds elapsed")
        
        # Get final status of all emulators
        print("📊 Final Status Report:")
        
        emulator_adapter = rm._adapters["emulator"]
        active_emulators = emulator_adapter.get_active_emulators()
        
        print(f"   Active Emulators: {len(active_emulators)}")
        for emu_id, emu_info in active_emulators.items():
            emu_type = emu_info.get("type", "unknown")
            status = emu_info.get("status", "unknown")
            print(f"     - {emu_id}: {emu_type} ({status})")
        
        # Stop all transactions
        for name, txn_id in transactions:
            rm.delete("transaction", txn_id, adapter_name="emulator")
            print(f"✅ Stopped {name}")
        
    except Exception as e:
        print(f"❌ Error in mixed environment: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        rm.rollback()
        print("🧹 Mixed environment cleanup completed")

def example_emulator_speed_control():
    """Example showing emulator speed control"""
    print("\n⚡ Emulator Speed Control Example")
    print("=" * 50)
    
    rm = ResourceManager()
    rm.register_adapter("emulator", EmulatorAdapter())
    
    try:
        # Create a fast inverter emulator
        inverter_id = rm.create("inverter_emulator", {
            "inverter_id": "SPEED_INV_001",
            "lat": 28.6139,
            "lon": 77.209,
            "mode": "inverter"
        }, adapter_name="emulator")
        
        print(f"✅ Created speed-controlled inverter: {inverter_id}")
        
        # Let it run at normal speed
        print("⏳ Running at normal speed for 5 seconds...")
        time.sleep(5)
        
        # Speed up the emulator (2x speed)
        rm.update("inverter_emulator", inverter_id, {
            "tick_interval_ms": 500  # 500ms = 2x speed
        }, adapter_name="emulator")
        
        print("⚡ Increased speed to 2x for 5 seconds...")
        time.sleep(5)
        
        # Speed up even more (10x speed)
        rm.update("inverter_emulator", inverter_id, {
            "tick_interval_ms": 100  # 100ms = 10x speed
        }, adapter_name="emulator")
        
        print("🚀 Increased speed to 10x for 5 seconds...")
        time.sleep(5)
        
        # Check final status
        status = rm.read("inverter_emulator", inverter_id, adapter_name="emulator")
        if 'emulator_status' in status:
            energy = status['emulator_status'].get('energy_counters', {})
            print(f"📊 Final energy counters: {energy}")
        
    except Exception as e:
        print(f"❌ Speed control error: {e}")
    finally:
        rm.rollback()
        print("🧹 Speed control cleanup completed")

def example_locust_with_unified_emulators():
    """Example Locust integration with unified emulators"""
    print("\n🏋️ Locust Integration with Unified Emulators")
    print("=" * 50)
    
    # This would be used in a Locust file
    class UnifiedEmulatorLoadTestUser:
        def on_start(self):
            self.rm = ResourceManager()
            self.rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
            self.rm.register_adapter("emulator", EmulatorAdapter())
            
            # Create test infrastructure
            self.tenant_id = self.rm.create("tenant", {"name": f"LoadTest_{time.time()}"})
            self.user_id = self.rm.create("user", {"tenant_id": self.tenant_id})
            
            # Create emulated resources for load testing
            self.inverter_id = self.rm.create("inverter_emulator", {
                "inverter_id": f"LOAD_INV_{int(time.time())}",
                "mode": "inverter"
            }, adapter_name="emulator")
            
            self.charger_id = self.rm.create("charger_emulator", {
                "charger_id": f"LOAD_CHG_{int(time.time())}",
                "max_power": 22000
            }, adapter_name="emulator")
        
        def charging_task(self):
            # Start transaction
            txn_id = self.rm.create("transaction", {
                "emulator_id": self.charger_id,
                "connector_id": 1,
                "id_tag": f"user_{int(time.time())}"
            }, adapter_name="emulator")
            
            # Simulate charging time
            time.sleep(2)
            
            # Stop transaction
            self.rm.delete("transaction", txn_id, adapter_name="emulator")
        
        def monitoring_task(self):
            # Read emulator status
            inverter_status = self.rm.read("inverter_emulator", self.inverter_id, adapter_name="emulator")
            charger_status = self.rm.read("charger_emulator", self.charger_id, adapter_name="emulator")
            
            # Simulate monitoring delay
            time.sleep(1)
        
        def on_stop(self):
            self.rm.rollback()
    
    print("📝 Unified Locust class example created")
    print("   Features:")
    print("   - Single EmulatorAdapter for all emulator types")
    print("   - Python-based emulators (no external dependencies)")
    print("   - Unified transaction management")
    print("   - Automatic MQTT publishing")
    print("   - Speed control capabilities")

if __name__ == "__main__":
    print("🚀 TestLib Unified Emulator Examples")
    print("=" * 60)
    
    try:
        example_unified_python_emulators()
        example_mixed_emulator_environment()
        example_emulator_speed_control()
        example_locust_with_unified_emulators()
        
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Unified emulator examples completed!")
    print("💡 Benefits of unified approach:")
    print("   - Single adapter for all emulator types")
    print("   - Pure Python implementation (no JS dependencies)")
    print("   - Realistic emulation with proper physics")
    print("   - Speed control for time-compressed testing")
    print("   - Automatic MQTT integration")
    print("   - Consistent API across all emulator types")