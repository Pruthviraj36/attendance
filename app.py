import os
import re
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_migrate import Migrate
from flask_talisman import Talisman
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import JSON, cast, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import validates

# Google Drive Imports
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload

# Load Environment Variables
load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

# ==========================================
# EXTENSIONS
# ==========================================
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()

# ==========================================
# SERVICE LOGIC (Consolidated)
# ==========================================

# --- Drive Service ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'service_account.json'

def authenticate_drive():
    creds = None
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        except Exception as e:
            logging.error(f"Failed to load service account: {e}")
    return creds

def get_or_create_folder(service, folder_name, parent_id=None):
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
    except Exception as e:
        logging.error(f"Drive API error: {e}")
        return None

def upload_file_to_drive(file_path, root_folder_id=None):
    # Input validation
    if not isinstance(file_path, str) or not file_path.strip():
        logging.error("file_path must be a non-empty string")
        return None
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return None

    creds = authenticate_drive()
    if not creds:
        logging.warning("No Drive credentials found.")
        return None

    try:
        service = build('drive', 'v3', credentials=creds)
        
        attendance_folder_id = root_folder_id
        if not attendance_folder_id:
            attendance_folder_id = get_or_create_folder(service, 'Attendance')
            
        date_str = datetime.now().strftime('%Y-%m-%d')
        date_folder_id = get_or_create_folder(service, date_str, parent_id=attendance_folder_id)
        
        if not date_folder_id:
             logging.error("Could not create/find date folder")
             return None

        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [date_folder_id]
        }
            
        media = MediaFileUpload(file_path, mimetype='text/csv')
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"Uploaded file ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        logging.error(f"Drive Upload Error: {e}")
        return None

# --- Mail Service ---
def send_absent_email(app, student_email, student_name, enrollment_no, subject, faculty_name, slot, date):
    # Needs app context or passed app object if called from thread
    with app.app_context():
        msg = Message(f"Absent Alert: {subject}",
                      sender=app.config.get('MAIL_USERNAME'),
                      recipients=[student_email])
        
        msg.body = f"""
        Dear {student_name},
        
        You have been marked ABSENT in {subject} by Prof. {faculty_name}.
        
        Enrollment No: {enrollment_no}
        Slot: {slot}
        Date: {date}
        
        If this is a mistake, please contact your faculty immediately.
        """
        
        try:
            mail.send(msg)
            return True
        except Exception as e:
            logging.error(f"Failed to send email to {student_email}: {e}")
            return False

# ==========================================
# MODELS
# ==========================================
class Faculty(UserMixin, db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256))

    @validates('email')
    def validate_email(self, key, value):
        if value and not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError("Invalid email format")
        return value

    def get_id(self):
        return str(self.id)

