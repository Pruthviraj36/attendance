from app import create_app
from models import Faculty
from extensions import db

app = create_app()

with app.app_context():
    faculties = Faculty.query.all()
    print("Current Faculty Subjects:")
    for f in faculties:
        print(f"ID: {f.id}, Name: {f.name}, Subject: '{f.subject}'")
