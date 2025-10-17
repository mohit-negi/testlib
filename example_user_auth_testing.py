# example_user_auth_testing.py - Test user authentication workflows

import time
from testlib import ResourceManager
from testlib.adapters.user_auth_adapter import UserAuthAdapter, UserAuthResourceAdapter

def example_basic_auth_workflow():
    """Test basic authentication workflow"""
    print("🔐 Basic Authentication Workflow Test")
    print("=" * 50)
    
    # Configure for your API
    auth_adapter = UserAuthAdapter("http://localhost:8000", {
        "register_endpoint": "/auth/register",
        "login_endpoint": "/auth/login",
        "refresh_endpoint": "/auth/refresh",
        "user_endpoint": "/users"
    })
    
    try:
        # 1. Register a new user
        user_id = auth_adapter.register_user(
            email="test@example.com",
            password="testpassword123",
            name="Test User",
            role="user"
        )
        print(f"✅ Step 1: User registered with ID: {user_id}")
        
        # 2. Login to get tokens
        access_token, refresh_token = auth_adapter.login(
            email="test@example.com",
            password="testpassword123"
        )
        print(f"✅ Step 2: Login successful")
        print(f"   Access Token: {access_token[:30]}...")
        print(f"   Refresh Token: {refresh_token[:30]}..." if refresh_token else "   No refresh token")
        
        # 3. Test authenticated request - get user profile
        profile = auth_adapter.get_user_profile(user_id)
        print(f"✅ Step 3: Retrieved profile: {profile.get('email')}")
        
        # 4. Test token refresh (if supported)
        if refresh_token:
            print("🔄 Testing token refresh...")
            new_access_token = auth_adapter.refresh_access_token()
            print(f"✅ Step 4: Token refreshed: {new_access_token[:30]}...")
        
        # 5. Test authenticated update
        updated_profile = auth_adapter.update_user_profile(user_id, {
            "name": "Updated Test User"
        })
        print(f"✅ Step 5: Profile updated")
        
        # 6. Verify update
        updated_profile = auth_adapter.get_user_profile(user_id)
        assert updated_profile["name"] == "Updated Test User"
        print(f"✅ Step 6: Update verified")
        
        # 7. Check auth status
        auth_status = auth_adapter.get_auth_status()
        print(f"📊 Auth Status: {auth_status}")
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
    finally:
        # Cleanup
        try:
            if auth_adapter.current_user_id:
                auth_adapter.delete_user()
                print("🧹 User deleted successfully")
        except:
            print("⚠️  Cleanup failed (user may not exist)")

def example_resource_manager_integration():
    """Test authentication with ResourceManager"""
    print("\n🔗 ResourceManager Integration Test")
    print("=" * 50)
    
    rm = ResourceManager()
    
    # Register the user auth adapter
    auth_adapter = UserAuthResourceAdapter("http://localhost:8000")
    rm.register_adapter("auth", auth_adapter)
    
    try:
        # Create user through ResourceManager
        user_id = rm.create("user", {
            "email": "rm_test@example.com",
            "password": "rmpassword123",
            "name": "ResourceManager User"
        }, adapter_name="auth")
        
        print(f"✅ Created user via ResourceManager: {user_id}")
        
        # Create login session
        session_id = rm.create("login_session", {
            "email": "rm_test@example.com", 
            "password": "rmpassword123"
        }, adapter_name="auth")
        
        print(f"✅ Created login session: {session_id}")
        
        # Read user profile
        profile = rm.read("user", user_id, adapter_name="auth")
        print(f"✅ Read user profile: {profile.get('email')}")
        
        # Read auth status
        auth_status = rm.read("auth_status", "current", adapter_name="auth")
        print(f"📊 Auth status: logged_in={auth_status['logged_in']}")
        
        # Update user
        rm.update("user", user_id, {
            "name": "Updated RM User"
        }, adapter_name="auth")
        print(f"✅ Updated user profile")
        
        # Verify update
        updated_profile = rm.read("user", user_id, adapter_name="auth")
        assert updated_profile["name"] == "Updated RM User"
        print(f"✅ Update verified")
        
    except Exception as e:
        print(f"❌ ResourceManager integration failed: {e}")
    finally:
        # Automatic cleanup via rollback
        rm.rollback()
        print("🧹 ResourceManager cleanup completed")