class Student(db.Model):
    __tablename__ = 'students'
    enrollment_no = db.Column(db.String(50), primary_key=True, unique=True)
    roll_no = db.Column(db.String(50), index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    batch = db.Column(db.String(50))
    semester = db.Column(db.String(10))
    elective_1 = db.Column(db.String(100))
    elective_2 = db.Column(db.String(100))
    extra_fields = db.Column(JSON().with_variant(JSONB, 'postgresql'))

    @validates('email')
    def validate_email(self, key, value):
        if value and not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError("Invalid email format")
        return value

    @validates('roll_no')
    def validate_roll_no(self, key, value):
        if value and not re.match(r'^\d+$', str(value)):
            raise ValueError("Roll number must be numeric")
        return value

class Slot(db.Model):
    __tablename__ = 'slots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    enrollment_no = db.Column(db.String(50), db.ForeignKey('students.enrollment_no'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=datetime.now)
    status = db.Column(db.Enum('P', 'A', name='attendance_status'), nullable=False)

    __table_args__ = (
        db.Index('idx_attendance_composite', 'faculty_id', 'enrollment_no', 'timestamp'),
    )

# ==========================================
# CONSTANTS
# ==========================================
COMPULSORY_SUBJECTS = ['OS', 'ATCC', 'FoA']
ELECTIVE_1_SUBJECTS = ['Information Network Security', 'Machine Learning', 'Machine Learning and DeepLearning']
ELECTIVE_2_SUBJECTS = [
    'Flutter', 
    'Advanced Web Technology', 
    'UI/UX Designing', 
    'Building RESTful APIs with ASP.NET Core (Advanced.NET )', 
    'Advanced .NET Development and Modern Architectures', 
    'Advanced Flutter'
]

# ==========================================
# BACKGROUND TASKS
# ==========================================
def run_async(app, func, *args, **kwargs):
    """Helper to run a function in a thread with application context"""
    try:
        func(app, *args, **kwargs) # Pass app explicitly
    except Exception as e:
        app.logger.error(f"Async task failed: {str(e)}")

def start_background_task(app, func, *args, **kwargs):
    """Starts a background thread"""
    thread = threading.Thread(target=run_async, args=(app, func) + args, kwargs=kwargs)
    thread.start()

def upload_csv_background(app, file_path, folder_id):
    # Drive service doesn't need app context for API calls but logging helps
    with app.app_context():
        upload_file_to_drive(file_path, folder_id)
        # Optional: Remove file after upload
        # if os.path.exists(file_path):
        #     os.remove(file_path)

def send_bulk_emails_background(app, absent_list):
    # absent_list = [{'email': '...', 'name': '...', ...}]
    for student in absent_list:
        try:
             send_absent_email(
                app,
                student['email'],
                student['name'],
                student['enrollment_no'],
                student['subject'],
                student['faculty_name'],
                student['slot'],
                student['date']
            )
        except Exception as e:
            app.logger.error(f"Failed to send email loop: {str(e)}")

def sanitize_enrollment_no(value):
    value = str(value).strip()
    if not re.match(r'^[A-Za-z0-9\-_\s]+$', value):
        raise ValueError("Invalid enrollment number")
    return value

# ==========================================
# APPLICATION FACTORY & ROUTES
# ==========================================
def create_app(test_config=None):
    app = Flask(__name__)
    
    if test_config:
        app.config.from_mapping(test_config)
    else:
        app.config.from_object(Config)

    # Security Headers
    csp = {
        'default-src': '\'self\'',
        'script-src': ['\'self\'', '\'unsafe-inline\'', '\'unsafe-eval\'', 'cdn.jsdelivr.net', 'unpkg.com', 'cdn.tailwindcss.com'],
        'style-src': ['\'self\'', '\'unsafe-inline\'', 'cdn.jsdelivr.net', 'fonts.googleapis.com'],
        'font-src': ['fonts.gstatic.com'],
        'img-src': ['\'self\'', 'data:', '*']
    }
    Talisman(app, content_security_policy=csp, force_https=False) 

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/attendance.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Attendance System startup')
    
    login_manager.login_view = 'login'

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logged = not app.debug
        flash('An internal server error occurred. Please try again later.')
        return render_template('500.html', logged=logged), 500

    @login_manager.user_loader
    def load_user(user_id):
        return Faculty.query.get(int(user_id))

    @app.route('/', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            if current_user.email == 'admin@univ.edu':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('faculty_dashboard'))
            
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            user = Faculty.query.filter_by(email=email).first()

            failed_attempts = session.get('failed_attempts', 0)
            if failed_attempts >= 3:
                flash('Too many failed login attempts. Please wait 5 minutes before trying again.')
                return render_template('login.html')

            if user and check_password_hash(user.password_hash, password):
                session.pop('failed_attempts', None)
                login_user(user)
                if user.email == 'admin@univ.edu':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('faculty_dashboard'))
            else:
                session['failed_attempts'] = failed_attempts + 1
                flash('Invalid email or password')
        
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/faculty')
    @login_required
    def faculty_dashboard():
        slots = Slot.query.all()
        batches = db.session.query(Student.batch).distinct().order_by(Student.batch).all()
        batches = [b[0] for b in batches if b[0]]
        semesters = db.session.query(Student.semester).distinct().order_by(Student.semester).all()
        semesters = [s[0] for s in semesters if s[0]]

        is_elective = current_user.subject in ELECTIVE_1_SUBJECTS or current_user.subject in ELECTIVE_2_SUBJECTS
        return render_template('faculty.html', slots=slots, batches=batches, semesters=semesters, user=current_user, is_elective=is_elective)

    @app.route('/api/students')
    @login_required
    def get_students():
        app.logger.info('API /api/students called with params: %s', dict(request.args))

        query = request.args.get('q', '')
        start_roll = request.args.get('start_roll', '')
        end_roll = request.args.get('end_roll', '')
        
        student_query = Student.query

        if start_roll and end_roll:
            try:
                start = int(start_roll)
                end = int(end_roll)
                student_query = student_query.filter(cast(Student.roll_no, Integer) >= start, cast(Student.roll_no, Integer) <= end)
            except ValueError:
                pass 

        if query:
            student_query = student_query.filter(
                (Student.name.ilike(f'%{query}%')) | 
                (Student.enrollment_no.ilike(f'%{query}%'))
            )
        
        if current_user.subject in COMPULSORY_SUBJECTS:
            pass
        elif current_user.subject in ELECTIVE_1_SUBJECTS:
            student_query = student_query.filter(Student.elective_1 == current_user.subject)
        elif current_user.subject in ELECTIVE_2_SUBJECTS:
            student_query = student_query.filter(Student.elective_2 == current_user.subject)
        
        students = student_query.order_by(cast(Student.roll_no, Integer)).all()
        no_results = len(students) == 0

        return render_template('partials/student_grid.html', students=students, no_results=no_results)

    @app.route('/save_attendance', methods=['POST'])
    @login_required
    def save_attendance_session():
        data = request.json
        students_data = data.get('students') 
        slot_name = data.get('slot_name')
        date_str = datetime.now().strftime('%Y-%m-%d')

        slot = Slot.query.filter_by(name=slot_name).first()
        if not slot:
            return jsonify({'success': False, 'message': 'Invalid slot'}), 400

        records = []
        absent_students = []

        for s_data in students_data:
            enrollment = s_data['enrollment_no']
            status = s_data['status']
            
            student = Student.query.get(enrollment)
            if not student: continue

            records.append({
                'Date': date_str,
                'Faculty': current_user.name,
                'Subject': current_user.subject,
                'Slot': slot_name,
                'Enrollment No': enrollment,
                'Name': student.name,
                'Status': status
            })

            if status == 'A':
                absent_students.append({
                    'email': student.email,
                    'name': student.name,
                    'enrollment_no': enrollment,
                    'subject': current_user.subject,
                    'faculty_name': current_user.name,
                    'slot': slot_name,
                    'date': date_str
                })

            attendance = Attendance(
                faculty_id=current_user.id,
                enrollment_no=enrollment,
                slot_id=slot.id,
                subject=current_user.subject,
                status=status
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        filename = f"{current_user.name}_{date_str}_{slot_name.replace(':', '-')}.csv"
        filepath = os.path.join('tmp', filename)
        os.makedirs('tmp', exist_ok=True)
        pd.DataFrame(records).to_csv(filepath, index=False)
        
        # Async Tasks
        folder_id = app.config.get('GOOGLE_DRIVE_FOLDER_ID')
        real_app = app._get_current_object() if hasattr(app, '_get_current_object') else app
        
        # Pass (app, *args)
        start_background_task(real_app, upload_csv_background, filepath, folder_id)
        start_background_task(real_app, send_bulk_emails_background, absent_students)
        
        return jsonify({'success': True, 'message': 'Attendance saved and processing started.'})

    @app.route('/admin', methods=['GET', 'POST'])
    @login_required
    def admin_dashboard():
        if current_user.email != 'admin@univ.edu':
            return redirect(url_for('faculty_dashboard'))
            
        if request.method == 'POST':
            if 'create_faculty' in request.form:
                name = request.form.get('name')
                email = request.form.get('email')
                subject = request.form.get('subject')
                password = request.form.get('password')
                
                if Faculty.query.filter_by(email=email).first():
                    flash('Email already exists')
                else:
                    new_faculty = Faculty(name=name, email=email, subject=subject, 
                                          password_hash=generate_password_hash(password))
                    db.session.add(new_faculty)
                    db.session.commit()
                    flash('Faculty added successfully')
            
            if 'upload_csv' in request.files:
                file = request.files['upload_csv']
                if file and file.filename.endswith('.csv'):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join('tmp', filename)
                    os.makedirs('tmp', exist_ok=True)
                    file.save(filepath)
                    
                    try:
                        df = pd.read_csv(filepath)
                        df.columns = [c.lower().strip() for c in df.columns]
                        
                        required_cols = ['enrollment_no', 'name']
                        if not all(col in df.columns for col in required_cols):
                            flash('CSV missing required columns: enrollment_no, name')
                        else:
                            std_cols = ['enrollment_no', 'name', 'roll_no', 'email', 'batch', 'semester', 'elective_1', 'elective_2']
                            
                            for _, row in df.iterrows():
                                try:
                                    enrollment = str(row['enrollment_no']).strip()
                                    if not enrollment: continue 
                                except: continue

                                student = Student.query.get(enrollment)
                                if not student:
                                    student = Student(enrollment_no=enrollment, name=row['name'])
                                
                                if 'roll_no' in row and pd.notna(row['roll_no']): student.roll_no = str(int(row['roll_no'])) if isinstance(row['roll_no'], float) else str(row['roll_no'])
                                if 'email' in row and pd.notna(row['email']): student.email = row['email']
                                if 'batch' in row and pd.notna(row['batch']): student.batch = row['batch']
                                if 'semester' in row and pd.notna(row['semester']): student.semester = str(row['semester'])
                                if 'elective_1' in row and pd.notna(row['elective_1']): student.elective_1 = str(row['elective_1'])
                                if 'elective_2' in row and pd.notna(row['elective_2']): student.elective_2 = str(row['elective_2'])
                                
                                extra_data = {}
                                for col in df.columns:
                                    if col not in std_cols:
                                        extra_data[col] = str(row[col])
                                student.extra_fields = extra_data
                                
                                db.session.add(student)
                            
                            db.session.commit()
                            flash('Students imported successfully')
                    except Exception as e:
                        flash(f'Error processing CSV: {str(e)}')
                    finally:
                        if os.path.exists(filepath):
                            os.remove(filepath)

        faculties = Faculty.query.all()
        return render_template('admin.html', faculties=faculties)

    @app.route('/admin/faculty/edit/<int:id>', methods=['POST'])
    @login_required
    def edit_faculty(id):
        if current_user.email != 'admin@univ.edu':
            return redirect(url_for('faculty_dashboard'))
            
        faculty = Faculty.query.get_or_404(id)
        faculty.name = request.form.get('name')
        faculty.email = request.form.get('email')
        faculty.subject = request.form.get('subject')
        
        if request.form.get('password'):
            faculty.password_hash = generate_password_hash(request.form.get('password'))
            
        db.session.commit()
        flash('Faculty updated successfully')
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/faculty/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_faculty(id):
        if current_user.email != 'admin@univ.edu':
            return redirect(url_for('faculty_dashboard'))
            
        faculty = Faculty.query.get_or_404(id)
        db.session.delete(faculty)
        db.session.commit()
        flash('Faculty deleted successfully')
        return redirect(url_for('admin_dashboard'))
        
    with app.app_context():
        db.create_all()
        
        # Create Admin if not exists
        if not Faculty.query.filter_by(email='admin@univ.edu').first():
            admin = Faculty(name='Admin', email='admin@univ.edu', subject='Administration', 
                            password_hash=generate_password_hash('admin123'))
            db.session.add(admin)
            
            # Create default slots
            if not Slot.query.first():
                slots = [
                    Slot(name="7:45-9:35", start_time=datetime.strptime("07:45", "%H:%M").time(), end_time=datetime.strptime("09:35", "%H:%M").time()),
                    Slot(name="9:50-11:30", start_time=datetime.strptime("09:50", "%H:%M").time(), end_time=datetime.strptime("11:30", "%H:%M").time()),
                    Slot(name="12:10-1:40", start_time=datetime.strptime("12:10", "%H:%M").time(), end_time=datetime.strptime("13:40", "%H:%M").time())
                ]
                db.session.add_all(slots)
            
            db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
