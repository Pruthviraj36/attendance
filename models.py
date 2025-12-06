from extensions import db
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class Faculty(UserMixin, db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256))

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
