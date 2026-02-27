import redis
import time

def test_acl_connection():
    try:
        # Use the newly created user credentials
        # Note: The password in URL needs URL encoding if it contains special chars
        # But here we can pass it directly to Redis client
        
        print("Connecting to Redis as 'admin'...")
        r = redis.Redis(
            host='localhost', 
            port=6379, 
            username='admin', 
            password='ecommerce_pwd', 
            decode_responses=True
        )
        
        if r.ping():
            print("Connection successful!")
        
        # Test key with the required prefix
        test_key = "Yang1024@q:test_key_3min"
        test_value = "This is a test value"
        ttl = 180  # 3 minutes
        
        print(f"Setting key '{test_key}' with {ttl}s TTL...")
        r.set(test_key, test_value, ex=ttl)
        
        # Verify
        val = r.get(test_key)
        expiry = r.ttl(test_key)
        
        print(f"Value retrieved: {val}")
        print(f"TTL remaining: {expiry} seconds")
        
        if val == test_value and expiry > 0:
            print("Test PASSED: Data inserted and verified correctly.")
        else:
            print("Test FAILED: Data verification failed.")
            
    except redis.exceptions.AuthenticationError:
        print("Authentication Failed!")
    except redis.exceptions.ResponseError as e:
        print(f"Redis Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_acl_connection()
