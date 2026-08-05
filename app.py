from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from databricks.sdk import WorkspaceClient
import base64
import os

app = Flask(__name__)

# Secret configuration
SECRET_SCOPE = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
SECRET_KEY = os.environ.get("LAKEBASE_SECRET_KEY", "lakebase-url")

def get_lakebase_url():
    """Fetch the Lakebase connection URL from Databricks secrets."""
    w = WorkspaceClient()
    secret = w.secrets.get_secret(scope=SECRET_SCOPE, key=SECRET_KEY)
    return base64.b64decode(secret.value).decode("utf-8")

def get_db_connection():
    """Create a connection to Lakebase using native password authentication."""
    # Get the connection URL (format: postgresql://user:password@host:port/database?sslmode=require)
    lakebase_url = get_lakebase_url()
    
    # Connect using the URL which includes username and static password
    conn = psycopg2.connect(lakebase_url, cursor_factory=RealDictCursor)
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tickets', methods=['GET'])
def get_tickets():
    """Get all tickets, optionally filtered by status."""
    status = request.args.get('status')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if status:
            cur.execute("""
                SELECT t.*, COUNT(m.message_id) as message_count
                FROM tickets t
                LEFT JOIN ticket_messages m ON t.ticket_id = m.ticket_id
                WHERE t.status = %s
                GROUP BY t.ticket_id
                ORDER BY t.created_at DESC
            """, (status,))
        else:
            cur.execute("""
                SELECT t.*, COUNT(m.message_id) as message_count
                FROM tickets t
                LEFT JOIN ticket_messages m ON t.ticket_id = m.ticket_id
                GROUP BY t.ticket_id
                ORDER BY t.created_at DESC
            """)
        
        tickets = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify(tickets)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tickets', methods=['POST'])
def create_ticket():
    """Create a new ticket with an initial message."""
    data = request.json
    title = data.get('title')
    initial_message = data.get('initial_message')
    
    if not title or not initial_message:
        return jsonify({"error": "Title and initial_message are required"}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get current user for created_by
        w = WorkspaceClient()
        current_user = w.current_user.me()
        created_by = current_user.user_name
        
        # Create ticket
        cur.execute("""
            INSERT INTO tickets (title, status, created_by)
            VALUES (%s, 'open', %s)
            RETURNING ticket_id
        """, (title, created_by))
        
        ticket_id = cur.fetchone()['ticket_id']
        
        # Add initial message
        cur.execute("""
            INSERT INTO ticket_messages (ticket_id, message_text, author)
            VALUES (%s, %s, %s)
        """, (ticket_id, initial_message, created_by))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"ticket_id": ticket_id, "message": "Ticket created successfully"}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    """Get a single ticket with all its messages."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get ticket
        cur.execute("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
        ticket = cur.fetchone()
        
        if not ticket:
            cur.close()
            conn.close()
            return jsonify({"error": "Ticket not found"}), 404
        
        # Get messages
        cur.execute("""
            SELECT * FROM ticket_messages
            WHERE ticket_id = %s
            ORDER BY created_at ASC
        """, (ticket_id,))
        messages = cur.fetchall()
        
        cur.close()
        conn.close()
        
        ticket['messages'] = messages
        return jsonify(ticket)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tickets/<int:ticket_id>/status', methods=['PATCH'])
def update_ticket_status(ticket_id):
    """Update the status of a ticket."""
    data = request.json
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({"error": "Status is required"}), 400
    
    valid_statuses = ['open', 'in_progress', 'resolved', 'closed']
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE tickets
            SET status = %s
            WHERE ticket_id = %s
            RETURNING ticket_id
        """, (new_status, ticket_id))
        
        result = cur.fetchone()
        
        if not result:
            cur.close()
            conn.close()
            return jsonify({"error": "Ticket not found"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Status updated successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tickets/<int:ticket_id>/messages', methods=['POST'])
def add_message(ticket_id):
    """Add a message to a ticket."""
    data = request.json
    message_text = data.get('message_text')
    
    if not message_text:
        return jsonify({"error": "message_text is required"}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify ticket exists
        cur.execute("SELECT ticket_id FROM tickets WHERE ticket_id = %s", (ticket_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Ticket not found"}), 404
        
        # Get current user
        w = WorkspaceClient()
        current_user = w.current_user.me()
        author = current_user.user_name
        
        # Add message
        cur.execute("""
            INSERT INTO ticket_messages (ticket_id, message_text, author)
            VALUES (%s, %s, %s)
            RETURNING message_id
        """, (ticket_id, message_text, author))
        
        message_id = cur.fetchone()['message_id']
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message_id": message_id, "message": "Message added successfully"}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)