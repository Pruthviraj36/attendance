from app import create_app
from models import Faculty, Student
from extensions import db

app = create_app()

SUBJECT_MAPPING = {
    'MLDL': 'Machine Learning and DeepLearning',
    'ML': 'Machine Learning',
    'INS': 'Information Network Security',
    'AWT': 'Advanced Web Technology',
    'UI/UX': 'UI/UX Designing',
    'ASP DOTNET CORE': 'Building RESTful APIs with ASP.NET Core (Advanced.NET )',
    'ADV. DOTNET': 'Advanced .NET Development and Modern Architectures',
    'FLUTTER': 'Flutter',
    'ADVANCE FLUTTER': 'Advanced Flutter'
}

with app.app_context():
    print("Migrating Faculty Subjects...")
    faculties = Faculty.query.all()
    for f in faculties:
        if f.subject in SUBJECT_MAPPING:
            print(f"Updating Faculty {f.name}: {f.subject} -> {SUBJECT_MAPPING[f.subject]}")
            f.subject = SUBJECT_MAPPING[f.subject]
    
    # Also define a reverse mapping or check for students if needed
    # Assuming students might not have electives set yet, but if they do:
    print("Migrating Student Electives...")
    students = Student.query.all()
    for s in students:
        changed = False
        if s.elective_1 in SUBJECT_MAPPING:
            print(f"Updating Student {s.name} Elective 1: {s.elective_1} -> {SUBJECT_MAPPING[s.elective_1]}")
            s.elective_1 = SUBJECT_MAPPING[s.elective_1]
            changed = True
        if s.elective_2 in SUBJECT_MAPPING:
            print(f"Updating Student {s.name} Elective 2: {s.elective_2} -> {SUBJECT_MAPPING[s.elective_2]}")
            s.elective_2 = SUBJECT_MAPPING[s.elective_2]
            changed = True
        
        if changed:
            db.session.add(s)

    db.session.commit()
    print("Migration Complete.")
