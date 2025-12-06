from flask_mail import Message
from extensions import mail
from flask import current_app

def send_absent_email(student_email, student_name, enrollment_no, subject, faculty_name, slot, date):
    msg = Message(f"Absent Alert: {subject}",
                  sender=current_app.config['MAIL_USERNAME'],
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
        print(f"Failed to send email to {student_email}: {e}")
        return False
