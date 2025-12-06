from extensions import celery
from drive_service import upload_file_to_drive
from mail_service import send_absent_email
from flask import current_app
import os

@celery.task
def upload_csv_task(file_path, folder_id):
    upload_file_to_drive(file_path, folder_id)
    # Optional: Remove file after upload
    # os.remove(file_path)

@celery.task
def send_bulk_emails_task(absent_list):
    # absent_list = [{'email': '...', 'name': '...', ...}]
    with celery.app.app_context():
        for student in absent_list:
            send_absent_email(
                student['email'],
                student['name'],
                student['enrollment_no'],
                student['subject'],
                student['faculty_name'],
                student['slot'],
                student['date']
            )
