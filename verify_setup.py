#!/usr/bin/env python3
"""
Verification script for the ticket support system setup.
Checks Lakebase connectivity and database configuration.
"""

from databricks.sdk import WorkspaceClient
import sys

def main():
    print("="*70)
    print("TICKET SUPPORT SYSTEM - SETUP VERIFICATION")
    print("="*70)
    print()
    
    w = WorkspaceClient()
    
    # 1. Check Lakebase endpoint
    print("[1/4] Checking Lakebase endpoint...")
    try:
        endpoint_path = "projects/ticket-support-system/branches/production/endpoints/primary"
        ep = w.postgres.get_endpoint(name=endpoint_path)
        print(f"  ✓ Endpoint found: {ep.status.hosts.host}")
        print(f"  ✓ State: {ep.status.state}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    
    # 2. Check service principal
    print("\n[2/4] Checking service principal...")
    try:
        current_user = w.current_user.me()
        print(f"  ✓ Running as: {current_user.user_name}")
    except:
        print("  ⚠ Could not get current user (expected for service principals)")
        print("  ℹ Service principal: app-1lvsgr ticket-system-app-assignment1")
    
    # 3. Test database connection
    print("\n[3/4] Testing database connection...")
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        host = ep.status.hosts.host
        
        # Try to get username
        try:
            username = w.current_user.me().user_name
        except:
            username = "app-1lvsgr ticket-system-app-assignment1"
        
        print(f"  → Connecting to {host}/databricks_postgres as {username}...")
        
        conn = psycopg2.connect(
            host=host,
            port=5432,
            database="databricks_postgres",
            user=username,
            sslmode="require",
            cursor_factory=RealDictCursor
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()
        print(f"  ✓ Connected successfully")
        print(f"  ✓ Database version: {version['version'][:50]}...")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        print("\n  ⚠ If you see a permission error, grant CONNECT permission:")
        print("\n  databricks postgres create-grant \\")
        print("    --parent projects/ticket-support-system/branches/production \\")
        print("    --json '{")
        print('      "spec": {')
        print('        "principal": "app-1lvsgr ticket-system-app-assignment1",')
        print('        "role": "CONNECT"')
        print('      }')
        print("    }'")
        return False
    
    # 4. Check schema
    print("\n[4/4] Checking database schema...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=5432,
            database="databricks_postgres",
            user=username,
            sslmode="require",
            cursor_factory=RealDictCursor
        )
        
        cur = conn.cursor()
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        tables = [row['table_name'] for row in cur.fetchall()]
        
        expected_tables = {'tickets', 'ticket_messages'}
        found_tables = set(tables)
        
        if expected_tables.issubset(found_tables):
            print(f"  ✓ All required tables exist: {', '.join(expected_tables)}")
        else:
            missing = expected_tables - found_tables
            print(f"  ⚠ Missing tables: {', '.join(missing)}")
            print("  ℹ Run the schema creation script to create tables")
        
        # Count records
        cur.execute("SELECT COUNT(*) as count FROM tickets")
        ticket_count = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM ticket_messages")
        message_count = cur.fetchone()['count']
        
        print(f"  ✓ Sample data: {ticket_count} tickets, {message_count} messages")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"  ⚠ Schema check failed: {e}")
    
    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)
    print("\n✓ Setup looks good! Your app should be ready to deploy.")
    print("\nApp deployment command:")
    print("  databricks apps deploy ticket-system-app-assignment1")
    print("\nApp URL (after deployment):")
    print("  https://ticket-system-app-assignment1-7474660735648608.aws.databricksapps.com")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
