"""
Blood Donation Alert System - Flask Backend
Main application file handling all routes and business logic
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import os
from dotenv import load_dotenv
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3

# Try to import MySQL connector, but don't fail if not available
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("MySQL connector not available. Using SQLite instead.")

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'  # Default to SQLite
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'blood_donation_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', 3306))
}

# SQLite database file path
SQLITE_DB = 'blood_donation.db'

# Email configuration
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'email': os.getenv('EMAIL_USER', ''),
    'password': os.getenv('EMAIL_PASSWORD', '')
}

# WhatsApp API configuration (using Twilio or similar)
WHATSAPP_CONFIG = {
    'account_sid': os.getenv('WHATSAPP_ACCOUNT_SID', ''),
    'auth_token': os.getenv('WHATSAPP_AUTH_TOKEN', ''),
    'from_number': os.getenv('WHATSAPP_FROM_NUMBER', '')
}


def get_db_connection():
    """Create and return database connection (MySQL or SQLite)"""
    # Try MySQL first if available and not forced to use SQLite
    if MYSQL_AVAILABLE and not USE_SQLITE:
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            return ('mysql', connection)
        except Exception as e:
            print(f"MySQL connection failed: {e}")
            print("Falling back to SQLite...")
    
    # Use SQLite (default or fallback)
    try:
        # SQLite connection with timeout and proper isolation
        connection = sqlite3.connect(
            SQLITE_DB,
            timeout=20.0,  # Wait up to 20 seconds if database is locked
            check_same_thread=False  # Allow multiple threads
        )
        connection.row_factory = sqlite3.Row  # Enable column access by name
        # Enable WAL mode for better concurrency
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA busy_timeout=20000')  # 20 second timeout
        return ('sqlite', connection)
    except Exception as e:
        print(f"Error connecting to SQLite: {e}")
        return None


def init_database():
    """Initialize database tables if they don't exist"""
    db_result = get_db_connection()
    if not db_result:
        return False
    
    db_type, connection = db_result
    
    try:
        cursor = connection.cursor()
        
        if db_type == 'mysql':
            # MySQL syntax
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS donors (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    blood_group VARCHAR(5) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    location VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_email (email),
                    UNIQUE KEY unique_phone (phone)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blood_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hospital_name VARCHAR(200) NOT NULL,
                    hospital_email VARCHAR(100) NOT NULL,
                    hospital_phone VARCHAR(20) NOT NULL,
                    hospital_location VARCHAR(100) NOT NULL,
                    required_blood_group VARCHAR(5) NOT NULL,
                    patient_details TEXT,
                    urgency_level VARCHAR(20) DEFAULT 'normal',
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    request_id INT NOT NULL,
                    donor_id INT NOT NULL,
                    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES blood_requests(id) ON DELETE CASCADE,
                    FOREIGN KEY (donor_id) REFERENCES donors(id) ON DELETE CASCADE
                )
            """)
        else:
            # SQLite syntax
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS donors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    blood_group VARCHAR(5) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    phone VARCHAR(20) NOT NULL UNIQUE,
                    location VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blood_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hospital_name VARCHAR(200) NOT NULL,
                    hospital_email VARCHAR(100) NOT NULL,
                    hospital_phone VARCHAR(20) NOT NULL,
                    hospital_location VARCHAR(100) NOT NULL,
                    required_blood_group VARCHAR(5) NOT NULL,
                    patient_details TEXT,
                    urgency_level VARCHAR(20) DEFAULT 'normal',
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    donor_id INTEGER NOT NULL,
                    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES blood_requests(id) ON DELETE CASCADE,
                    FOREIGN KEY (donor_id) REFERENCES donors(id) ON DELETE CASCADE
                )
            """)
        
        connection.commit()
        cursor.close()
        connection.close()
        db_name = "SQLite" if db_type == 'sqlite' else "MySQL"
        print(f"✅ Database initialized successfully using {db_name}!")
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


