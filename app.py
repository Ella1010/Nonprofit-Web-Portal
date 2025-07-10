from flask import Flask, render_template, request, redirect, url_for, make_response, session, send_from_directory
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from io import BytesIO
from xhtml2pdf import pisa
from dotenv import load_dotenv
from reportlab.platypus import Paragraph
from flask_mail import Mail, Message
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import flash
from flask import send_file
import secrets
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import uuid
from datetime import datetime, timezone
from werkzeug.utils import secure_filename  # put this at the top of your file if not already
from werkzeug.exceptions import RequestEntityTooLarge


load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 10MB limit


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    flash("Your uploaded file is too large. The limit is 5MB.")
    return redirect(request.referrer or url_for('index')), 413

app.secret_key = os.getenv("SECRET_KEY") or "supersecret"

UPLOAD_DIR = '/mnt/data/uploads'
# UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.")
            return redirect(url_for('login_user'))
        return f(*args, **kwargs)
    return decorated_function

# --- USERS TABLE CREATION (run once in your DB) ---
"""
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    student_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""



# fetches user's existing application
def get_application_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM applications WHERE user_id = %s", (user_id,))
    application = cursor.fetchone()
    conn.close()
    return application

# --- REGISTRATION ROUTE ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = clean_input(request.form.get('email'))
        password = request.form.get('password')
        student_name = clean_input(request.form.get('student_name'))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return render_template("register.html", error="An account with this email already exists.")

        hash_pw = generate_password_hash(password)
        cursor.execute("INSERT INTO users (email, password_hash, student_name) VALUES (%s, %s, %s)", (email, hash_pw, student_name))
        conn.commit()
        conn.close()

        return redirect(url_for('login_user'))

    return render_template("register.html")


# --- APPLICANT LOGIN ROUTE ---



# --- LOGOUT FOR USERS ---
@app.route('/logout_user')
def logout_user():
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('student_name', None)
    return redirect(url_for('login_user'))





# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

mail = Mail(app)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

def clean_input(value):
    if value is None:
        return ""
    return value.replace(u'\xa0', u' ').strip()

def sanitize_ascii(text):
    return text.encode("ascii", errors="ignore").decode()


def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def insert_application(data, grade_report_path=None, optional_upload_path=None, activities=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO applications (
        user_id, student_name, student_gender, dob, email, phone, grade,
        parent_name, parent_contact, school_name, school_location, school_contact,
        teacher_name, teacher_contact, teacher_email, subjects, interests,
        accommodation_required, accommodation_comment,
        essay1, essay2, essay3, optional_info,
        grade_report_path, upload_path
    ) VALUES ( %(user_id)s,
        %(student_name)s, %(student_gender)s, %(dob)s, %(email)s, %(phone)s, %(grade)s,
        %(parent_name)s, %(parent_contact)s, %(school_name)s, %(school_location)s, %(school_contact)s,
        %(teacher_name)s, %(teacher_contact)s, %(teacher_email)s, %(subjects)s, %(interests)s,
        %(accommodation_required)s, %(accommodation_comment)s,
        %(essay1)s, %(essay2)s, %(essay3)s, %(optional_info)s,
        %(grade_report_path)s, %(upload_path)s
    ) RETURNING id
    """, {**data, "grade_report_path": grade_report_path, "upload_path": optional_upload_path})

    application_id = cursor.fetchone()[0]

    if activities:
        max_len = max(
            len(activities.get('types', [])),
            len(activities.get('positions', [])),
            len(activities.get('orgs', [])),
            len(activities.get('descs', []))
        )

        for i in range(max_len):
            type_ = activities['types'][i] if i < len(activities['types']) else ''
            pos = activities['positions'][i] if i < len(activities['positions']) else ''
            org = activities['orgs'][i] if i < len(activities['orgs']) else ''
            desc = activities['descs'][i] if i < len(activities['descs']) else ''

            if any([type_.strip(), pos.strip(), org.strip(), desc.strip()]):
                cursor.execute("""
                    INSERT INTO activities (application_id, activity_type, activity_position, activity_org, activity_desc)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    application_id,
                    type_.strip(),
                    pos.strip(),
                    org.strip(),
                    desc.strip()
                ))

    conn.commit()
    conn.close()


@app.route('/')
@login_required
def index():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM applications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (session["user_id"],))
    application = cursor.fetchone()

    activities = []
    if application:
        cursor.execute("""
            SELECT activity_type, activity_position, activity_org, activity_desc
            FROM activities WHERE application_id = %s
        """, (application['id'],))
        activities = cursor.fetchall()

    conn.close()

    if application and application.get("status") == "submitted":
        return redirect(url_for("dashboard"))

    return render_template('multistep_form.html', draft=application, activities=activities)



@app.route('/submit', methods=['POST'])
@login_required
def submit():

    conn = get_connection()
    cursor = conn.cursor()
    user_id = session["user_id"]

    # Fetch latest application
    cursor.execute("SELECT * FROM applications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))
    app_row = cursor.fetchone()

    if not app_row:

        conn.close()
        return redirect(url_for("index"))


    app_id = app_row[0]

    # Handle file uploads

    grade_file = request.files.get('grade_report')
    grade_path = None
    if grade_file and grade_file.filename:

        filename = f"{uuid.uuid4().hex}_{secure_filename(grade_file.filename)}"
        grade_path = os.path.join(UPLOAD_DIR, filename)
        grade_file.save(grade_path)

    optional_file = request.files.get('upload')
    optional_path = None
    if optional_file and optional_file.filename:
        filename = f"{uuid.uuid4().hex}_{secure_filename(optional_file.filename)}"
        optional_path = os.path.join(UPLOAD_DIR, filename)
        optional_file.save(optional_path)

    # Dynamic activities
    activity_types = request.form.getlist('activity_type[]')
    activity_positions = request.form.getlist('activity_position[]')
    activity_orgs = request.form.getlist('activity_org[]')
    activity_descs = request.form.getlist('activity_desc[]')

    # Insert activities
    cursor.execute("DELETE FROM activities WHERE application_id = %s", (app_id,))
    for i in range(len(activity_types)):
        if activity_types[i].strip():
            cursor.execute("""
                INSERT INTO activities (application_id, activity_type, activity_position, activity_org, activity_desc)
                VALUES (%s, %s, %s, %s, %s)
            """, (app_id, activity_types[i], activity_positions[i], activity_orgs[i], activity_descs[i]))

    # Update application
    cursor.execute("""
        UPDATE applications SET
            student_name = %s,
            student_gender = %s,
            dob = %s,
            email = %s,
            phone = %s,
            grade = %s,
            parent_name = %s,
            parent_contact = %s,
            school_name = %s,
            school_location = %s,
            school_contact = %s,
            teacher_name = %s,
            teacher_contact = %s,
            teacher_email = %s,
            subjects = %s,
            interests = %s,
            accommodation_required = %s,
            accommodation_comment = %s,
            essay1 = %s,
            essay2 = %s,
            essay3 = %s,
            optional_info = %s,
            grade_report_path = %s,
            upload_path = %s,
            status = 'submitted',
            submitted_at = %s


        WHERE id = %s
    """, (
        request.form.get("student_name"),
        request.form.get("student_gender"),
        request.form.get("dob"),
        request.form.get("email"),
        request.form.get("phone"),
        request.form.get("grade"),
        request.form.get("parent_name"),
        request.form.get("parent_contact"),
        request.form.get("school_name"),
        request.form.get("school_location"),
        request.form.get("school_contact"),
        request.form.get("teacher_name"),
        request.form.get("teacher_contact"),
        request.form.get("teacher_email"),
        request.form.get("subjects"),
        request.form.get("interests"),
        request.form.get("accommodation_required"),
        request.form.get("accommodation_comment"),
        request.form.get("essay1"),
        request.form.get("essay2"),
        request.form.get("essay3"),
        request.form.get("optional_info"),
        grade_path,
        optional_path,
        datetime.now(timezone.utc),
        app_id

    ))

    conn.commit()
    conn.close()

    # Send confirmation email
    student_name = request.form.get("student_name")
    user_email = request.form.get("email")
    session["email"] = user_email
    session["student_name"] = student_name

    try:
        msg = Message(
            subject="PEAR Application Received!",
            sender=app.config["MAIL_USERNAME"],
            recipients=[user_email],
            bcc=["admin@pearafrica.org"]
        )
        msg.body = f"""Dear {student_name},

Thank you for applying to the PEAR Summer Program!

Your application has been received. We’ll be in touch once the review process is complete.

Best,
The PEAR Team"""

        msg.html = f"""
        <p>Dear {student_name},</p>
        <p>Thank you for applying to the <strong>PEAR Summer Program!</strong>.</p>
        <p>This email confirms that your application has been received. We’ll be in touch once the review process is complete.</p>
        <p>Best regards,<br>The PEAR Team</p>
        """

        mail.send(msg)
        print("📤 Sending confirmation email to", user_email)

    except Exception as e:
        print("Email failed to send:", e)

    print("✅ Submission complete, redirecting to dashboard")
    return redirect(url_for("dashboard"))






@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Get latest application
    cursor.execute("SELECT * FROM applications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (session['user_id'],))
    application = cursor.fetchone()

    # Fetch related activities
    activities = []
    if application:
        cursor.execute("""
            SELECT activity_type, activity_position, activity_org, activity_desc
            FROM activities WHERE application_id = %s
        """, (application['id'],))
        activities = cursor.fetchall()

    conn.close()

    # Send both application and activities to the template
    return render_template('dashboard.html', application=application, activities=activities)


@app.route('/download_user_pdf/<int:app_id>')
@login_required
def download_user_pdf(app_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch application
    cursor.execute("SELECT * FROM applications WHERE id = %s AND user_id = %s", (app_id, session["user_id"]))
    app_data = cursor.fetchone()

    if not app_data:
        conn.close()
        return "Application not found.", 404

    # Fetch related activities
    cursor.execute("SELECT * FROM activities WHERE application_id = %s", (app_id,))
    activities = cursor.fetchall()

    conn.close()

    # Render PDF with activities injected
    rendered = render_template("submitted_pdf.html", app=app_data, activities=activities)
    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(rendered, dest=pdf)

    if pisa_status.err:
        return "PDF generation error", 500

    pdf.seek(0)
    return send_file(pdf, mimetype='application/pdf', as_attachment=True,
                     download_name='PEAR_Submitted_Application.pdf')




@app.route('/autosave', methods=['POST'])
def autosave():



    user_id = session.get("user_id")

    if not session.get("user_id"):

        return {"error": "Not logged in"}, 401



    fields = [
        "student_name", "student_gender", "dob", "email", "phone", "grade",
        "parent_name", "parent_contact", "school_name", "school_location", "school_contact",
        "teacher_name", "teacher_contact", "teacher_email", "subjects", "interests",
        "accommodation_required", "accommodation_comment",
        "essay1", "essay2", "essay3", "optional_info"
    ]

    data = {f: clean_input(request.form.get(f, '')) for f in fields}

    # Get activity fields
    activity_types = request.form.getlist('activity_type[]')
    activity_positions = request.form.getlist('activity_position[]')
    activity_orgs = request.form.getlist('activity_org[]')
    activity_descs = request.form.getlist('activity_desc[]')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, status FROM applications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))
    existing = cursor.fetchone()



    if existing:
        app_id, status = existing
        if status == "submitted":
            conn.close()
            return {"error": "Application already submitted"}, 403

        # Update application
        update_fields = ", ".join([f"{k} = %s" for k in data.keys()])
        cursor.execute(f"""
            UPDATE applications SET {update_fields}
            WHERE id = %s
        """, list(data.values()) + [app_id])

        # Overwrite activities
        cursor.execute("DELETE FROM activities WHERE application_id = %s", (app_id,))
        for i in range(len(activity_types)):
            if activity_types[i].strip():
                cursor.execute("""
                    INSERT INTO activities (application_id, activity_type, activity_position, activity_org, activity_desc)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    app_id,
                    clean_input(activity_types[i]),
                    clean_input(activity_positions[i]),
                    clean_input(activity_orgs[i]),
                    clean_input(activity_descs[i])
                ))

    else:
        # New draft
        fields_str = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        cursor.execute(f"""
            INSERT INTO applications (user_id, status, {fields_str})
            VALUES (%s, 'incomplete', {placeholders})
            RETURNING id
        """, [user_id] + list(data.values()))

        app_id = cursor.fetchone()[0]

        # Insert new activities
        for i in range(len(activity_types)):
            if activity_types[i].strip():
                cursor.execute("""
                    INSERT INTO activities (application_id, activity_type, activity_position, activity_org, activity_desc)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    app_id,
                    clean_input(activity_types[i]),
                    clean_input(activity_positions[i]),
                    clean_input(activity_orgs[i]),
                    clean_input(activity_descs[i])
                ))

    conn.commit()
    conn.close()
    print("✅ Autosave successful")
    return {"success": True}





# @app.route('/autosave', methods=['POST'])
# def autosave():
#     if not session.get("user_id"):
#         return {"error": "Not logged in"}, 401

#     user_id = session["user_id"]

#     fields = [
#         "student_name", "student_gender", "student_gender_other", "dob", "email", "phone", "grade",
#         "parent_name", "parent_contact", "school_name", "school_location", "school_contact",
#         "teacher_name", "teacher_contact", "teacher_email", "subjects", "interests",
#         "accommodation_required", "accommodation_comment",
#         "essay1", "essay2", "essay3", "optional_info"
#     ]

#     data = {f: clean_input(request.form.get(f, '')) for f in fields}

#     conn = get_connection()
#     cursor = conn.cursor()

#     cursor.execute("SELECT id, status FROM applications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))
#     existing = cursor.fetchone()

#     if existing:
#         app_id, status = existing
#         if status == "submitted":
#             conn.close()
#             return {"error": "Application already submitted"}, 403

#         update_fields = ", ".join([f"{k} = %s" for k in data.keys()])
#         cursor.execute(f"""
#             UPDATE applications SET {update_fields}
#             WHERE id = %s
#         """, list(data.values()) + [app_id])
#     else:
#         fields_str = ", ".join(data.keys())
#         placeholders = ", ".join(["%s"] * len(data))
#         cursor.execute(f"""
#             INSERT INTO applications (user_id, status, {fields_str})
#             VALUES (%s, 'incomplete', {placeholders})
#         """, [user_id] + list(data.values()))

#     conn.commit()
#     conn.close()
#     return {"success": True}




@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')






@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if (
            (email == os.getenv("ADMIN_EMAIL_1") and password == os.getenv("ADMIN_PASS_1"))
        ):
            session["admin"] = True
            return redirect(url_for('admin'))
        else:
            return render_template("login.html", error="Invalid credentials.")

    return render_template("login.html")


@app.route('/admin')
def admin():

    if not session.get("admin"):
        return redirect(url_for("login"))

    status_filter = request.args.get("status")

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if status_filter in ["submitted", "incomplete"]:
        cursor.execute("""
            SELECT * FROM applications
            WHERE status = %s
            ORDER BY submitted_at DESC NULLS LAST, created_at DESC
        """, (status_filter,))
    else:
        cursor.execute("""
            SELECT * FROM applications
            ORDER BY submitted_at DESC NULLS LAST, created_at DESC
        """)
    applications = cursor.fetchall()

    cursor.execute("SELECT * FROM activities")
    activities = cursor.fetchall()

    act_map = defaultdict(list)
    for a in activities:
        act_map[a['application_id']].append(a)

    for app in applications:
        app['activities'] = act_map.get(app['id'], [])

    return render_template('admin.html', rows=applications)

@app.route('/admin/pdf/<int:app_id>')
def download_response_pdf(app_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM applications WHERE id = %s", (app_id,))
    application = cursor.fetchone()

    if not application:
        conn.close()
        return "Application not found", 404

    cursor.execute("SELECT * FROM activities WHERE application_id = %s", (app_id,))
    activities = cursor.fetchall()
    conn.close()

    html = render_template('pdf_template.html', app_data=application, activities=activities, request=request)
    result = BytesIO()
    pisa.CreatePDF(html, dest=result)

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=application_{app_id}.pdf'
    return response

@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        email = clean_input(request.form.get('email'))
        password = request.form.get('password')

        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['student_name'] = user['student_name']
            return redirect(url_for('dashboard'))  # ✅ Go to dashboard

        else:
            return render_template("login_user.html", error="Invalid email or password.")

    return render_template("login_user.html")


@app.route('/logout')
def logout():
    session.clear()  # clears all session data
    return redirect(url_for('login'))

@app.route('/logout_user_dashboard')
def logout_user_dashboard():
    session.clear()
    return redirect(url_for('login_user'))  # 👈 Redirect to login page after logout


# Token Serializer
serializer = URLSafeTimedSerializer(app.secret_key)

# DB connection
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            token = serializer.dumps(email, salt='password-reset')
            link = url_for('reset_password', token=token, _external=True)

            msg = Message( subject="Reset your password", recipients=[email],  sender=app.config["MAIL_USERNAME"])


            msg.body = f"Click here to reset your password: {link}"
            mail.send(msg)
            flash("Reset link sent to your email.", "info")
        else:
            flash("Email not found.", "error")
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        return render_template('reset_password.html', error='Token has expired.')
    except BadSignature:
        return render_template('reset_password.html', error='Invalid or tampered token.')

    if request.method == 'POST':
        new_password = request.form['password']
        hashed = generate_password_hash(new_password)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = %s WHERE email = %s", (hashed, email))
        conn.commit()
        cur.close()
        conn.close()

        flash("Your password has been reset! Please log in.", "success")
        return redirect(url_for('login_user'))

    return render_template('reset_password.html', email=email)

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    if not session.get("admin"):
        return "Unauthorized", 403
    return send_from_directory(UPLOAD_DIR, filename)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
