# example_complete_system.py - Complete TestLib System Example
"""
Comprehensive example covering:
- User authentication (register, login, tokens)
- REST API management (tenants, users, chargers)
- OCPP charger simulation
- MQTT inverter emulation
- Real charging transactions
- Complete cleanup and rollback
"""

import time
import random
from testlib import ResourceManager
from testlib.adapters import (
    RESTAdapter, 
    EmulatorAdapter, 
    OCPPAdapter,
    UserAuthResourceAdapter
)

class CompleteSystemTest:
    """
    Complete system test demonstrating all TestLib capabilities
    """
    
    def __init__(self, config: dict = None):
        self.config = {
            "rest_api_url": "http://localhost:8000",
            "ocpp_websocket_url": "ws://localhost:8080",
            "mqtt_broker_host": "localhost",
            "mqtt_broker_port": 1883,
            "test_duration": 60,  # seconds
            **(config or {})
        }
        
        self.rm = ResourceManager()
        self.setup_adapters()
        
        # Track created resources for reporting
        self.created_resources = {
            "tenants": [],
            "users": [],
            "chargers": [],
            "inverters": [],
            "transactions": []
        }
    
    def setup_adapters(self):
        """Setup all adapters for the test"""
        print("🔧 Setting up adapters...")
        
        # REST API adapter for backend services
        self.rm.register_adapter("rest", RESTAdapter(
            self.config["rest_api_url"],
            {
                "timeout": 30,
                "max_retries": 3,
                "auth_type": "bearer",
                "auth_token": "test-api-token"  # In real scenario, get from login
            }
        ))
        
        # User authentication adapter
        self.rm.register_adapter("auth", UserAuthResourceAdapter(
            self.config["rest_api_url"],
            {
                "register_endpoint": "/auth/register",
                "login_endpoint": "/auth/login",
                "user_endpoint": "/users"
            }
        ))
        
        # Unified emulator adapter (Python-based)
        self.rm.register_adapter("emulator", EmulatorAdapter({
            "mqtt_broker_host": self.config["mqtt_broker_host"],
            "mqtt_broker_port": self.config["mqtt_broker_port"]
        }))
        
        # OCPP adapter for real charger simulation
        self.rm.register_adapter("ocpp", OCPPAdapter(
            self.config["ocpp_websocket_url"]
        ))
        
        print("✅ All adapters configured")
    
    def create_test_infrastructure(self):
        """Create the basic infrastructure for testing"""
        print("\n🏗️ Creating test infrastructure...")
        
        # 1. Create tenant organization
        tenant_data = {
            "name": f"TestCorp_{int(time.time())}",
            "plan": "enterprise",
            "contact_email": "admin@testcorp.com",
            "address": "123 Test Street, Test City"
        }
        
        tenant_id = self.rm.create("tenant", tenant_data)
        self.created_resources["tenants"].append(tenant_id)
        print(f"✅ Created tenant: {tenant_id}")
        
        # 2. Create admin user with authentication
        admin_email = f"admin_{int(time.time())}@testcorp.com"
        admin_password = "SecurePassword123!"
        
        admin_user_id = self.rm.create("user", {
            "email": admin_email,
            "password": admin_password,
            "name": "Test Admin",
            "role": "admin",
            "tenant_id": tenant_id
        }, adapter_name="auth")
        
        self.created_resources["users"].append(admin_user_id)
        print(f"✅ Created admin user: {admin_user_id}")
        
        # 3. Login admin user to get tokens
        admin_session = self.rm.create("login_session", {
            "email": admin_email,
            "password": admin_password
        }, adapter_name="auth")
        print(f"✅ Admin logged in: {admin_session}")
        
        # 4. Create regular users
        for i in range(3):
            user_email = f"user_{i}_{int(time.time())}@testcorp.com"
            user_password = f"UserPass{i}23!"
            
            user_id = self.rm.create("user", {
                "email": user_email,
                "password": user_password,
                "name": f"Test User {i+1}",
                "role": "user",
                "tenant_id": tenant_id
            }, adapter_name="auth")
            
            self.created_resources["users"].append(user_id)
            print(f"✅ Created user {i+1}: {user_id}")
        
        return tenant_id, admin_user_id
    
    def create_charging_infrastructure(self, tenant_id: str):
        """Create chargers and inverters"""
        print("\n⚡ Creating charging infrastructure...")
        
        # 1. Create solar inverters (Python emulated)
        for i in range(2):
            inverter_id = self.rm.create("inverter_emulator", {
                "inverter_id": f"INV_{tenant_id}_{i+1}",
                "tenant_id": tenant_id,
                "lat": 28.6139 + (i * 0.01),  # Slightly different locations
                "lon": 77.209 + (i * 0.01),
                "timezone": "Asia/Kolkata",
                "fault_enabled": True,
                "mode": "inverter",
                "max_power": 5000  # 5kW
            }, adapter_name="emulator")
            
            self.created_resources["inverters"].append(inverter_id)
            print(f"✅ Created solar inverter {i+1}: {inverter_id}")
        
        # 2. Create AC chargers (Python emulated)
        for i in range(2):
            charger_id = self.rm.create("charger_emulator", {
                "charger_id": f"AC_CHG_{tenant_id}_{i+1}",
                "tenant_id": tenant_id,
                "model": "AC_22kW",
                "max_power": 22000,  # 22kW
                "connectors": 2,
                "location": f"Parking Spot {i+1}"
            }, adapter_name="emulator")
            
            self.created_resources["chargers"].append(charger_id)
            print(f"✅ Created AC charger {i+1}: {charger_id}")
        
        # 3. Create DC fast charger (Python emulated)
        dc_charger_id = self.rm.create("charger_emulator", {
            "charger_id": f"DC_CHG_{tenant_id}_FAST",
            "tenant_id": tenant_id,
            "model": "DC_150kW",
            "max_power": 150000,  # 150kW
            "connectors": 1,
            "location": "Fast Charging Bay"
        }, adapter_name="emulator")
        
        self.created_resources["chargers"].append(dc_charger_id)
        print(f"✅ Created DC fast charger: {dc_charger_id}")
        
        # 4. Create OCPP charger (real protocol simulation)
        try:
            ocpp_charger_id = self.rm.create("charger", {
                "charger_id": f"OCPP_CHG_{tenant_id}",
                "tenant_id": tenant_id,
                "model": "OCPP_AC_11kW"
            }, adapter_name="ocpp")
            
            self.created_resources["chargers"].append(ocpp_charger_id)
            print(f"✅ Created OCPP charger: {ocpp_charger_id}")
        except Exception as e:
            print(f"⚠️  OCPP charger creation failed (server may be down): {e}")
        
        return self.created_resources["chargers"]
    
    def run_charging_scenarios(self, user_ids: list, charger_ids: list):
        """Run various charging scenarios"""
        print(f"\n🔋 Running charging scenarios for {len(user_ids)} users...")
        
        active_transactions = []
        
        # Scenario 1: Quick AC charging sessions
        for i, user_id in enumerate(user_ids[:2]):  # First 2 users
            if i < len(charger_ids):
                charger_id = charger_ids[i]
                
                try:
                    txn_id = self.rm.create("transaction", {
                        "emulator_id": charger_id,
                        "connector_id": 1,
                        "id_tag": f"user_card_{user_id}",
                        "user_id": user_id
                    }, adapter_name="emulator")
                    
                    active_transactions.append((txn_id, charger_id, "AC"))
                    self.created_resources["transactions"].append(txn_id)
                    print(f"✅ Started AC charging: User {i+1} on {charger_id}")
                    
                except Exception as e:
                    print(f"❌ Failed to start AC charging for user {i+1}: {e}")
        
        # Scenario 2: DC fast charging
        if len(user_ids) > 2 and len(charger_ids) > 2:
            dc_charger = charger_ids[2]  # DC charger
            user_id = user_ids[2]
            
            try:
                txn_id = self.rm.create("transaction", {
                    "emulator_id": dc_charger,
                    "connector_id": 1,
                    "id_tag": f"user_card_{user_id}",
                    "user_id": user_id
                }, adapter_name="emulator")
                
                active_transactions.append((txn_id, dc_charger, "DC"))
                self.created_resources["transactions"].append(txn_id)
                print(f"✅ Started DC fast charging: User 3 on {dc_charger}")
                
            except Exception as e:
                print(f"❌ Failed to start DC charging: {e}")
        
        # Scenario 3: OCPP charging (if available)
        ocpp_chargers = [c for c in charger_ids if "OCPP" in c]
        if ocpp_chargers and len(user_ids) > 0:
            try:
                ocpp_txn_id = self.rm.create("transaction", {
                    "charger_id": ocpp_chargers[0],
                    "user_id": user_ids[0],
                    "id_tag": "ocpp_test_card"
                }, adapter_name="ocpp")
                
                active_transactions.append((ocpp_txn_id, ocpp_chargers[0], "OCPP"))
                self.created_resources["transactions"].append(ocpp_txn_id)
                print(f"✅ Started OCPP charging: {ocpp_txn_id}")
                
            except Exception as e:
                print(f"❌ Failed to start OCPP charging: {e}")
        
        return active_transactions
    
    def monitor_system(self, duration: int, active_transactions: list):
        """Monitor the system during operation"""
        print(f"\n📊 Monitoring system for {duration} seconds...")
        
        start_time = time.time()
        monitoring_interval = 10  # seconds
        
        while time.time() - start_time < duration:
            elapsed = int(time.time() - start_time)
            print(f"\n⏱️  System Status at {elapsed}s:")
            
            # Check emulator statuses
            try:
                emulator_adapter = self.rm._adapters["emulator"]
                active_emulators = emulator_adapter.get_active_emulators()
                
                print(f"   🔌 Active Emulators: {len(active_emulators)}")
                
                for emu_id, emu_info in active_emulators.items():
                    emu_type = emu_info.get("type", "unknown")
                    status = emu_info.get("status", "unknown")
                    print(f"     - {emu_id}: {emu_type} ({status})")
                
            except Exception as e:
                print(f"   ⚠️  Emulator status check failed: {e}")
            
            # Check authentication status
            try:
                auth_status = self.rm.read("auth_status", "current", adapter_name="auth")
                print(f"   🔐 Auth Status: logged_in={auth_status.get('logged_in', False)}")
                
            except Exception as e:
                print(f"   ⚠️  Auth status check failed: {e}")
            
            # Show transaction summary
            print(f"   ⚡ Active Transactions: {len(active_transactions)}")
            for txn_id, charger_id, txn_type in active_transactions:
                print(f"     - {txn_id}: {txn_type} on {charger_id}")
            
            # Random events simulation
            if random.random() < 0.3:  # 30% chance
                event_type = random.choice(["user_update", "charger_status", "energy_report"])
                
                if event_type == "user_update" and self.created_resources["users"]:
                    user_id = random.choice(self.created_resources["users"])
                    try:
                        self.rm.update("user", user_id, {
                            "last_activity": time.time()
                        }, adapter_name="auth")
                        print(f"   📝 Updated user activity: {user_id}")
                    except:
                        pass
                
                elif event_type == "energy_report":
                    print(f"   ⚡ Energy Report: Solar generation active, {len(active_transactions)} vehicles charging")
            
            time.sleep(monitoring_interval)
        
        print(f"\n✅ Monitoring completed after {duration} seconds")
    
    def stop_charging_sessions(self, active_transactions: list):
        """Stop all active charging sessions"""
        print(f"\n🛑 Stopping {len(active_transactions)} charging sessions...")
        
        for txn_id, charger_id, txn_type in active_transactions:
            try:
                if txn_type == "OCPP":
                    success = self.rm.delete("transaction", txn_id, adapter_name="ocpp")
                else:
                    success = self.rm.delete("transaction", txn_id, adapter_name="emulator")
                
                if success:
                    print(f"✅ Stopped {txn_type} transaction: {txn_id}")
                else:
                    print(f"⚠️  Failed to stop transaction: {txn_id}")
                    
            except Exception as e:
                print(f"❌ Error stopping transaction {txn_id}: {e}")
        
        print("✅ All charging sessions stopped")
    
    def generate_system_report(self):
        """Generate final system report"""
        print("\n📋 System Test Report")
        print("=" * 50)
        
        total_resources = sum(len(resources) for resources in self.created_resources.values())
        
        print(f"📊 Resources Created:")
        print(f"   - Tenants: {len(self.created_resources['tenants'])}")
        print(f"   - Users: {len(self.created_resources['users'])}")
        print(f"   - Chargers: {len(self.created_resources['chargers'])}")
        print(f"   - Inverters: {len(self.created_resources['inverters'])}")
        print(f"   - Transactions: {len(self.created_resources['transactions'])}")
        print(f"   - Total: {total_resources}")
        
        # Check final adapter states
        print(f"\n🔧 Adapter Status:")
        for adapter_name, adapter in self.rm._adapters.items():
            try:
                if hasattr(adapter, 'get_active_emulators'):
                    active = len(adapter.get_active_emulators())
                    print(f"   - {adapter_name}: {active} active emulators")
                elif hasattr(adapter, 'get_auth_status'):
                    status = adapter.auth_adapter.get_auth_status()
                    print(f"   - {adapter_name}: logged_in={status.get('logged_in', False)}")
                else:
                    print(f"   - {adapter_name}: configured")
            except:
                print(f"   - {adapter_name}: error checking status")
        
        print(f"\n✅ Test completed successfully!")
        print(f"💡 All resources will be cleaned up automatically")
    
    def run_complete_test(self):
        """Run the complete system test"""
        print("🚀 Starting Complete TestLib System Test")
        print("=" * 60)
        
        try:
            # Phase 1: Infrastructure
            tenant_id, admin_user_id = self.create_test_infrastructure()
            
            # Phase 2: Charging Infrastructure  
            charger_ids = self.create_charging_infrastructure(tenant_id)
            
            # Phase 3: Start Charging
            user_ids = self.created_resources["users"]
            active_transactions = self.run_charging_scenarios(user_ids, charger_ids)
            
            # Phase 4: Monitor System
            self.monitor_system(self.config["test_duration"], active_transactions)
            
            # Phase 5: Stop Charging
            self.stop_charging_sessions(active_transactions)
            
            # Phase 6: Generate Report
            self.generate_system_report()
            
        except KeyboardInterrupt:
            print("\n⏹️  Test interrupted by user")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Phase 7: Cleanup
            print(f"\n🧹 Cleaning up all resources...")
            self.rm.rollback()
            print("✅ Cleanup completed")