# Blood compatibility matrix
BLOOD_COMPATIBILITY = {
    'A+': ['A+', 'A-', 'O+', 'O-'],
    'A-': ['A-', 'O-'],
    'B+': ['B+', 'B-', 'O+', 'O-'],
    'B-': ['B-', 'O-'],
    'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
    'AB-': ['A-', 'B-', 'AB-', 'O-'],
    'O+': ['O+', 'O-'],
    'O-': ['O-']
}


def calculate_location_distance(loc1, loc2):
    """
    Simple location matching - in production, use geocoding API
    For now, exact match or substring match
    """
    loc1_clean = loc1.lower().strip()
    loc2_clean = loc2.lower().strip()
    
    # Exact match
    if loc1_clean == loc2_clean:
        return 0
    
    # Check if one location contains the other (for same city/district)
    if loc1_clean in loc2_clean or loc2_clean in loc1_clean:
        return 1
    
    # Different locations
    return 2


def _row_to_dict(row, db_type):
    """Convert database row to dictionary"""
    if db_type == 'sqlite':
        return dict(row)
    else:
        return row

def find_compatible_donors(required_blood_group, hospital_location):
    """Find compatible donors based on blood group and location"""
    db_result = get_db_connection()
    if not db_result:
        return [], []
    
    db_type, connection = db_result
    cursor = None
    
    try:
        if db_type == 'mysql':
            cursor = connection.cursor(dictionary=True)
        else:
            cursor = connection.cursor()
        
        # Get compatible blood groups
        compatible_groups = BLOOD_COMPATIBILITY.get(required_blood_group, [])
        
        if not compatible_groups:
            return [], []
        
        # Find all compatible donors
        if db_type == 'mysql':
            placeholders = ','.join(['%s'] * len(compatible_groups))
        else:
            placeholders = ','.join(['?'] * len(compatible_groups))
        
        query = f"""
            SELECT id, name, blood_group, email, phone, location
            FROM donors
            WHERE blood_group IN ({placeholders})
        """
        cursor.execute(query, compatible_groups)
        all_donors = cursor.fetchall()
        
        # Convert to dictionaries
        all_donors = [_row_to_dict(row, db_type) for row in all_donors]
        
        # Separate by location proximity
        nearby_donors = []
        far_donors = []
        
        for donor in all_donors:
            distance = calculate_location_distance(donor['location'], hospital_location)
            if distance <= 1:  # Same or nearby location
                nearby_donors.append(donor)
            else:
                far_donors.append(donor)
        
        return nearby_donors, far_donors
    
    except Exception as e:
        print(f"Error finding compatible donors: {e}")
        return [], []
    finally:
        # Always close connections properly
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def send_email_notification(donor_email, donor_name, request_details):
    """Send email notification to donor (with timeout protection)"""
    # Check if email is configured
    if not EMAIL_CONFIG.get('email') or not EMAIL_CONFIG.get('password'):
        return False  # Silently skip if not configured
    
    try:
        import socket
        socket.setdefaulttimeout(10)  # 10 second timeout
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = donor_email
        msg['Subject'] = 'Urgent Blood Donation Request'
        
        body = f"""
Dear {donor_name},

We have an urgent blood donation request that matches your blood group ({request_details['blood_group']}).

Hospital Details:
- Hospital Name: {request_details['hospital_name']}
- Location: {request_details['hospital_location']}
- Contact Email: {request_details['hospital_email']}
- Contact Phone: {request_details['hospital_phone']}

{f"Patient Details: {request_details.get('patient_details', 'N/A')}" if request_details.get('patient_details') else ''}

If you are available and willing to help, please contact the hospital directly using the information above.

Thank you for being a part of our life-saving network.

Best regards,
Blood Donation Alert System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=10)
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except socket.timeout:
        print(f"⚠️  Email timeout for {donor_email}")
        return False
    except Exception as e:
        error_msg = str(e)
        if '535' in error_msg or 'BadCredentials' in error_msg:
            # Don't print error for every donor if credentials are wrong
            pass
        return False


def send_whatsapp_notification(donor_phone, donor_name, request_details):
    """Send WhatsApp notification to donor (Free alternative using pywhatkit) - Non-blocking"""
    try:
        # Check if WhatsApp Web is enabled
        use_whatsapp_web = os.getenv('USE_WHATSAPP_WEB', 'false').lower() == 'true'
        
        if not use_whatsapp_web:
            # WhatsApp is optional - email notifications work fine!
            return True  # Return True to not block the flow
        
        # Skip WhatsApp for now to prevent blocking - can be enabled later
        # pywhatkit requires browser automation which can hang the request
        return True
        
        # Uncomment below if you want to enable WhatsApp Web (not recommended for production)
        # try:
        #     import pywhatkit as pwk
        #     from datetime import datetime, timedelta
        #     
        #     # Format phone number (remove +, spaces, etc.)
        #     phone = donor_phone.replace('+', '').replace(' ', '').replace('-', '')
        #     # Ensure it starts with country code (add 91 for India if not present)
        #     if not phone.startswith('91') and len(phone) == 10:
        #         phone = '91' + phone
        #     
        #     # Prepare message
        #     message = f"""*Urgent Blood Donation Request*
        # 
        # Dear {donor_name},
        # 
        # We have an urgent blood donation request matching your blood group ({request_details['blood_group']}).
        # 
        # *Hospital Details:*
        # 🏥 {request_details['hospital_name']}
        # 📍 {request_details['hospital_location']}
        # 📧 {request_details['hospital_email']}
        # 📞 {request_details['hospital_phone']}
        # 
        # {f"*Patient Details:* {request_details.get('patient_details', 'N/A')}" if request_details.get('patient_details') else ''}
        # 
        # If available, please contact the hospital directly.
        # 
        # Thank you for your compassion."""
        #     
        #     # Calculate time 2 minutes from now (pywhatkit needs future time)
        #     now = datetime.now()
        #     send_time = now + timedelta(minutes=2)
        #     hour = send_time.hour
        #     minute = send_time.minute
        #     
        #     # Send WhatsApp message
        #     pwk.sendwhatmsg(f"+{phone}", message, hour, minute, wait_time=15, tab_close=True)
        #     
        #     print(f"✅ WhatsApp message scheduled for {donor_name} at {hour}:{minute}")
        #     return True
        #     
        # except ImportError:
        #     return True
        # except Exception as e:
        #     return True
            
    except Exception as e:
        # Silently fail - don't block the request
        return True


