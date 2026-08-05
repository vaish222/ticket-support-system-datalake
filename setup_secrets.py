"""
One-time setup script: creates the Databricks secret scope and stores the Lakebase connection URL.

Run this locally (with the Databricks CLI configured) or from a notebook.
Never commit the resulting secret value anywhere.

Usage:
    python setup_secrets.py

The LAKEBASE_URL should be in the format:
    postgresql://username:password@host:5432/databricks_postgres?sslmode=require

Where:
  - username: Native Postgres role created in Lakebase
  - password: Static, non-expiring password for that role
  - host: Your Lakebase endpoint host (e.g., ep-xxx.cloud.databricks.com)

Note: Lakebase must have "Native password authentication" enabled.
"""
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace
import getpass
import base64

w = WorkspaceClient()

# Create secret scope (uncomment if not already created)
# w.secrets.create_scope(scope="database")

print("Enter your Lakebase connection URL:")
print("Format: postgresql://username:password@host:5432/databricks_postgres?sslmode=require")
print()
lakebase_url = getpass.getpass("Paste your Lakebase URL: ")

# Store the secret (base64 encoded)
w.secrets.put_secret(
    scope="database",
    key="lakebase-url",
    string_value=base64.b64encode(lakebase_url.encode()).decode()
)

print("\n✓ Secret stored successfully!")
print("  Scope: database")
print("  Key: lakebase-url")

# Grant read access to users
w.secrets.put_acl(
    scope="database",
    principal="users",
    permission=workspace.AclPermission.READ,
)

print("✓ Read permission granted to 'users' principal")
print("\nSetup complete! Your app can now connect to Lakebase.")
