# Faculty Attendance System Documentation

This document provides an overview of the application structure and detailed setup instructions for Windows and macOS.

## Project Structure

Here is a breakdown of "where everything goes" in the project:

- **`app.py`**: The main entry point of the Flask application. It contains the route definitions, database models, and service logic (Email, Google Drive).
- **`requirements.txt`**: Lists all the Python packages required to run the application.
- **`reset_db.py`**: A utility script to completely reset the database, creating tables and default data (Admin user, Slots).
- **`templates/`**: Contains the HTML files (Jinja2 templates) for the frontend user interface.
- **`static/`**: Contains static assets like CSS files, JavaScript files, and images.
- **`logs/`**: Directory where application log files (`attendance.log`) are stored.
- **`tmp/`**: Used for temporary storage of CSV files generated during attendance saving or bulk imports.
- **`.env`**: Configuration file for environment variables (Database URI, Email credentials, API keys).
- **`service_account.json`**: (Required but not checked in) Google Cloud Service Account credentials for Drive API access.
- **`sample_students.csv`**: A sample CSV file for bulk importing students.

---

## Setup Instructions

### Prerequisites
1.  **Python 3.8+** installed on your system.
2.  **Google Cloud Service Account**:
    -   You need a `service_account.json` file from the Google Cloud Console with Google Drive API enabled.
    -   Place this file in the **root directory** of the project.

### Configuration (`.env`)
Create a file named `.env` in the root directory and add the following variables:

```ini
# Security
SECRET_KEY=your_secure_secret_key

# Database (Default is SQLite if left blank, but app supports PostgreSQL)
SQLALCHEMY_DATABASE_URI=sqlite:///attendance.db

# Email Configuration (for sending absent alerts)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_specific_password

# Google Drive
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
```

---

### Installation & Running (Windows)

1.  **Open PowerShell or Command Prompt** and navigate to the project directory:
    ```powershell
    cd path\to\attendance
    ```

2.  **Create a Virtual Environment**:
    ```powershell
    python -m venv venv
    ```

3.  **Activate the Virtual Environment**:
    ```powershell
    .\venv\Scripts\activate
    ```
    *(You should see `(venv)` appear at the start of your command line)*

4.  **Install Dependencies**:
    ```powershell
    pip install -r requirements.txt
    ```

5.  **Initialize the Database**:
    *   For a fresh start with default data:
        ```powershell
        python reset_db.py
        ```
    *   *Note: `app.py` will also create tables on first run if they don't exist.*

6.  **Run the Application**:
    ```powershell
    python setup_build.py
    ```
    Access the app at `http://127.0.0.1:5000`

---

### Installation & Running (macOS / Linux)

1.  **Open Terminal** and navigate to the project directory:
    ```bash
    cd /path/to/attendance
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    ```

3.  **Activate the Virtual Environment**:
    ```bash
    source venv/bin/activate
    ```
    *(You should see `(venv)` appear at the start of your command line)*

4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Initialize the Database**:
    *   For a fresh start with default data:
        ```bash
        python3 reset_db.py
        ```

6.  **Run the Application**:
    ```bash
    python3 setup_build.py
    ```
    Access the app at `http://127.0.0.1:5000`