def run_load_test_simulation():
    """Simulate a load test scenario"""
    print("\n🏋️ Load Test Simulation")
    print("=" * 40)
    
    # Simulate multiple concurrent users
    test_instances = []
    
    for i in range(3):  # 3 concurrent test instances
        config = {
            "rest_api_url": "http://localhost:8000",
            "test_duration": 30,  # Shorter for demo
        }
        
        test_instance = CompleteSystemTest(config)
        test_instances.append(test_instance)
        
        print(f"🔄 Starting test instance {i+1}...")
        
        # In real load testing, these would run in parallel
        # For demo, we'll run them sequentially with shorter duration
        try:
            tenant_id, admin_id = test_instance.create_test_infrastructure()
            charger_ids = test_instance.create_charging_infrastructure(tenant_id)
            
            # Quick charging session
            if test_instance.created_resources["users"] and charger_ids:
                txn_id = test_instance.rm.create("transaction", {
                    "emulator_id": charger_ids[0],
                    "connector_id": 1,
                    "id_tag": f"load_test_{i}"
                }, adapter_name="emulator")
                
                print(f"✅ Instance {i+1}: Started charging session")
                
                # Brief monitoring
                time.sleep(5)
                
                # Stop session
                test_instance.rm.delete("transaction", txn_id, adapter_name="emulator")
                print(f"✅ Instance {i+1}: Stopped charging session")
            
        except Exception as e:
            print(f"❌ Instance {i+1} failed: {e}")
        finally:
            test_instance.rm.rollback()
            print(f"🧹 Instance {i+1}: Cleaned up")
    
    print("✅ Load test simulation completed")

