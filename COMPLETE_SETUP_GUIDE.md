# TestLib Complete Setup Guide

This guide covers the complete setup and usage of TestLib for comprehensive EV charging system testing.

## 🎯 What This System Tests

- **User Authentication**: Registration, login, token management
- **REST API Operations**: CRUD operations on tenants, users, chargers
- **OCPP Protocol**: Real charger communication simulation
- **MQTT Integration**: Inverter data publishing and monitoring
- **Charging Transactions**: Complete charging session workflows
- **Load Testing**: Realistic multi-user scenarios

## 🛠️ Prerequisites

### System Requirements
- Python 3.8+
- Node.js 18+ (optional, for JS emulators)
- MQTT Broker (Mosquitto recommended)
- Your EV charging API backend

### Dependencies Installation

```bash
# 1. Clone/setup your project
git clone <your-repo>
cd <your-project>

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 3. Install TestLib dependencies
pip install -r requirements.txt

# 4. Verify installation
python setup_environment.py
```

## 🔧 Configuration

### 1. Environment Variables

Create `.env` file:

```bash
# API Configuration
REST_API_BASE_URL=http://localhost:8000
REST_AUTH_TYPE=bearer
REST_AUTH_TOKEN=your-api-token

# Authentication Endpoints
AUTH_REGISTER_ENDPOINT=/auth/register
AUTH_LOGIN_ENDPOINT=/auth/login
AUTH_REFRESH_ENDPOINT=/auth/refresh
USER_ENDPOINT=/api/v1/users

# OCPP Configuration
OCPP_WEBSOCKET_URL=ws://localhost:8080

# MQTT Configuration
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=testuser
MQTT_PASSWORD=testpass

# Emulator Configuration
DEFAULT_LATITUDE=28.6139
DEFAULT_LONGITUDE=77.209
DEFAULT_TIMEZONE=Asia/Kolkata
```

### 2. API Endpoint Mapping

Update adapter configurations in your code:

```python
# REST API endpoints
rest_config = {
    "endpoints": {
        "tenant": "/api/v1/tenants",
        "user": "/api/v1/users", 
        "charger": "/api/v1/chargers",
        "transaction": "/api/v1/transactions"
    }
}

# Authentication endpoints
auth_config = {
    "register_endpoint": "/auth/register",
    "login_endpoint": "/auth/login",
    "refresh_endpoint": "/auth/refresh",
    "user_endpoint": "/api/v1/users"
}
```

## 🚀 Usage Examples

### 1. Basic System Test

```bash
# Run complete system test
python example_complete_system.py
```

This will:
- Create tenant and users
- Setup charging infrastructure
- Run charging sessions
- Monitor system for 60 seconds
- Generate report and cleanup

### 2. Load Testing with Locust

```bash
# Start Locust web interface
locust -f locustfile_complete.py --host=http://localhost:8000

# Or run headless
locust -f locustfile_complete.py --host=http://localhost:8000 \
       --users 50 --spawn-rate 5 --run-time 300s --headless
```

User types available:
- `ChargingStationUser`: Regular EV drivers (default)
- `AdminUser`: Network administrators
- `PeakHourUser`: Aggressive peak-time usage
- `OffPeakUser`: Relaxed off-peak usage

### 3. Authentication Testing

```bash
# Test authentication workflows
python example_user_auth_testing.py
```

### 4. Emulator Testing

```bash
# Test unified emulators
python example_unified_emulators.py
```

## 📊 Monitoring and Reporting

### Real-time Monitoring

The system provides real-time monitoring of:

```
⏱️  System Status at 30s:
   🔌 Active Emulators: 5
     - inverter_emulator_INV_001: inverter (running)
     - charger_emulator_AC_CHG_001: charger (running)
     - charger_emulator_DC_CHG_FAST: charger (running)
   🔐 Auth Status: logged_in=True
   ⚡ Active Transactions: 3
     - txn_AC_001: AC on AC_CHG_001
     - txn_DC_001: DC on DC_CHG_FAST
     - txn_OCPP_001: OCPP on OCPP_CHG_001
```

### Final Reports

```
📋 System Test Report
📊 Resources Created:
   - Tenants: 1
   - Users: 4
   - Chargers: 4
   - Inverters: 2
   - Transactions: 6
   - Total: 17

🔧 Adapter Status:
   - rest: configured
   - auth: logged_in=True
   - emulator: 7 active emulators
   - ocpp: 1 active chargers
```

## 🔍 Troubleshooting

### Common Issues

