"""
Internal Support Ticket System - Databricks App
Stores operational data in Lakebase Postgres.
"""

import logging
import os
from datetime import datetime

from databricks.sdk import WorkspaceClient
from flask import Flask, jsonify, render_template, request

import lakebase_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket-system")

app = Flask(__name__)
_w = WorkspaceClient()


def _current_user_email() -> str:
    """
    Resolve the current user's email.
    Databricks Apps inject the logged-in user's identity via X-Forwarded-Email.
    """
    header_email = request.headers.get("X-Forwarded-Email")
    if header_email:
        return header_email
    return _w.current_user.me().user_name


@app.route("/healthz")
def healthz():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.errorhandler(Exception)
def handle_exception(err):
    """Ensure all unhandled errors return JSON."""
    logger.exception("Unhandled exception while processing request")
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


@app.route("/")
def index():
    """Render the main UI."""
    return render_template("index.html")


@app.route("/tickets", methods=["GET"])
def list_tickets():
    """
    List all tickets with message counts.
    Optional filters: status, created_by
    """
    status_filter = request.args.get("status")
    created_by_filter = request.args.get("created_by")
    
    query = """
        SELECT 
            t.ticket_id,
            t.title,
            t.status,
            t.created_by,
            t.created_at,
            COUNT(m.message_id) as message_count
        FROM tickets t
        LEFT JOIN ticket_messages m ON t.ticket_id = m.ticket_id
    """
    
    conditions = []
    params = []
    
    if status_filter:
        conditions.append("t.status = %s")
        params.append(status_filter)
    
    if created_by_filter:
        conditions.append("t.created_by = %s")
        params.append(created_by_filter)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += """
        GROUP BY t.ticket_id, t.title, t.status, t.created_by, t.created_at
        ORDER BY t.created_at DESC
    """
    
    tickets = lakebase_db.run_query(query, tuple(params))
    
    # Convert datetime to ISO format for JSON serialization
    for ticket in tickets:
        if ticket.get("created_at"):
            ticket["created_at"] = ticket["created_at"].isoformat()
    
    return jsonify(tickets)


@app.route("/tickets", methods=["POST"])
def create_ticket():
    """
    Create a new support ticket.
    Body: {"title": "...", "initial_message": "..."}
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.json
    title = data.get("title", "").strip()
    initial_message = data.get("initial_message", "").strip()
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
    
    if not initial_message:
        return jsonify({"error": "Initial message is required"}), 400
    
    email = _current_user_email()
    
    # Create ticket
    ticket = lakebase_db.run_write_returning(
        """
        INSERT INTO tickets (title, status, created_by)
        VALUES (%s, 'open', %s)
        RETURNING ticket_id, title, status, created_by, created_at
        """,
        (title, email),
    )
    
    # Add initial message
    lakebase_db.run_write(
        """
        INSERT INTO ticket_messages (ticket_id, message_text, author)
        VALUES (%s, %s, %s)
        """,
        (ticket["ticket_id"], initial_message, email),
    )
    
    # Convert datetime to ISO format
    if ticket.get("created_at"):
        ticket["created_at"] = ticket["created_at"].isoformat()
    
    return jsonify(ticket), 201


@app.route("/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """
    Get a single ticket with all its messages.
    """
    # Get ticket details
    tickets = lakebase_db.run_query(
        "SELECT * FROM tickets WHERE ticket_id = %s",
        (ticket_id,),
    )
    
    if not tickets:
        return jsonify({"error": "Ticket not found"}), 404
    
    ticket = tickets[0]
    
    # Get all messages for this ticket
    messages = lakebase_db.run_query(
        """
        SELECT message_id, ticket_id, message_text, author, created_at
        FROM ticket_messages
        WHERE ticket_id = %s
        ORDER BY created_at ASC
        """,
        (ticket_id,),
    )
    
    # Convert datetimes to ISO format
    if ticket.get("created_at"):
        ticket["created_at"] = ticket["created_at"].isoformat()
    
    for msg in messages:
        if msg.get("created_at"):
            msg["created_at"] = msg["created_at"].isoformat()
    
    ticket["messages"] = messages
    
    return jsonify(ticket)


@app.route("/tickets/<int:ticket_id>/status", methods=["PATCH"])
def update_ticket_status(ticket_id):
    """
    Update ticket status.
    Body: {"status": "open|in_progress|resolved|closed"}
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.json
    status = data.get("status", "").strip().lower()
    
    valid_statuses = ["open", "in_progress", "resolved", "closed"]
    if status not in valid_statuses:
        return jsonify({
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }), 400
    
    # Update the ticket
    lakebase_db.run_write(
        "UPDATE tickets SET status = %s WHERE ticket_id = %s",
        (status, ticket_id),
    )
    
    return jsonify({"ticket_id": ticket_id, "status": status})


@app.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    """
    Add a message to an existing ticket.
    Body: {"message_text": "..."}
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.json
    message_text = data.get("message_text", "").strip()
    
    if not message_text:
        return jsonify({"error": "Message text is required"}), 400
    
    # Verify ticket exists
    tickets = lakebase_db.run_query(
        "SELECT ticket_id FROM tickets WHERE ticket_id = %s",
        (ticket_id,),
    )
    
    if not tickets:
        return jsonify({"error": "Ticket not found"}), 404
    
    email = _current_user_email()
    
    # Add the message
    message = lakebase_db.run_write_returning(
        """
        INSERT INTO ticket_messages (ticket_id, message_text, author)
        VALUES (%s, %s, %s)
        RETURNING message_id, ticket_id, message_text, author, created_at
        """,
        (ticket_id, message_text, email),
    )
    
    # Convert datetime to ISO format
    if message.get("created_at"):
        message["created_at"] = message["created_at"].isoformat()
    
    return jsonify(message), 201


if __name__ == "__main__":
    # Ensure database schema exists on startup
    lakebase_db.ensure_schema()
    
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8000))
    app.run(debug=True, host=host, port=port)