from app import create_app
from extensions import db
from models import Faculty, Slot
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_triggers(db_session):
    """Create database triggers for updating last attendance."""
    db_session.execute(db.text("""
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
    
    db_session.execute(db.text("""
        DROP TRIGGER IF EXISTS trigger_update_last_attendance ON attendance;
        CREATE TRIGGER trigger_update_last_attendance
        AFTER INSERT ON attendance
        FOR EACH ROW
        EXECUTE FUNCTION update_last_attendance();
    """))

def create_admin(db_session):
    """Create the default admin user."""
    admin = Faculty(name='Admin', email='admin@univ.edu', subject='Administration', 
                    password_hash=generate_password_hash('admin123'))
    db_session.add(admin)

app = create_app()

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    
    # Re-create Triggers
    print("Creating triggers...")
    create_triggers(db.session)

    # Create Admin
    print("Creating Admin user...")
    create_admin(db.session)
    
    # Create Default Slots
    print("Creating default slots...")
    slots = [
        Slot(name="7:45-9:35", start_time=datetime.strptime("07:45", "%H:%M").time(), end_time=datetime.strptime("09:35", "%H:%M").time()),
        Slot(name="9:50-11:30", start_time=datetime.strptime("09:50", "%H:%M").time(), end_time=datetime.strptime("11:30", "%H:%M").time()),
        Slot(name="12:10-1:40", start_time=datetime.strptime("12:10", "%H:%M").time(), end_time=datetime.strptime("13:40", "%H:%M").time())
    ]
    db.session.add_all(slots)
    
    db.session.commit()
    print("Database reset complete!")