1. **API Connection Failed**
   ```
   ❌ Registration failed: 500 - Internal Server Error
   ```
   - Check if your API server is running
   - Verify endpoint URLs in configuration
   - Check authentication tokens

2. **OCPP Connection Failed**
   ```
   ❌ OCPP charger creation failed (server may be down)
   ```
   - Verify OCPP WebSocket server is running
   - Check WebSocket URL format
   - Ensure firewall allows WebSocket connections

3. **MQTT Connection Failed**
   ```
   ❌ MQTT connection failed: Connection refused
   ```
   - Start MQTT broker: `mosquitto -v`
   - Check broker host/port configuration
   - Verify username/password if authentication enabled

4. **Token Refresh Failed**
   ```
   ❌ Token refresh failed: 401 - Unauthorized
   ```
   - Check if refresh endpoint is implemented
   - Verify refresh token format
   - Check token expiry configuration

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run your tests with detailed logging
```

### Health Checks

```python
# Check adapter health
from testlib.adapters import RESTAdapter

adapter = RESTAdapter("http://localhost:8000")
if adapter.health_check():
    print("✅ API is healthy")
else:
    print("❌ API health check failed")
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Locust Users  │    │  Complete Test  │    │  Auth Testing   │
│                 │    │     System      │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     ResourceManager      │
                    │   (State Management)     │
                    └─────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐    ┌──────────▼──────────┐    ┌─────────▼─────────┐
│  REST Adapter  │    │  EmulatorAdapter    │    │  UserAuthAdapter  │
│                │    │                     │    │                   │
│ - CRUD Ops     │    │ - Python Emulators │    │ - Register/Login  │
│ - Auth Tokens  │    │ - MQTT Publishing  │    │ - Token Refresh   │
│ - Retries      │    │ - Real Physics     │    │ - Profile Mgmt    │
└────────────────┘    └─────────────────────┘    └───────────────────┘
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐    ┌─────────────────────┐    ┌───────────────────┐
│   Your API    │    │  MQTT Broker +      │    │  Auth Service     │
│   Backend     │    │  Emulated Devices   │    │                   │
└───────────────┘    └─────────────────────┘    └───────────────────┘
```

## 🎛️ Customization

### Adding Custom Adapters

```python
class CustomProtocolAdapter:
    def create(self, resource_type: str, data: dict) -> str:
        # Your custom creation logic
        pass
    
    def read(self, resource_type: str, resource_id: str) -> dict:
        # Your custom read logic
        pass
    
    def update(self, resource_type: str, resource_id: str, data: dict):
        # Your custom update logic
        pass
    
    def delete(self, resource_type: str, resource_id: str) -> bool:
        # Your custom deletion logic
        pass

# Register with ResourceManager
rm.register_adapter("custom", CustomProtocolAdapter())
```

### Custom Business Logic

```python
class EVChargingTestSuite(CompleteSystemTest):
    def custom_charging_scenario(self):
        """Your specific charging scenario"""
        # Create specific test data
        # Run custom workflows
        # Validate business rules
        pass
    
    def run_complete_test(self):
        # Call parent setup
        super().run_complete_test()
        
        # Add your custom scenarios
        self.custom_charging_scenario()
```

## 📈 Performance Tuning

### For High Load Testing

```python
# Optimize for performance
config = {
    "timeout": 5,           # Faster timeouts
    "max_retries": 1,       # Fewer retries
    "cache_ttl": 30,        # Short cache TTL
    "tick_interval_ms": 100 # Faster emulator ticks (10x speed)
}
```

### Resource Limits

```python
# Limit resource creation for large tests
class OptimizedSystemTest(CompleteSystemTest):
    def create_charging_infrastructure(self, tenant_id):
        # Create fewer emulators for large-scale tests
        # Use shared resources where possible
        pass
```

## 🔒 Security Considerations

- Store API tokens in environment variables
- Use HTTPS for production API endpoints
- Implement proper authentication in your API
- Rotate test credentials regularly
- Don't commit sensitive data to version control

## 📚 Next Steps

1. **Customize for Your API**: Update endpoints and data structures
2. **Add Business Logic**: Implement your specific test scenarios  
3. **Scale Testing**: Use multiple Locust workers for large-scale tests
4. **CI/CD Integration**: Add TestLib tests to your pipeline
5. **Monitoring**: Integrate with your monitoring systems

## 🆘 Support

For issues and questions:
1. Check this guide first
2. Review example files
3. Enable debug logging
4. Check adapter-specific documentation
5. Create detailed issue reports with logs

---

**Happy Testing! 🚀**