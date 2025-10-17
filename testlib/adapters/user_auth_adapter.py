# testlib/adapters/user_auth_adapter.py
import requests
import time
from typing import Dict, Optional, Tuple
import json

class UserAuthAdapter:
    """
    Simple adapter for user authentication workflow:
    1. Register user
    2. Login to get tokens
    3. Use tokens for authenticated requests
    4. Cleanup user
    """
    
    def __init__(self, base_url: str, config: Dict = None):
        self.base_url = base_url.rstrip("/")
        self.config = {
            "timeout": 30,
            "register_endpoint": "/auth/register",
            "login_endpoint": "/auth/login", 
            "refresh_endpoint": "/auth/refresh",
            "user_endpoint": "/users",
            **(config or {})
        }
        
        # Store authentication state
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.current_user_id = None
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def register_user(self, email: str, password: str, **extra_data) -> str:
        """
        Register a new user
        Returns: user_id
        """
        url = f"{self.base_url}{self.config['register_endpoint']}"
        
        payload = {
            "email": email,
            "password": password,
            **extra_data
        }
        
        print(f"🔐 Registering user: {email}")
        
        response = self.session.post(url, json=payload, timeout=self.config["timeout"])
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Registration failed: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Extract user ID (try common field names)
        user_id = None
        for field in ["id", "user_id", "userId", "_id"]:
            if field in data:
                user_id = str(data[field])
                break
        
        if not user_id:
            raise Exception(f"Could not extract user ID from response: {data}")
        
        self.current_user_id = user_id
        print(f"✅ User registered with ID: {user_id}")
        
        return user_id
    
    def login(self, email: str, password: str) -> Tuple[str, str]:
        """
        Login user and get tokens
        Returns: (access_token, refresh_token)
        """
        url = f"{self.base_url}{self.config['login_endpoint']}"
        
        payload = {
            "email": email,
            "password": password
        }
        
        print(f"🔑 Logging in user: {email}")
        
        response = self.session.post(url, json=payload, timeout=self.config["timeout"])
        
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Extract tokens (try common field names)
        access_token = None
        refresh_token = None
        
        for field in ["access_token", "accessToken", "token", "jwt"]:
            if field in data:
                access_token = data[field]
                break
        
        for field in ["refresh_token", "refreshToken", "refresh"]:
            if field in data:
                refresh_token = data[field]
                break
        
        if not access_token:
            raise Exception(f"Could not extract access token from response: {data}")
        
        # Store tokens
        self.access_token = access_token
        self.refresh_token = refresh_token
        
        # Calculate expiry (if provided)
        if "expires_in" in data:
            self.token_expires_at = time.time() + data["expires_in"]
        elif "exp" in data:
            self.token_expires_at = data["exp"]
        
        # Update session headers
        self.session.headers["Authorization"] = f"Bearer {access_token}"
        
        print(f"✅ Login successful, tokens obtained")
        print(f"   Access token: {access_token[:20]}...")
        if refresh_token:
            print(f"   Refresh token: {refresh_token[:20]}...")
        
        return access_token, refresh_token
    
    def refresh_access_token(self) -> str:
        """
        Refresh the access token using refresh token
        Returns: new_access_token
        """
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        url = f"{self.base_url}{self.config['refresh_endpoint']}"
        
        payload = {
            "refresh_token": self.refresh_token
        }
        
        print("🔄 Refreshing access token...")
        
        response = self.session.post(url, json=payload, timeout=self.config["timeout"])
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")
        
        data = response.json()
        
        # Extract new access token
        new_access_token = None
        for field in ["access_token", "accessToken", "token", "jwt"]:
            if field in data:
                new_access_token = data[field]
                break
        
        if not new_access_token:
            raise Exception(f"Could not extract new access token: {data}")
        
        # Update stored token
        self.access_token = new_access_token
        self.session.headers["Authorization"] = f"Bearer {new_access_token}"
        
        # Update expiry if provided
        if "expires_in" in data:
            self.token_expires_at = time.time() + data["expires_in"]
        
        print(f"✅ Access token refreshed: {new_access_token[:20]}...")
        
        return new_access_token
    
    def is_token_expired(self) -> bool:
        """Check if access token is expired"""
        if not self.token_expires_at:
            return False  # No expiry info, assume valid
        
        # Add 30 second buffer
        return time.time() > (self.token_expires_at - 30)
    
    def ensure_valid_token(self):
        """Ensure we have a valid access token, refresh if needed"""
        if not self.access_token:
            raise Exception("No access token available. Please login first.")
        
        if self.is_token_expired():
            print("⚠️  Access token expired, refreshing...")
            self.refresh_access_token()
    
    def authenticated_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an authenticated request
        """
        self.ensure_valid_token()
        
        url = f"{self.base_url}{endpoint}"
        
        response = self.session.request(
            method, 
            url, 
            timeout=self.config["timeout"],
            **kwargs
        )
        
        return response
    
    def get_user_profile(self, user_id: str = None) -> Dict:
        """Get user profile using authenticated request"""
        user_id = user_id or self.current_user_id
        if not user_id:
            raise Exception("No user ID available")
        
        print(f"👤 Getting profile for user: {user_id}")
        
        response = self.authenticated_request("GET", f"{self.config['user_endpoint']}/{user_id}")
        
        if response.status_code != 200:
            raise Exception(f"Get profile failed: {response.status_code} - {response.text}")
        
        profile = response.json()
        print(f"✅ Retrieved user profile: {profile.get('email', 'unknown')}")
        
        return profile
    
    def update_user_profile(self, user_id: str, data: Dict) -> Dict:
        """Update user profile using authenticated request"""
        print(f"📝 Updating profile for user: {user_id}")
        
        response = self.authenticated_request(
            "PUT", 
            f"{self.config['user_endpoint']}/{user_id}",
            json=data
        )
        
        if response.status_code not in [200, 204]:
            raise Exception(f"Update profile failed: {response.status_code} - {response.text}")
        
        if response.status_code == 204:
            return {"updated": True}
        
        updated_profile = response.json()
        print(f"✅ Profile updated successfully")
        
        return updated_profile
    
    def delete_user(self, user_id: str = None) -> bool:
        """Delete user using authenticated request"""
        user_id = user_id or self.current_user_id
        if not user_id:
            raise Exception("No user ID available")
        
        print(f"🗑️  Deleting user: {user_id}")
        
        response = self.authenticated_request("DELETE", f"{self.config['user_endpoint']}/{user_id}")
        
        if response.status_code not in [200, 204, 404]:
            raise Exception(f"Delete user failed: {response.status_code} - {response.text}")
        
        # Clear stored data
        if user_id == self.current_user_id:
            self.current_user_id = None
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None
            
            # Remove auth header
            if "Authorization" in self.session.headers:
                del self.session.headers["Authorization"]
        
        print(f"✅ User deleted successfully")
        
        return True
    
    def logout(self):
        """Clear authentication state"""
        print("👋 Logging out...")
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.current_user_id = None
        
        # Remove auth header
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
        
        print("✅ Logged out successfully")
    
    def get_auth_status(self) -> Dict:
        """Get current authentication status"""
        return {
            "logged_in": bool(self.access_token),
            "user_id": self.current_user_id,
            "has_refresh_token": bool(self.refresh_token),
            "token_expired": self.is_token_expired() if self.access_token else None,
            "expires_at": self.token_expires_at
        }

# Integration with ResourceManager
class UserAuthResourceAdapter:
    """
    Adapter that integrates UserAuthAdapter with ResourceManager
    """
    
    def __init__(self, base_url: str, config: Dict = None):
        self.auth_adapter = UserAuthAdapter(base_url, config)
        self._created_users = {}  # Track created users for cleanup
    
    def create(self, resource_type: str, data: Dict) -> str:
        """Create resources (register users, login sessions)"""
        if resource_type == "user":
            email = data["email"]
            password = data["password"]
            extra_data = {k: v for k, v in data.items() if k not in ["email", "password"]}
            
            user_id = self.auth_adapter.register_user(email, password, **extra_data)
            
            # Store user credentials for potential login
            self._created_users[user_id] = {
                "email": email,
                "password": password,
                "data": data
            }
            
            return user_id
        
        elif resource_type == "login_session":
            email = data["email"]
            password = data["password"]
            
            access_token, refresh_token = self.auth_adapter.login(email, password)
            
            # Return session ID (use access token as ID)
            session_id = f"session_{int(time.time())}"
            return session_id
        
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def read(self, resource_type: str, resource_id: str) -> Dict:
        """Read resources (user profiles, auth status)"""
        if resource_type == "user":
            return self.auth_adapter.get_user_profile(resource_id)
        
        elif resource_type == "auth_status":
            return self.auth_adapter.get_auth_status()
        
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def update(self, resource_type: str, resource_id: str, data: Dict) -> Dict:
        """Update resources (user profiles)"""
        if resource_type == "user":
            return self.auth_adapter.update_user_profile(resource_id, data)
        
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def delete(self, resource_type: str, resource_id: str) -> bool:
        """Delete resources (users, logout sessions)"""
        if resource_type == "user":
            success = self.auth_adapter.delete_user(resource_id)
            
            # Remove from tracking
            if resource_id in self._created_users:
                del self._created_users[resource_id]
            
            return success
        
        elif resource_type == "login_session":
            self.auth_adapter.logout()
            return True
        
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def get_created_users(self) -> Dict:
        """Get all created users for debugging"""
        return self._created_users.copy()