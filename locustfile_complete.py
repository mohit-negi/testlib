# locustfile_complete.py - Complete Locust Integration
"""
Production-ready Locust file demonstrating all TestLib capabilities:
- User authentication workflows
- Charging session simulation
- Emulator management
- Real-world load patterns
- Comprehensive error handling
"""

import time
import random
from locust import HttpUser, task, between, events
from testlib import ResourceManager
from testlib.adapters import (
    RESTAdapter,
    EmulatorAdapter, 
    UserAuthResourceAdapter
)

class ChargingStationUser(HttpUser):
    """
    Simulates a user of an EV charging network
    """
    wait_time = between(5, 15)  # Wait 5-15 seconds between tasks
    
    def on_start(self):
        """Setup user session"""
        self.setup_resource_manager()
        self.create_user_account()
        self.setup_charging_infrastructure()
    
    def setup_resource_manager(self):
        """Initialize ResourceManager with all adapters"""
        self.rm = ResourceManager()
        
        # REST API for backend services
        self.rm.register_adapter("rest", RESTAdapter(
            self.host,
            {
                "timeout": 30,
                "max_retries": 2,
                "endpoints": {
                    "tenant": "/api/v1/tenants",
                    "user": "/api/v1/users",
                    "charger": "/api/v1/chargers",
                    "transaction": "/api/v1/transactions"
                }
            }
        ))
        
        # User authentication
        self.rm.register_adapter("auth", UserAuthResourceAdapter(
            self.host,
            {
                "register_endpoint": "/auth/register",
                "login_endpoint": "/auth/login",
                "user_endpoint": "/api/v1/users"
            }
        ))
        
        # Emulator for realistic charging simulation
        self.rm.register_adapter("emulator", EmulatorAdapter({
            "mqtt_broker_host": "localhost",
            "mqtt_broker_port": 1883
        }))
    
    def create_user_account(self):
        """Create unique user account for this test instance"""
        # Generate unique credentials
        user_number = random.randint(10000, 99999)
        self.user_email = f"loadtest_{user_number}@example.com"
        self.user_password = f"LoadTest{user_number}!"
        
        try:
            # Register user
            self.user_id = self.rm.create("user", {
                "email": self.user_email,
                "password": self.user_password,
                "name": f"Load Test User {user_number}",
                "phone": f"+1555{user_number}",
                "role": "customer"
            }, adapter_name="auth")
            
            print(f"✅ Created user: {self.user_email}")
            
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            self.user_id = None
    
    def setup_charging_infrastructure(self):
        """Setup emulated chargers for this user"""
        if not self.user_id:
            return
        
        try:
            # Create a personal AC charger emulator
            self.ac_charger_id = self.rm.create("charger_emulator", {
                "charger_id": f"AC_CHG_{self.user_id}",
                "model": "AC_22kW",
                "max_power": 22000,
                "connectors": 2,
                "location": f"User {self.user_id} Home"
            }, adapter_name="emulator")
            
            # Create a DC fast charger (shared simulation)
            self.dc_charger_id = self.rm.create("charger_emulator", {
                "charger_id": f"DC_CHG_SHARED_{random.randint(1, 5)}",
                "model": "DC_150kW", 
                "max_power": 150000,
                "connectors": 1,
                "location": "Highway Fast Charging"
            }, adapter_name="emulator")
            
            print(f"✅ Setup charging infrastructure for user {self.user_id}")
            
        except Exception as e:
            print(f"❌ Failed to setup infrastructure: {e}")
            self.ac_charger_id = None
            self.dc_charger_id = None
    
    @task(3)
    def login_and_check_profile(self):
        """Login and check user profile - common operation"""
        if not self.user_id:
            return
        
        try:
            # Login to get fresh tokens
            session_id = self.rm.create("login_session", {
                "email": self.user_email,
                "password": self.user_password
            }, adapter_name="auth")
            
            # Check profile
            profile = self.rm.read("user", self.user_id, adapter_name="auth")
            
            # Update last login time
            self.rm.update("user", self.user_id, {
                "last_login": time.time()
            }, adapter_name="auth")
            
            # Logout
            self.rm.delete("login_session", session_id, adapter_name="auth")
            
            print(f"✅ Login cycle completed for {self.user_email}")
            
        except Exception as e:
            print(f"❌ Login cycle failed: {e}")
    
    @task(2)
    def home_charging_session(self):
        """Simulate home charging - slower, longer sessions"""
        if not self.user_id or not self.ac_charger_id:
            return
        
        try:
            # Start home charging session
            txn_id = self.rm.create("transaction", {
                "emulator_id": self.ac_charger_id,
                "connector_id": 1,
                "id_tag": f"home_card_{self.user_id}",
                "user_id": self.user_id
            }, adapter_name="emulator")
            
            print(f"🏠 Started home charging: {txn_id}")
            
            # Home charging typically lasts longer
            charging_duration = random.randint(20, 60)  # 20-60 seconds in test
            time.sleep(charging_duration)
            
            # Stop charging
            self.rm.delete("transaction", txn_id, adapter_name="emulator")
            
            print(f"✅ Completed home charging session: {txn_id}")
            
        except Exception as e:
            print(f"❌ Home charging failed: {e}")
    
    @task(1)
    def fast_charging_session(self):
        """Simulate DC fast charging - quick, high-power sessions"""
        if not self.user_id or not self.dc_charger_id:
            return
        
        try:
            # Start fast charging session
            txn_id = self.rm.create("transaction", {
                "emulator_id": self.dc_charger_id,
                "connector_id": 1,
                "id_tag": f"fast_card_{self.user_id}",
                "user_id": self.user_id
            }, adapter_name="emulator")
            
            print(f"⚡ Started fast charging: {txn_id}")
            
            # Fast charging is quicker but more intensive
            charging_duration = random.randint(10, 30)  # 10-30 seconds in test
            time.sleep(charging_duration)
            
            # Stop charging
            self.rm.delete("transaction", txn_id, adapter_name="emulator")
            
            print(f"✅ Completed fast charging session: {txn_id}")
            
        except Exception as e:
            print(f"❌ Fast charging failed: {e}")
    
    @task(1)
    def update_user_preferences(self):
        """Update user preferences and settings"""
        if not self.user_id:
            return
        
        try:
            # Login first
            session_id = self.rm.create("login_session", {
                "email": self.user_email,
                "password": self.user_password
            }, adapter_name="auth")
            
            # Update preferences
            preferences = {
                "preferred_charging_power": random.choice([11, 22, 50, 150]),
                "notification_enabled": random.choice([True, False]),
                "auto_payment": random.choice([True, False]),
                "last_activity": time.time()
            }
            
            self.rm.update("user", self.user_id, preferences, adapter_name="auth")
            
            # Logout
            self.rm.delete("login_session", session_id, adapter_name="auth")
            
            print(f"✅ Updated preferences for user {self.user_id}")
            
        except Exception as e:
            print(f"❌ Preference update failed: {e}")
    
    @task(1)
    def check_charging_history(self):
        """Check charging history and statistics"""
        if not self.user_id:
            return
        
        try:
            # Login
            session_id = self.rm.create("login_session", {
                "email": self.user_email,
                "password": self.user_password
            }, adapter_name="auth")
            
            # Get user profile (includes charging stats)
            profile = self.rm.read("user", self.user_id, adapter_name="auth")
            
            # Simulate checking transaction history via REST API
            # (This would be a real API call in production)
            
            # Logout
            self.rm.delete("login_session", session_id, adapter_name="auth")
            
            print(f"✅ Checked history for user {self.user_id}")
            
        except Exception as e:
            print(f"❌ History check failed: {e}")
    
    def on_stop(self):
        """Cleanup when user stops"""
        try:
            # Complete rollback of all resources
            self.rm.rollback()
            print(f"🧹 Cleaned up all resources for {self.user_email}")
            
        except Exception as e:
            print(f"❌ Cleanup failed for {self.user_email}: {e}")