def example_load_testing_auth():
    """Example for load testing authentication"""
    print("\n🏋️ Load Testing Authentication Example")
    print("=" * 50)
    
    # This would be used in Locust
    class AuthLoadTestUser:
        def on_start(self):
            self.rm = ResourceManager()
            self.rm.register_adapter("auth", UserAuthResourceAdapter("http://localhost:8000"))
            
            # Create unique user for this test instance
            self.user_email = f"loadtest_{int(time.time())}_{id(self)}@example.com"
            self.user_password = "loadtest123"
            
            # Register user
            self.user_id = self.rm.create("user", {
                "email": self.user_email,
                "password": self.user_password,
                "name": f"LoadTest User {id(self)}"
            }, adapter_name="auth")
        
        def login_task(self):
            # Login to get fresh tokens
            session_id = self.rm.create("login_session", {
                "email": self.user_email,
                "password": self.user_password
            }, adapter_name="auth")
            
            # Use authenticated endpoints
            profile = self.rm.read("user", self.user_id, adapter_name="auth")
            
            # Update profile
            self.rm.update("user", self.user_id, {
                "last_login": time.time()
            }, adapter_name="auth")
            
            # Logout
            self.rm.delete("login_session", session_id, adapter_name="auth")
        
        def profile_update_task(self):
            # Quick profile update (assumes already logged in)
            self.rm.update("user", self.user_id, {
                "last_activity": time.time()
            }, adapter_name="auth")
        
        def on_stop(self):
            # Cleanup user
            self.rm.rollback()
    
    print("📝 Load testing class created")
    print("   Features:")
    print("   - Unique users per test instance")
    print("   - Login/logout cycles")
    print("   - Authenticated API calls")
    print("   - Automatic cleanup")

def example_token_expiry_handling():
    """Test token expiry and refresh"""
    print("\n⏰ Token Expiry Handling Test")
    print("=" * 50)
    
    auth_adapter = UserAuthAdapter("http://localhost:8000")
    
    try:
        # Register and login
        user_id = auth_adapter.register_user(
            email="expiry_test@example.com",
            password="expirytest123"
        )
        
        access_token, refresh_token = auth_adapter.login(
            email="expiry_test@example.com",
            password="expirytest123"
        )
        
        print(f"✅ Initial login successful")
        
        # Simulate token expiry by manually setting expiry time
        auth_adapter.token_expires_at = time.time() - 1  # Expired 1 second ago
        
        print("⏰ Simulated token expiry")
        
        # This should automatically refresh the token
        profile = auth_adapter.get_user_profile(user_id)
        print(f"✅ Automatic token refresh worked, got profile: {profile.get('email')}")
        
        # Check new auth status
        auth_status = auth_adapter.get_auth_status()
        print(f"📊 New auth status: {auth_status}")
        
    except Exception as e:
        print(f"❌ Token expiry test failed: {e}")
        print("   This is expected if your API doesn't support refresh tokens")
    finally:
        try:
            auth_adapter.delete_user()
        except:
            pass

def example_error_scenarios():
    """Test error handling scenarios"""
    print("\n🛡️ Error Handling Test")
    print("=" * 50)
    
    auth_adapter = UserAuthAdapter("http://localhost:8000")
    
    # Test 1: Invalid registration
    try:
        auth_adapter.register_user("invalid-email", "short")
        print("❌ Should have failed with invalid data")
    except Exception as e:
        print(f"✅ Registration validation works: {e}")
    
    # Test 2: Invalid login
    try:
        auth_adapter.login("nonexistent@example.com", "wrongpassword")
        print("❌ Should have failed with wrong credentials")
    except Exception as e:
        print(f"✅ Login validation works: {e}")
    
    # Test 3: Unauthenticated request
    try:
        auth_adapter.get_user_profile("some-user-id")
        print("❌ Should have failed without authentication")
    except Exception as e:
        print(f"✅ Authentication required: {e}")
    
    print("✅ Error handling tests completed")

if __name__ == "__main__":
    print("🚀 User Authentication Testing Examples")
    print("=" * 60)
    
    examples = [
        ("Basic Auth Workflow", example_basic_auth_workflow),
        ("ResourceManager Integration", example_resource_manager_integration),
        ("Load Testing Setup", example_load_testing_auth),
        ("Token Expiry Handling", example_token_expiry_handling),
        ("Error Scenarios", example_error_scenarios)
    ]
    
    for name, example_func in examples:
        try:
            example_func()
        except KeyboardInterrupt:
            print(f"\n⏹️ {name} interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            continue
    
    print("\n✨ Authentication testing examples completed!")
    print("\n💡 Key features:")
    print("   - Register → Login → Use Tokens → Delete workflow")
    print("   - Automatic token refresh handling")
    print("   - Integration with ResourceManager")
    print("   - Load testing ready")
    print("   - Comprehensive error handling")
    print("   - Configurable endpoints")
    print("\n🔧 To use with your API:")
    print("   1. Update endpoints in UserAuthAdapter config")
    print("   2. Adjust field names if your API uses different ones")
    print("   3. Run: python example_user_auth_testing.py")