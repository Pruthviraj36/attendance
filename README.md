# Faculty Attendance System Documentation

This document provides an overview of the application structure and detailed setup instructions for Windows and macOS.

## Project Structure

Here is a breakdown of "where everything goes" in the project:

- **`app.py`**: The main entry point of the Flask application. It contains the route definitions, database models, and service logic (Email, Google Drive).
- **`wizard.py`**: An all-in-one CLI tool for setup, configuration, running the app, and git management. (**Start here!**)
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

## ⚡ Quick Start: The Wizard

The easiest way to set up and run the application is using the **setup wizard**.

1.  **Run the Wizard**:
    ```bash
    python wizard.py
    ```
2.  **Choose Option 1** (`First Time Setup`) to automatically:
    -   Install dependencies.
    -   Configure your `.env` file (Database, Email, Drive).
    -   Initialize the database.
3.  **Choose Option 2** (`Run Application`) to start the server.

---

## 🔑 Obtaining Credentials (for `.env`)

Before running the setup, you will need to gather a few keys. The wizard will ask you for these.

### 1. Gmail App Password (Required for Emails)
Since regular passwords don't work with scripts anymore, you need an **App Password**:
1.  Go to [Google Account Security](https://myaccount.google.com/security).
2.  Enable **2-Step Verification** (if not already enabled).
3.  Search for **"App Passwords"** in the top search bar (or find it under 2-Step Verification).
4.  Create a new App Password:
    -   **App**: Mail
    -   **Device**: Other (Name it "Faculty Attendance")
5.  **Copy the 16-character code** (e.g., `abcd efgh ijkl mnop`). This is your `MAIL_PASSWORD`.

### 2. Google Drive Folder ID (Required for Backups)
1.  Open [Google Drive](https://drive.google.com/).
2.  Create a folder (e.g., "Attendance_Backups") or open an existing one.
3.  Look at the URL in your browser address bar:
    `https://drive.google.com/drive/folders/1A2B3C4D5E6F7G8H9I0J`
4.  The last part (`1A2B3C4D5E6F7G8H9I0J`) is your **Folder ID**. Copy it.

### 3. Google Cloud Service Account
1.  You need a `service_account.json` file from the Google Cloud Console.
2.  Ensure the **Google Drive API** is enabled for your project.
3.  Place `service_account.json` in the **root directory** of this project.

---

## 🛠 Manual Setup Instructions

If you prefer to set everything up manually without the wizard:

### Prerequisites
1.  **Python 3.8+** installed.
2.  **Git** installed.

### Configuration (`.env`)
Create a `.env` file and fill in the details (use the credentials obtained above):

```ini
# Security
SECRET_KEY=any_random_string_here

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///attendance.db

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_16_char_app_password

# Google Drive
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
```

### Installation Steps (Windows)

1.  **Create Virtual Environment**:
    ```powershell
    python -m venv venv
    ```
2.  **Activate it**:
    ```powershell
    .\venv\Scripts\activate
    ```
3.  **Install Dependencies**:
    ```powershell
    pip install -r requirements.txt
    ```
4.  **Initialize Database**:
    ```powershell
<<<<<<< HEAD
    python reset_db.py
=======
    python wizard.py
>>>>>>> bd8f019b895f5d3c98a0962a0b585c020f1ad067
    ```
5.  **Run Application**:
    ```powershell
    python wizard.py
    ```

### Installation Steps (macOS / Linux)

1.  **Create Custom Environment**:
    ```bash
    python3 -m venv venv
    ```
2.  **Activate it**:
    ```bash
    source venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Initialize Database**:
    ```bash
<<<<<<< HEAD
    python3 reset_db.py
=======
    python3 wizard.py
>>>>>>> bd8f019b895f5d3c98a0962a0b585c020f1ad067
    ```
5.  **Run Application**:
    ```bash
    python3 wizard.py
    ```

Access the app at `http://127.0.0.1:5000`
