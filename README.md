# Ticket Support System with Lakebase

An internal support system where users can create support tickets and add messages to those tickets. Built with Flask, deployed as a Databricks App, and backed by Lakebase Postgres.

## Architecture

- **Frontend**: HTML/CSS/JavaScript (responsive card-based UI)
- **Backend**: Flask REST API (Python)
- **Database**: Lakebase Postgres Autoscaling
- **Deployment**: Databricks Apps
- **Authentication**: Service Principal (no OAuth tokens required)

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

```

### 3. Deploy the App

The app is configured in `app.yaml` with the Lakebase resource.

Deploy using Databricks CLI:
```bash
cd /Workspace/Users/your-email@example.com/ticket-support-system-datalake
databricks apps deploy ticket-system-app-assignment1
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

**Service Principal Authentication (No OAuth)**

The app connects to Lakebase using service principal authentication:
- No OAuth tokens generated
- No password required in connection
- Service principal identity comes from the app's execution context
- Requires CONNECT grant on the Lakebase branch

See `app.py`, `lakebase.py`, and `lakebase_db.py` for implementation details.

## Files

- `app.py` - Main Flask application with REST API endpoints
- `lakebase.py` - Database connection helper (service principal auth)
- `lakebase_db.py` - Connection pooling module
- `app.yaml` - Databricks App configuration with Lakebase resource
- `requirements.txt` - Python dependencies
- `templates/index.html` - Frontend UI
- `setup_secrets.py` - Deprecated (OAuth removed)

## Sample Data

The database includes 4 sample tickets with different statuses and 12 messages across all tickets for testing.

## Troubleshooting

### App shows "App Not Available"
- Check that the service principal has CONNECT permission on the Lakebase branch
- Verify the endpoint path in `app.py` matches your Lakebase setup
- Check app logs: `databricks apps logs ticket-system-app-assignment1`

### Database connection errors
- Ensure the Lakebase endpoint is running
- Verify the service principal name matches in the grant
- Check that `app.yaml` includes the postgres resource with `permission: ALL`
