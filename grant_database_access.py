# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Check SDK Version
# Alternative: Use databricks CLI with proper auth
import subprocess
import json

print("Granting database access to app service principal...")
print("Using Databricks CLI\n")

# Create grant using CLI
grant_json = json.dumps({
    "spec": {
        "principal": "app-1lvsgr ticket-system-app-assignment1",
        "role": "CONNECT"
    }
})

cmd = [
    "databricks",
    "postgres",
    "create-grant",
    "--parent", "projects/ticket-support-system/branches/production",
    "--json", grant_json
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("✓ Grant created successfully!")
    print("✓ Database access granted!")
    if result.stdout:
        print(f"\nResponse: {result.stdout}")
except subprocess.CalledProcessError as e:
    if "already exists" in e.stderr.lower() or "AlreadyExists" in e.stderr:
        print("✓ Grant already exists - database access is already configured!")
    else:
        print(f"\n❌ CLI Error:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        raise
except Exception as e:
    print(f"\n❌ Error: {e}")
    raise

print("\n" + "="*70)
print("YOUR APP IS NOW READY!")
print("="*70)
print("\nApp URL: https://ticket-system-app-assignment1-7474660735648608.aws.databricksapps.com")
print("\nFeatures available:")
print("  ✓ View 4 sample tickets (open, in_progress, resolved)")
print("  ✓ View 12 messages across all tickets")
print("  ✓ Create new tickets")
print("  ✓ Add messages to tickets")
print("  ✓ Update ticket statuses")
print("\nOpen the URL above to test your support ticket system!")

# COMMAND ----------

# DBTITLE 1,Grant Database Access to App
# Step 1: Upgrade databricks-sdk to support Lakebase
import sys
import subprocess

print("Upgrading databricks-sdk...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "databricks-sdk>=0.118.0", "-q"])
print("✓ SDK upgraded")
print("\n⚠️  Restarting Python to load new SDK...")

# Restart Python to load the upgraded SDK
dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Step 2: Grant Database Access
# Step 2: Grant database access to app service principal
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Grant, GrantSpec, GrantRole

w = WorkspaceClient()

print("Granting database access to app service principal...")

try:
    grant = w.postgres.create_grant(
        parent="projects/ticket-support-system/branches/production",
        grant=Grant(spec=GrantSpec(
            principal="app-1lvsgr ticket-system-app-assignment1",
            role=GrantRole.CONNECT
        ))
    )
    print(f"\n✓ Grant created: {grant.name}")
    print("✓ Database access granted successfully!")
except Exception as e:
    if "already exists" in str(e).lower():
        print("\n✓ Grant already exists - database access is already configured!")
    else:
        raise

print("\n" + "="*70)
print("YOUR APP IS NOW READY!")
print("="*70)
print("\nApp URL: https://ticket-system-app-assignment1-7474660735648608.aws.databricksapps.com")
print("\nFeatures available:")
print("  ✓ View 4 sample tickets (open, in_progress, resolved)")
print("  ✓ View 12 messages across all tickets")
print("  ✓ Create new tickets")
print("  ✓ Add messages to tickets")
print("  ✓ Update ticket statuses")
print("\nOpen the URL above to test your support ticket system!")