#!/usr/bin/env python3
# setup_environment.py - Environment setup and validation

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return False

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible")
        print("   TestLib requires Python 3.8 or higher")
        return False

def create_virtual_environment():
    """Create and activate virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("📁 Virtual environment already exists")
        return True
    
    print("📁 Creating virtual environment...")
    if run_command(f"{sys.executable} -m venv venv", "Virtual environment creation"):
        print("💡 To activate the virtual environment:")
        if os.name == 'nt':  # Windows
            print("   venv\\Scripts\\activate")
        else:  # Unix/Linux/macOS
            print("   source venv/bin/activate")
        return True
    return False

def install_dependencies():
    """Install required dependencies"""
    requirements_files = ["requirements.txt"]
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if not in_venv:
        print("⚠️  Warning: Not in a virtual environment")
        print("   Consider activating the virtual environment first")
    
    for req_file in requirements_files:
        if Path(req_file).exists():
            cmd = f"{sys.executable} -m pip install -r {req_file}"
            if not run_command(cmd, f"Installing dependencies from {req_file}"):
                return False
        else:
            print(f"⚠️  {req_file} not found, skipping")
    
    return True

def validate_installation():
    """Validate that key dependencies are installed"""
    print("🔍 Validating installation...")
    
    required_packages = [
        ("requests", "HTTP client library"),
        ("websockets", "WebSocket support for OCPP"),
        ("ocpp", "OCPP protocol library"),
        ("paho.mqtt", "MQTT client library"),
        ("astral", "Solar calculations for inverter emulator")
    ]
    
    all_good = True
    
    for package, description in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} (MISSING)")
            all_good = False
    
    return all_good

def test_basic_functionality():
    """Test basic TestLib functionality"""
    print("🧪 Testing basic functionality...")
    
    try:
        # Test imports
        from testlib import ResourceManager
        from testlib.adapters import RESTAdapter, EmulatorAdapter
        print("✅ Core imports successful")
        
        # Test ResourceManager creation
        rm = ResourceManager()
        print("✅ ResourceManager creation successful")
        
        # Test adapter registration
        rm.register_adapter("rest", RESTAdapter("http://localhost:8000/api"))
        rm.register_adapter("emulator", EmulatorAdapter())
        print("✅ Adapter registration successful")
        
        # Test emulator creation (without actually starting)
        print("✅ Basic functionality test passed")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def create_example_config():
    """Create example configuration files"""
    print("📝 Creating example configuration files...")
    
    # Create .env example
    env_example = """# TestLib Environment Configuration
# Copy this file to .env and modify as needed

# REST API Configuration
REST_API_BASE_URL=http://localhost:8000/api

# MQTT Broker Configuration  
MQTT_BROKER_HOST=13.127.194.179
MQTT_BROKER_PORT=8000
MQTT_USERNAME=vikash
MQTT_PASSWORD=password

# OCPP Configuration
OCPP_WEBSOCKET_URL=ws://a285870195a5d4f9da391367ccd284a7-2128649528.ap-south-1.elb.amazonaws.com:8080

# Emulator Configuration
DEFAULT_LATITUDE=28.6139
DEFAULT_LONGITUDE=77.209
DEFAULT_TIMEZONE=Asia/Kolkata

# Testing Configuration
LOCUST_HOST=http://localhost:8000
PYTEST_TIMEOUT=30
"""
    
    with open(".env.example", "w") as f:
        f.write(env_example)
    print("✅ Created .env.example")
    
    # Create basic locustfile example
    locustfile_example = """# locustfile.py - Example Locust integration
from locust import HttpUser, task
from testlib import ResourceManager
from testlib.adapters import RESTAdapter, EmulatorAdapter

class TestLibUser(HttpUser):
    def on_start(self):
        self.rm = ResourceManager()
        self.rm.register_adapter("rest", RESTAdapter(self.host + "/api"))
        self.rm.register_adapter("emulator", EmulatorAdapter())
        
        # Create test infrastructure
        self.tenant_id = self.rm.create("tenant", {"name": f"LoadTest_{self.user_id}"})
        self.charger_id = self.rm.create("charger_emulator", {
            "charger_id": f"CHG_{self.user_id}",
            "max_power": 22000
        }, adapter_name="emulator")
    
    @task
    def charging_session(self):
        # Start transaction
        txn_id = self.rm.create("transaction", {
            "emulator_id": self.charger_id,
            "connector_id": 1,
            "id_tag": f"user_{self.user_id}"
        }, adapter_name="emulator")
        
        # Simulate charging
        self.wait_time = lambda: 2
        
        # Stop transaction
        self.rm.delete("transaction", txn_id, adapter_name="emulator")
    
    def on_stop(self):
        self.rm.rollback()
"""
    
    with open("locustfile.example.py", "w") as f:
        f.write(locustfile_example)
    print("✅ Created locustfile.example.py")
    
    return True

def main():
    """Main setup function"""
    print("🚀 TestLib Environment Setup")
    print("=" * 50)
    
    steps = [
        ("Python Version Check", check_python_version),
        ("Virtual Environment", create_virtual_environment),
        ("Dependencies Installation", install_dependencies),
        ("Installation Validation", validate_installation),
        ("Basic Functionality Test", test_basic_functionality),
        ("Example Configuration", create_example_config),
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        print(f"\n📋 Step: {step_name}")
        if not step_func():
            failed_steps.append(step_name)
    
    print("\n" + "=" * 50)
    print("🏁 Setup Summary")
    
    if not failed_steps:
        print("✅ All setup steps completed successfully!")
        print("\n🎉 TestLib is ready to use!")
        print("\n📚 Next steps:")
        print("   1. Activate virtual environment (if not already active)")
        print("   2. Copy .env.example to .env and configure")
        print("   3. Run: python example_unified_emulators.py")
        print("   4. For load testing: locust -f locustfile.example.py")
    else:
        print(f"❌ {len(failed_steps)} step(s) failed:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\n🔧 Please resolve the issues above and run setup again")
    
    return len(failed_steps) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)