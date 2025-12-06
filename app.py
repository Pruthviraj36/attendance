from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from config import Config
from extensions import db, login_manager, mail, celery, migrate
from models import Faculty, Student, Slot, Attendance
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
import os
import logging
from logging.handlers import RotatingFileHandler
from flask_talisman import Talisman
from datetime import datetime
from celery_tasks import upload_csv_task, send_bulk_emails_task
from sqlalchemy import cast, Integer
import re

def sanitize_enrollment_no(value):
    value = str(value).strip()
    if not re.match(r'^[A-Za-z0-9\-_\s]+$', value):
        raise ValueError("Invalid enrollment number")
    return value

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Security Headers
    csp = {
        'default-src': '\'self\'',
        'script-src': ['\'self\'', '\'unsafe-inline\'', '\'unsafe-eval\'', 'cdn.jsdelivr.net', 'unpkg.com', 'cdn.tailwindcss.com'],
        'style-src': ['\'self\'', '\'unsafe-inline\'', 'cdn.jsdelivr.net'],
        'img-src': ['\'self\'', 'data:', '*']
    }
    Talisman(app, content_security_policy=csp, force_https=False) # Set force_https=True in real prod with SSL

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    
    # Logging Configuration
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/attendance.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Attendance System startup')
    
    # Celery config update
    celery.conf.update(app.config)

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
            if current_user.email == 'admin@univ.edu': # Simple admin check
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
                session.pop('failed_attempts', None)  # Reset on success
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

    @app.route('/admin', methods=['GET', 'POST'])
    @login_required
    def admin_dashboard():
        if current_user.email != 'admin@univ.edu':
            return redirect(url_for('faculty_dashboard'))
            
        if request.method == 'POST':
            # Handle Faculty Creation
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
            
            # Handle CSV Upload
            if 'upload_csv' in request.files:
                file = request.files['upload_csv']
                if file and file.filename.endswith('.csv'):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join('tmp', filename)
                    os.makedirs('tmp', exist_ok=True)
                    file.save(filepath)
                    
                    try:
                        df = pd.read_csv(filepath)
                        # Normalize columns
                        df.columns = [c.lower().strip() for c in df.columns]
                        
                        required_cols = ['enrollment_no', 'name', 'roll_no']
                        if not all(col in df.columns for col in required_cols):
                            flash('Missing required columns: enrollment_no, name, roll_no')
                        else:
                            # Dynamic JSONB fields
                            std_cols = ['enrollment_no', 'name', 'roll_no', 'email', 'batch', 'semester']
                            extra_cols = [c for c in df.columns if c not in std_cols]
                            
                            for _, row in df.iterrows():
                                extra_data = {col: row[col] for col in extra_cols}
                                enrollment_no = sanitize_enrollment_no(row['enrollment_no'])
                                student = Student.query.get(enrollment_no)
                                if not student:
                                    student = Student(enrollment_no=enrollment_no)

                                student.name = row['name']
                                student.roll_no = str(row['roll_no'])
                                student.email = row.get('email')
                                student.batch = row.get('batch')
                                student.semester = str(row.get('semester', ''))
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

    @app.route('/faculty')
    @login_required
    def faculty_dashboard():
        slots = Slot.query.all()
        # Fetch unique batches
        batches = db.session.query(Student.batch).distinct().order_by(Student.batch).all()
        batches = [b[0] for b in batches if b[0]] # Flatten and remove None
        # Fetch unique semesters
        semesters = db.session.query(Student.semester).distinct().order_by(Student.semester).all()
        semesters = [s[0] for s in semesters if s[0]] # Flatten and remove None

        return render_template('faculty.html', slots=slots, batches=batches, semesters=semesters, user=current_user)

    @app.route('/api/students')
    @login_required
    def get_students():
        app.logger.info('API /api/students called with params: %s', dict(request.args))

        # Search functionality
        query = request.args.get('q', '')
        start_roll = request.args.get('start_roll', '')
        end_roll = request.args.get('end_roll', '')
        batch = request.args.get('batch', '')
        semester = request.args.get('semester', '')

        student_query = Student.query

        if start_roll and end_roll:
            try:
                start = int(start_roll)
                end = int(end_roll)
                # Cast roll_no to Integer for numeric comparison
                student_query = student_query.filter(
                    cast(Student.roll_no, Integer) >= start,
                    cast(Student.roll_no, Integer) <= end
                )
                app.logger.info('Filtering by roll range: %s to %s', start, end)
            except ValueError:
                app.logger.warning('Invalid roll range: start=%s, end=%s', start_roll, end_roll)
                pass # Handle non-integer inputs gracefully

        if batch:
            student_query = student_query.filter(Student.batch == batch)
            app.logger.info('Filtering by batch: %s', batch)

        if semester:
            student_query = student_query.filter(Student.semester == semester)
            app.logger.info('Filtering by semester: %s', semester)

        if query:
            student_query = student_query.filter(
                (Student.enrollment_no.ilike(f'%{query}%')) |
                (Student.roll_no.ilike(f'%{query}%')) |
                (Student.name.ilike(f'%{query}%'))
            )
            app.logger.info('Filtering by query: %s', query)

        # Default loading: if no filters, load all students
        students = student_query.order_by(cast(Student.roll_no, Integer)).all()

        app.logger.info('Found %d students', len(students))

        # Error handling for empty results
        no_results = len(students) == 0

        return render_template('partials/student_grid.html', students=students, no_results=no_results)

    @app.route('/api/attendance', methods=['POST'])
    @login_required
    def mark_attendance():
        data = request.json
        enrollment_no = data.get('enrollment_no')
        status = data.get('status') # 'P' or 'A'
        slot_id = data.get('slot_id')
        
        # Logic to save/update attendance
        # This is a simplified example, you'd likely want to batch this or handle it more robustly
        
        return jsonify({'success': True})

    @app.route('/save_attendance', methods=['POST'])
    @login_required
    def save_attendance_session():
        # Generate CSV of current session
        data = request.json
        students_data = data.get('students') # List of {enrollment_no, status}
        slot_name = data.get('slot_name')
        date_str = datetime.now().strftime('%Y-%m-%d')
    
        app.logger.info('save_attendance payload: %s', data)

        # Get slot_id from slot_name
        slot = Slot.query.filter_by(name=slot_name).first()
        if not slot:
            app.logger.error('Slot not found: %s', slot_name)
            return jsonify({'success': False, 'message': f'Slot {slot_name} not found'})
        slot_id = slot.id
        app.logger.info('Resolved slot_name=%s to slot_id=%s', slot_name, slot_id)
        
        # Create DataFrame
        records = []
        absent_students = []
        
        for s in students_data:
            enrollment_no = s['enrollment_no']
            status = s['status']
            app.logger.info('Processing student enrollment_no=%s, status=%s', enrollment_no, status)
            student = Student.query.get(enrollment_no)
            if not student:
                app.logger.error('Student not found for enrollment_no=%s', enrollment_no)
                continue
            app.logger.info('Found student: enrollment_no=%s, roll_no=%s, name=%s', student.enrollment_no, student.roll_no, student.name)
            records.append({
                'enrollment_no': student.enrollment_no,
                'roll_no': student.roll_no,
                'name': student.name,
                'status': status,
                'date': date_str,
                'slot': slot_name,
                'subject': current_user.subject
            })
    
            if status == 'A' and student.email:
                absent_students.append({
                    'email': student.email,
                    'name': student.name,
                    'enrollment_no': student.enrollment_no,
                    'subject': current_user.subject,
                    'faculty_name': current_user.name,
                    'slot': slot_name,
                    'date': date_str
                })
    
            # Save to DB
            att = Attendance(
                faculty_id=current_user.id,
                enrollment_no=student.enrollment_no,
                slot_id=slot_id,
                subject=current_user.subject,
                status=status
            )
            db.session.add(att)
    
        app.logger.info('Processed %d students, %d attendance records added', len(students_data), len(records))
        db.session.commit()
        
        # Generate CSV
        filename = f"{current_user.name}_{date_str}_{slot_name.replace(':', '-')}.csv"
        filepath = os.path.join('tmp', filename)
        os.makedirs('tmp', exist_ok=True)
        pd.DataFrame(records).to_csv(filepath, index=False)
        
        # Trigger Async Tasks
        folder_id = app.config.get('GOOGLE_DRIVE_FOLDER_ID')
        upload_csv_task.delay(filepath, folder_id)
        send_bulk_emails_task.delay(absent_students)
        
        return jsonify({'success': True, 'message': 'Attendance saved and processing started.'})

    with app.app_context():
        db.create_all()
        
        # Ensure extra_fields column exists (Auto-migration)
        try:
            db.session.execute(db.text("ALTER TABLE students ADD COLUMN IF NOT EXISTS extra_fields JSONB;"))
            db.session.commit()
        except Exception as e:
            app.logger.warning(f"Could not alter table: {e}")
            db.session.rollback()

        # Create Trigger Function and Trigger
        db.session.execute(db.text("""
            CREATE OR REPLACE FUNCTION update_last_attendance()
            RETURNS TRIGGER AS $$
            BEGIN
                UPDATE students 
                SET extra_fields = jsonb_set(COALESCE(extra_fields, '{}'::jsonb), '{last_attendance}', to_jsonb(NEW.timestamp))
                WHERE enrollment_no = NEW.enrollment_no;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        db.session.execute(db.text("""
            DROP TRIGGER IF EXISTS trigger_update_last_attendance ON attendance;
            CREATE TRIGGER trigger_update_last_attendance
            AFTER INSERT ON attendance
            FOR EACH ROW
            EXECUTE FUNCTION update_last_attendance();
        """))
        db.session.commit()

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
    app.run() # Debug is controlled by env or config now
