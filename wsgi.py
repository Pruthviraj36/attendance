import os
from app import create_app
from waitress import serve

app = create_app()

if __name__ == "__main__":
    # Use waitress for Windows production, or gunicorn for Linux
    serve(app, host=os.environ.get('HOST', '0.0.0.0'), port=int(os.environ.get('PORT', '8000')))