# ==================== ROUTES ====================

@app.route('/')
def index():
    """First page - Login/Entry page"""
    return render_template('index.html')


@app.route('/donor-form')
def donor_form():
    """Donor registration form page"""
    return render_template('donor_form.html')


@app.route('/requester-form')
def requester_form():
    """Requester (Hospital) form page"""
    return render_template('requester_form.html')


@app.route('/main')
def main_page():
    """Main page showing donor statistics"""
    db_result = get_db_connection()
    if not db_result:
        return render_template('main.html', stats={})
    
    db_type, connection = db_result
    
    try:
        if db_type == 'mysql':
            cursor = connection.cursor(dictionary=True)
        else:
            cursor = connection.cursor()
        
        # Get total donor count
        cursor.execute("SELECT COUNT(*) as total FROM donors")
        row = cursor.fetchone()
        total_donors = row['total'] if db_type == 'mysql' else row[0]
        
        # Get blood group-wise counts
        cursor.execute("""
            SELECT blood_group, COUNT(*) as count
            FROM donors
            GROUP BY blood_group
            ORDER BY blood_group
        """)
        rows = cursor.fetchall()
        blood_group_stats = {}
        for row in rows:
            if db_type == 'mysql':
                blood_group_stats[row['blood_group']] = row['count']
            else:
                blood_group_stats[row[0]] = row[1]
        
        # Get location-wise counts
        cursor.execute("""
            SELECT location, COUNT(*) as count
            FROM donors
            GROUP BY location
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        location_stats = {}
        for row in rows:
            if db_type == 'mysql':
                location_stats[row['location']] = row['count']
            else:
                location_stats[row[0]] = row[1]
        
        cursor.close()
        connection.close()
        
        stats = {
            'total_donors': total_donors,
            'blood_group_stats': blood_group_stats,
            'location_stats': location_stats
        }
        
        return render_template('main.html', stats=stats)
    
    except Exception as e:
        print(f"Error fetching statistics: {e}")
        return render_template('main.html', stats={})


@app.route('/details')
def details_page():
    """Details/Information page with FAQ"""
    # Initialize stats
    stats = {'total_donors': 0}
    connections_made = 0
    
    db_result = get_db_connection()
    if db_result:
        try:
            db_type, connection = db_result
            cursor = connection.cursor()
            
            # Get total donor count for stats
            cursor.execute("SELECT COUNT(*) as total FROM donors")
            row = cursor.fetchone()
            stats['total_donors'] = row[0] if db_type == 'sqlite' else row['total']
            
            # Get connections made (matches)
            cursor.execute("SELECT COUNT(*) as total FROM matches")
            row = cursor.fetchone()
            connections_made = row[0] if db_type == 'sqlite' else row['total']
            
            cursor.close()
            connection.close()
        except Exception as e:
            print(f"Error fetching statistics: {e}")
    
    return render_template('details.html', stats=stats, connections_made=connections_made)


@app.route('/donor-match')
def donor_match_page():
    """Donor match page showing matched donors"""
    request_id = request.args.get('request_id', type=int)
    
    if not request_id:
        return redirect(url_for('main_page'))
    
    db_result = get_db_connection()
    if not db_result:
        return render_template('donor_match.html', nearby_count=0, far_count=0)
    
    db_type, connection = db_result
    
    try:
        if db_type == 'mysql':
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT required_blood_group, hospital_location
                FROM blood_requests
                WHERE id = %s
            """, (request_id,))
        else:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT required_blood_group, hospital_location
                FROM blood_requests
                WHERE id = ?
            """, (request_id,))
        
        row = cursor.fetchone()
        if not row:
            cursor.close()
            connection.close()
            return redirect(url_for('main_page'))
        
        if db_type == 'mysql':
            request_data = row
        else:
            request_data = {'required_blood_group': row[0], 'hospital_location': row[1]}
        
        nearby_donors, far_donors = find_compatible_donors(
            request_data['required_blood_group'],
            request_data['hospital_location']
        )
        
        cursor.close()
        connection.close()
        
        return render_template('donor_match.html', 
                             nearby_count=len(nearby_donors),
                             far_count=len(far_donors))
    
    except Exception as e:
        print(f"Error fetching donor match: {e}")
        return render_template('donor_match.html', nearby_count=0, far_count=0)


# ==================== API ENDPOINTS ====================

@app.route('/api/register-donor', methods=['POST'])
def register_donor():
    """API endpoint to register a new donor"""
    data = request.json
    
    required_fields = ['name', 'blood_group', 'email', 'phone', 'location']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    db_result = get_db_connection()
    if not db_result:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    db_type, connection = db_result
    
    try:
        cursor = connection.cursor()
        
        if db_type == 'mysql':
            cursor.execute("""
                INSERT INTO donors (name, blood_group, email, phone, location)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['name'], data['blood_group'], data['email'], 
                  data['phone'], data['location']))
        else:
            cursor.execute("""
                INSERT INTO donors (name, blood_group, email, phone, location)
                VALUES (?, ?, ?, ?, ?)
            """, (data['name'], data['blood_group'], data['email'], 
                  data['phone'], data['location']))
        
        connection.commit()
        donor_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'message': 'Donor registered successfully',
            'donor_id': donor_id
        }), 201
    
    except Exception as e:
        error_msg = str(e).lower()
        if 'unique' in error_msg or 'constraint' in error_msg:
            return jsonify({'success': False, 'message': 'Email or phone already registered'}), 400
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/submit-request', methods=['POST'])
def submit_request():
    """API endpoint to submit a blood request"""
    data = request.json
    
    required_fields = ['hospital_name', 'hospital_email', 'hospital_phone', 
                      'hospital_location', 'required_blood_group']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    db_result = get_db_connection()
    if not db_result:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    db_type, connection = db_result
    cursor = None
    
    try:
        cursor = connection.cursor()
        
        if db_type == 'mysql':
            cursor.execute("""
                INSERT INTO blood_requests 
                (hospital_name, hospital_email, hospital_phone, hospital_location, 
                 required_blood_group, patient_details, urgency_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (data['hospital_name'], data['hospital_email'], 
                  data['hospital_phone'], data['hospital_location'],
                  data['required_blood_group'], 
                  data.get('patient_details', ''),
                  data.get('urgency_level', 'normal')))
        else:
            cursor.execute("""
                INSERT INTO blood_requests 
                (hospital_name, hospital_email, hospital_phone, hospital_location, 
                 required_blood_group, patient_details, urgency_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['hospital_name'], data['hospital_email'], 
                  data['hospital_phone'], data['hospital_location'],
                  data['required_blood_group'], 
                  data.get('patient_details', ''),
                  data.get('urgency_level', 'normal')))
        
        request_id = cursor.lastrowid
        connection.commit()
        
        # Find compatible donors
        nearby_donors, far_donors = find_compatible_donors(
            data['required_blood_group'],
            data['hospital_location']
        )
        
        # Prepare request details for notifications
        request_details = {
            'hospital_name': data['hospital_name'],
            'hospital_email': data['hospital_email'],
            'hospital_phone': data['hospital_phone'],
            'hospital_location': data['hospital_location'],
            'blood_group': data['required_blood_group'],
            'patient_details': data.get('patient_details', '')
        }
        
        # Send notifications to nearby donors first (non-blocking)
        notified_count = 0
        try:
            for donor in nearby_donors:
                try:
                    # Try to send email (with timeout protection)
                    email_sent = send_email_notification(donor['email'], donor['name'], request_details)
                    # WhatsApp is non-blocking, just try it
                    send_whatsapp_notification(donor['phone'], donor['name'], request_details)
                    
                    if email_sent:
                        # Record the match
                        if db_type == 'mysql':
                            cursor.execute("""
                                INSERT INTO matches (request_id, donor_id)
                                VALUES (%s, %s)
                            """, (request_id, donor['id']))
                        else:
                            cursor.execute("""
                                INSERT INTO matches (request_id, donor_id)
                                VALUES (?, ?)
                            """, (request_id, donor['id']))
                        notified_count += 1
                except Exception as e:
                    print(f"⚠️  Error notifying donor {donor['name']}: {e}")
                    # Continue with next donor even if one fails
                    continue
        except Exception as e:
            print(f"⚠️  Error in notification loop: {e}")
        
        # Also notify far donors (optional - can be configured)
        try:
            for donor in far_donors[:5]:  # Limit to 5 far donors
                try:
                    send_email_notification(donor['email'], donor['name'], request_details)
                    send_whatsapp_notification(donor['phone'], donor['name'], request_details)
                    
                    # Record match for far donors too
                    if db_type == 'mysql':
                        cursor.execute("""
                            INSERT INTO matches (request_id, donor_id)
                            VALUES (%s, %s)
                        """, (request_id, donor['id']))
                    else:
                        cursor.execute("""
                            INSERT INTO matches (request_id, donor_id)
                            VALUES (?, ?)
                        """, (request_id, donor['id']))
                except Exception as e:
                    print(f"⚠️  Error notifying far donor: {e}")
                    continue
        except Exception as e:
            print(f"⚠️  Error in far donor notification: {e}")
        
        connection.commit()
        
        return jsonify({
            'success': True,
            'message': f'Request submitted successfully. {notified_count} nearby donors notified.',
            'request_id': request_id,
            'nearby_count': len(nearby_donors),
            'far_count': len(far_donors)
        }), 201
    
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        if 'locked' in error_msg:
            return jsonify({'success': False, 'message': 'Database is busy. Please try again in a moment.'}), 503
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        # Always close connections properly
        if cursor:
            cursor.close()
        if connection:
            connection.close()


if __name__ == '__main__':
    # Initialize database on startup
    print("Initializing database...")
    if init_database():
        print("Database initialized successfully!")
    else:
        print("Warning: Database initialization failed. Please check your database connection.")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)

