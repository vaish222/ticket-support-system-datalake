# Ticket Support System with Lakebase

An internal support system where users can create support tickets and add messages to those tickets. Built with Flask, deployed as a Databricks App, and backed by Lakebase Postgres.

## Architecture

- **Frontend**: HTML/CSS/JavaScript (responsive card-based UI)
- **Backend**: Flask REST API (Python)
- **Database**: Lakebase Postgres Autoscaling
- **Deployment**: Databricks Apps
- **Authentication**: Native Postgres password (static, non-expiring)

## Database Schema

### Tables

**tickets**
- `ticket_id` (SERIAL PRIMARY KEY)
- `title` (VARCHAR(500))
- `status` (VARCHAR(50)) - Values: open, in_progress, resolved, closed
- `created_by` (VARCHAR(255))
- `created_at` (TIMESTAMPTZ)

**ticket_messages**
- `message_id` (SERIAL PRIMARY KEY)
- `ticket_id` (INTEGER REFERENCES tickets)
- `message_text` (TEXT)
- `author` (VARCHAR(255))
- `created_at` (TIMESTAMPTZ)

## Setup Instructions

### 1. Lakebase Resources

The app uses these Lakebase resources:
- **Project**: `ticket-support-system`
- **Branch**: `production`
- **Endpoint**: `primary`
- **Database**: `databricks_postgres`

Full endpoint path: `projects/ticket-support-system/branches/production/endpoints/primary`

### 2. Enable Native Password Authentication

In your Lakebase instance settings:
1. Look for **"Native passwords"** or **"Password authentication"** setting
2. Toggle/enable it (some Lakebase instances only support OAuth by default)
3. This allows you to create Postgres roles with static, non-expiring passwords

### 3. Create Native Postgres Role

Create a dedicated Postgres role for the app:

```sql
-- Connect to your Lakebase database
CREATE ROLE ticket_app_role WITH LOGIN PASSWORD 'your_secure_password';

-- Grant permissions
GRANT CONNECT ON DATABASE databricks_postgres TO ticket_app_role;
GRANT USAGE ON SCHEMA public TO ticket_app_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ticket_app_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ticket_app_role;
```

### 4. Store Connection Secret

Run the setup script to store the Lakebase connection URL in Databricks secrets:

```bash
python setup_secrets.py
```

When prompted, enter your connection URL in this format:
```
postgresql://ticket_app_role:your_secure_password@ep-xxxxx.cloud.databricks.com:5432/databricks_postgres?sslmode=require
```

Replace:
- `ticket_app_role` - your Postgres role name
- `your_secure_password` - the role's password
- `ep-xxxxx.cloud.databricks.com` - your Lakebase endpoint host

The script will:
- Base64 encode the URL for security
- Store it in the `database` secret scope as `lakebase-url`
- Grant read access to the `users` principal

### 5. Deploy the App

The app is configured in `app.yaml` with the Lakebase resource and secret environment variables.

Deploy using Databricks CLI:
```bash
cd /Workspace/Users/vaishali221@gmail.com/ticket-support-system-datalake
databricks apps deploy ticket-system-app-assignment1
```

After deployment, access your app at:
```
https://ticket-system-app-assignment1-7474660735648608.aws.databricksapps.com
```

## API Endpoints

### Get All Tickets
```
GET /tickets?status=open
```
Returns all tickets, optionally filtered by status.

### Get Single Ticket
```
GET /tickets/{ticket_id}
```
Returns ticket details with all messages.

### Create Ticket
```
POST /tickets
Content-Type: application/json

{
  "title": "Ticket title",
  "initial_message": "Message text"
}
```

### Update Ticket Status
```
PATCH /tickets/{ticket_id}/status
Content-Type: application/json

{
  "status": "in_progress"
}
```

### Add Message to Ticket
```
POST /tickets/{ticket_id}/messages
Content-Type: application/json

{
  "message_text": "Reply text"
}
```

## Authentication Model

**Native Postgres Password Authentication**

The app connects to Lakebase using a native Postgres role with a static password:

- **Connection URL format**: `postgresql://username:password@host:5432/database?sslmode=require`
- **Username**: Native Postgres role created in Lakebase
- **Password**: Static, non-expiring password (no token refresh needed)
- **Storage**: Connection URL stored in Databricks secrets (base64 encoded)
- **Requirement**: "Native password authentication" must be enabled in Lakebase

**Secret Configuration:**
- **Scope**: `database`
- **Key**: `lakebase-url`
- **Value**: Base64-encoded connection URL
- **Environment Variables**: 
  - `LAKEBASE_SECRET_SCOPE` → `database`
  - `LAKEBASE_SECRET_KEY` → `lakebase-url`

**How it works:**
1. App reads `LAKEBASE_SECRET_SCOPE` and `LAKEBASE_SECRET_KEY` from environment (set in `app.yaml`)
2. Retrieves the secret using `w.secrets.get_secret(scope, key)`
3. Base64 decodes the connection URL
4. Connects to Lakebase using `psycopg2.connect(url)`
5. No token generation or refresh logic needed

See `app.py`, `lakebase.py`, and `lakebase_db.py` for implementation details.

## Files

- `app.py` - Main Flask application with REST API endpoints
- `lakebase.py` - Database connection helper (native password auth)
- `lakebase_db.py` - Connection pooling module
- `app.yaml` - Databricks App configuration with Lakebase resource and secrets
- `requirements.txt` - Python dependencies (Flask, databricks-sdk, psycopg2-binary)
- `templates/index.html` - Frontend UI (responsive card-based design)
- `setup_secrets.py` - One-time setup script to store Lakebase connection URL
- `verify_setup.py` - Verification script to test database connectivity

## Sample Data

The database includes 4 sample tickets with different statuses and 12 messages across all tickets for testing.

## Troubleshooting

### App shows "App Not Available"
- Check app deployment status: `databricks apps list`
- Check app logs: `databricks apps logs ticket-system-app-assignment1`
- Verify the Lakebase endpoint is running and accessible

### Database connection errors

**"Could not connect to server" or "connection refused":**
- Ensure the Lakebase endpoint is running
- Verify the host in your connection URL is correct
- Check that port 5432 is accessible

**"password authentication failed":**
- Verify "Native password authentication" is enabled in Lakebase
- Check that the Postgres role exists and password is correct
- Re-run `setup_secrets.py` to update the connection URL

**"permission denied":**
- Ensure the Postgres role has proper grants:
  ```sql
  GRANT CONNECT ON DATABASE databricks_postgres TO ticket_app_role;
  GRANT USAGE ON SCHEMA public TO ticket_app_role;
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ticket_app_role;
  ```

**"secret not found":**
- Run `setup_secrets.py` to create the secret
- Verify secret scope and key match environment variables in `app.yaml`
- Check secret exists: `databricks secrets list --scope database`

### Verify Setup

Run the verification script to test all components:
```bash
python verify_setup.py
```

This will check:
- Lakebase endpoint connectivity
- Secret configuration
- Database connection
- Schema and sample data