if __name__ == "__main__":
    print("🚀 TestLib Complete System Example")
    print("=" * 60)
    print("This example demonstrates:")
    print("- User authentication (register, login, tokens)")
    print("- REST API management (tenants, users)")
    print("- Python emulator integration (chargers, inverters)")
    print("- OCPP protocol simulation")
    print("- MQTT data publishing")
    print("- Real charging transactions")
    print("- System monitoring")
    print("- Complete cleanup and rollback")
    print("=" * 60)
    
    # Configuration for your environment
    config = {
        "rest_api_url": "http://localhost:8000",
        "ocpp_websocket_url": "ws://localhost:8080", 
        "mqtt_broker_host": "localhost",
        "mqtt_broker_port": 1883,
        "test_duration": 60  # Run for 1 minute
    }
    
    try:
        # Run main system test
        system_test = CompleteSystemTest(config)
        system_test.run_complete_test()
        
        # Run load test simulation
        run_load_test_simulation()
        
    except KeyboardInterrupt:
        print("\n⏹️  Complete system test interrupted")
    except Exception as e:
        print(f"\n❌ Complete system test failed: {e}")
    
    print("\n🎉 Complete system example finished!")
    print("\n💡 To customize for your environment:")
    print("   1. Update API URLs in config")
    print("   2. Adjust endpoint paths in adapters")
    print("   3. Modify authentication flow as needed")
    print("   4. Add your specific business logic")
    print("\n🔧 For production use:")
    print("   - Add proper error handling")
    print("   - Implement retry logic")
    print("   - Add metrics and logging")
    print("   - Use environment variables for config")