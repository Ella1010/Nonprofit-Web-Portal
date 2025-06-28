from flask import Flask, render_template, request, redirect, url_for, make_response, session
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from io import BytesIO
from xhtml2pdf import pisa
from dotenv import load_dotenv
from reportlab.platypus import Paragraph
from flask_mail import Mail, Message
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "supersecret"



# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
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
        student_name, student_gender, student_gender_other, dob, email, phone, grade,
        parent_name, parent_contact, school_name, school_location, school_contact,
        teacher_name, teacher_contact, teacher_email, subjects, interests,
        accommodation_required, accommodation_comment,
        essay1, essay2, essay3, optional_info,
        grade_report_path, upload_path
    ) VALUES (
        %(student_name)s, %(student_gender)s, %(student_gender_other)s, %(dob)s, %(email)s, %(phone)s, %(grade)s,
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
def index():
    return render_template('multistep_form.html')

@app.route('/submit', methods=['POST'])
def submit():
    activity_types = request.form.getlist('activity_type[]')
    activity_positions = request.form.getlist('activity_position[]')
    activity_orgs = request.form.getlist('activity_org[]')
    activity_descs = request.form.getlist('activity_desc[]')
    activities = {
    'types': [clean_input(x) for x in activity_types],
    'positions': [clean_input(x) for x in activity_positions],
    'orgs': [clean_input(x) for x in activity_orgs],
    'descs': [clean_input(x) for x in activity_descs]
    }

    fields = ["student_name", "student_gender", "student_gender_other", "dob", "email", "phone", "grade",
              "parent_name", "parent_contact", "school_name", "school_location", "school_contact",
              "teacher_name", "teacher_contact", "teacher_email", "subjects", "interests",
              "accommodation_required", "accommodation_comment", "essay1", "essay2", "essay3", "optional_info"]

    data = {f: clean_input(request.form.get(f, '')) for f in fields}

    os.makedirs('static/uploads', exist_ok=True)

    grade_file = request.files.get('grade_report')
    grade_path = None
    if grade_file and grade_file.filename:
        grade_path = f"static/uploads/{grade_file.filename}"
        grade_file.save(grade_path)

    optional_file = request.files.get('upload')
    optional_path = None
    if optional_file and optional_file.filename:
        optional_path = f"static/uploads/{optional_file.filename}"
        optional_file.save(optional_path)

    insert_application(data, grade_path, optional_path, activities)

    user_email = clean_input(data["email"])
    student_name = clean_input(data["student_name"])
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

    Thank you for applying to the PEAR Summer Program!.

    Your application has been received. We’ll be in touch once the review process is complete.

    Best,
    The PEAR Team"""
        # HTML version
        msg.html = f"""
    <p>Dear {student_name},</p>
    <p>Thank you for applying to the <strong>PEAR Summer Program!</strong>.</p>
    <p>This email confirms that your application has been received. We’ll be in touch once the review process is complete.</p>
    <p>Best regards,<br>The PEAR Team</p>
    """

        mail.send(msg)

    except Exception as e:
        print("Email failed to send:", e)


    return redirect(url_for('confirmation'))


@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/admin')
def admin():

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM applications")
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

@app.route('/logout')
def logout():
    session.clear()  # clears all session data
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