class AdminUser(HttpUser):
    """
    Simulates an admin user managing the charging network
    """
    wait_time = between(10, 30)  # Admins work more slowly
    weight = 1  # Fewer admin users compared to regular users
    
    def on_start(self):
        """Setup admin session"""
        self.rm = ResourceManager()
        
        # Setup adapters (same as regular user)
        self.rm.register_adapter("rest", RESTAdapter(self.host))
        self.rm.register_adapter("auth", UserAuthResourceAdapter(self.host))
        self.rm.register_adapter("emulator", EmulatorAdapter())
        
        # Create admin account
        admin_number = random.randint(1000, 9999)
        self.admin_email = f"admin_{admin_number}@company.com"
        self.admin_password = f"AdminPass{admin_number}!"
        
        try:
            self.admin_id = self.rm.create("user", {
                "email": self.admin_email,
                "password": self.admin_password,
                "name": f"Admin User {admin_number}",
                "role": "admin"
            }, adapter_name="auth")
            
            print(f"👑 Created admin: {self.admin_email}")
            
        except Exception as e:
            print(f"❌ Failed to create admin: {e}")
            self.admin_id = None
    
    @task(2)
    def monitor_charging_network(self):
        """Monitor the charging network status"""
        if not self.admin_id:
            return
        
        try:
            # Login as admin
            session_id = self.rm.create("login_session", {
                "email": self.admin_email,
                "password": self.admin_password
            }, adapter_name="auth")
            
            # Check emulator status
            emulator_adapter = self.rm._adapters["emulator"]
            active_emulators = emulator_adapter.get_active_emulators()
            
            print(f"👑 Admin monitoring: {len(active_emulators)} active emulators")
            
            # Logout
            self.rm.delete("login_session", session_id, adapter_name="auth")
            
        except Exception as e:
            print(f"❌ Admin monitoring failed: {e}")
    
    @task(1)
    def create_new_charging_station(self):
        """Create new charging stations"""
        if not self.admin_id:
            return
        
        try:
            # Create a new public charging station
            station_id = self.rm.create("charger_emulator", {
                "charger_id": f"PUBLIC_CHG_{random.randint(1000, 9999)}",
                "model": random.choice(["AC_11kW", "AC_22kW", "DC_50kW", "DC_150kW"]),
                "max_power": random.choice([11000, 22000, 50000, 150000]),
                "connectors": random.randint(1, 4),
                "location": f"Public Station {random.randint(1, 100)}"
            }, adapter_name="emulator")
            
            print(f"👑 Admin created charging station: {station_id}")
            
            # Simulate some monitoring time
            time.sleep(5)
            
            # Remove the station (simulate maintenance)
            self.rm.delete("charger_emulator", station_id, adapter_name="emulator")
            
            print(f"👑 Admin removed charging station: {station_id}")
            
        except Exception as e:
            print(f"❌ Admin station management failed: {e}")
    
    def on_stop(self):
        """Admin cleanup"""
        try:
            self.rm.rollback()
            print(f"🧹 Admin cleanup completed for {self.admin_email}")
        except Exception as e:
            print(f"❌ Admin cleanup failed: {e}")

