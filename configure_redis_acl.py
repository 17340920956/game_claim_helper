import redis
import sys

def configure_acl():
    # Connect to Redis using default credentials (no password initially)
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Check connection
        if not r.ping():
            print("Could not connect to Redis.")
            return

        print("Connected to Redis.")
        
        # ACL Command from user
        acl_command = "ACL SETUSER admin on >ecommerce_pwd ~Yang1024@q:* +@all -FLUSHDB"
        
        # Execute ACL command
        # Redis-py's execute_command can run arbitrary commands
        # The command string needs to be split for execute_command if not using raw
        # But let's try passing the parts.
        
        # ACL SETUSER admin on >ecommerce_pwd ~Yang1024@q:* +@all -FLUSHDB
        try:
            r.execute_command("ACL", "SETUSER", "admin", "on", ">ecommerce_pwd", "~Yang1024@q:*", "+@all", "-FLUSHDB")
            print("ACL User 'admin' configured successfully.")
        except redis.exceptions.ResponseError as e:
            print(f"Failed to configure ACL: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    configure_acl()