# Locust event handlers for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("🚀 Load test started with TestLib integration")
    print(f"   Target host: {environment.host}")
    print(f"   User classes: ChargingStationUser, AdminUser")

@events.test_stop.add_listener  
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("🏁 Load test completed")
    print("   All TestLib resources should be cleaned up automatically")

# Custom Locust user classes with different behaviors
class PeakHourUser(ChargingStationUser):
    """User during peak hours - more aggressive charging"""
    wait_time = between(2, 8)  # Faster operations
    weight = 3  # More peak hour users
    
    @task(4)  # Higher priority for charging during peak
    def peak_hour_charging(self):
        """Aggressive charging behavior during peak hours"""
        # Prefer fast charging during peak times
        self.fast_charging_session()

class OffPeakUser(ChargingStationUser):
    """User during off-peak hours - more relaxed"""
    wait_time = between(15, 45)  # Slower operations
    weight = 2
    
    @task(4)  # Prefer home charging during off-peak
    def off_peak_charging(self):
        """Relaxed charging behavior during off-peak hours"""
        # Prefer home charging during off-peak
        self.home_charging_session()

if __name__ == "__main__":
    print("🏋️ TestLib Complete Locust Integration")
    print("=" * 50)
    print("Usage:")
    print("  locust -f locustfile_complete.py --host=http://localhost:8000")
    print("")
    print("User Types:")
    print("  - ChargingStationUser: Regular EV drivers")
    print("  - AdminUser: Network administrators") 
    print("  - PeakHourUser: Aggressive peak-time usage")
    print("  - OffPeakUser: Relaxed off-peak usage")
    print("")
    print("Features:")
    print("  - Complete authentication workflows")
    print("  - Realistic charging session simulation")
    print("  - Emulator integration with MQTT")
    print("  - Automatic resource cleanup")
    print("  - Error handling and reporting")
    print("  - Multiple user behavior patterns")