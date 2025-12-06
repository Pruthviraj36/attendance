import os
import subprocess
import sys
import shutil
import time

# --- ANSI Colors for "Kali Style" ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    # A bit of ASCII art style
    print(Colors.FAIL + Colors.BOLD)
    print(r"""
      █████╗ ████████╗████████╗███████╗███╗   ██╗██████╗  █████╗ ███╗   ██╗██╗  ██╗
     ██╔══██╗╚══██╔══╝╚══██╔══╝██╔════╝████╗  ██║██╔══██╗██╔══██╗████╗  ██║██║  ██║
     ███████║   ██║      ██║   █████╗  ██╔██╗ ██║██║  ██║███████║██╔██╗ ██║██║  ██║
     ██╔══██║   ██║      ██║   ██╔══╝  ██║╚██╗██║██║  ██║██╔══██║██║╚██╗██║██║  ██║
     ██║  ██║   ██║      ██║   ███████╗██║ ╚████║██████╔╝██║  ██║██║ ╚████║╚█████╔╝
     ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚════╝ 
                                [ BUILDER & LAUNCHER ]
    """ + Colors.ENDC)
    print(Colors.BLUE + "    [*] Faculty Attendance System v2.0" + Colors.ENDC)
    print(Colors.BLUE + "    [*] Mode: Standalone Executable" + Colors.ENDC)
    print(Colors.BLUE + "    [*] Target: Windows .exe" + Colors.ENDC)
    print("-" * 70)
    print()

def log(msg, type="INFO"):
    if type == "INFO":
        print(f"{Colors.BLUE}[*]{Colors.ENDC} {msg}")
    elif type == "SUCCESS":
        print(f"{Colors.GREEN}[+]{Colors.ENDC} {msg}")
    elif type == "WARN":
        print(f"{Colors.WARNING}[!]{Colors.ENDC} {msg}")
    elif type == "ERROR":
        print(f"{Colors.FAIL}[-]{Colors.ENDC} {msg}")
    elif type == "INPUT":
        print(f"{Colors.CYAN}[?]{Colors.ENDC} {msg}", end="")

def install_requirements():
    log("Checking and installing dependencies...", "INFO")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        log("Dependencies installed successfully.", "SUCCESS")
    except subprocess.CalledProcessError:
        log("Failed to install dependencies.", "ERROR")
        sys.exit(1)

def get_env_input(key, current_val, secret=False):
    prompt_text = f"Set {key}"
    if current_val:
        display_val = "****" if secret and current_val else current_val
        prompt_text += f" [{display_val}]: "
    else:
        prompt_text += ": "
    
    print(f"{Colors.CYAN}[?]{Colors.ENDC} {prompt_text}", end="")
    val = input().strip()
    
    if not val:
        return current_val
    return val

def load_env_file(filepath='.env'):
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    env_vars[key] = val
    return env_vars

def save_env_file(env_vars, filepath='.env'):
    with open(filepath, 'w') as f:
        for key, val in env_vars.items():
            f.write(f"{key}={val}\n")
    log(f"Configuration saved to {filepath}", "SUCCESS")

def build_executable():
    print()
    log("Initializing Build Process...", "INFO")
    time.sleep(1)
    
    # Clean previous build
    if os.path.exists('build'): shutil.rmtree('build')
    if os.path.exists('dist'): shutil.rmtree('dist')
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', 'FacultyAttendance',
        '--onefile',
        '--clean',
        '--add-data', 'templates;templates',
        '--add-data', 'static;static',
        '--add-data', '.env;.',
        'app.py'
    ]
    
    if os.path.exists('service_account.json'):
         log("Detected service_account.json, bundling...", "INFO")
         cmd.extend(['--add-data', 'service_account.json;.'])

    log("Running PyInstaller (this might take a minute)...", "INFO")
    try:
        # Run silent to enable custom spinner/logs or just let it run
        # Using subprocess.run to allow output streaming if needed, but standard call is fine
        subprocess.check_call(cmd)
        print()
        log("Build Successfully Completed!", "SUCCESS")
        return True
    except subprocess.CalledProcessError:
        log("Build Failed.", "ERROR")
        return False

def main():
    # enable colors in windows terminal
    os.system("") 
    
    clear_screen()
    print_banner()
    
    # Step 1: Install Requirements
    log("Phase 1: Dependency Check", "INFO")
    install_requirements()
    print("-" * 70)
    
    # Step 2: Config
    log("Phase 2: Configuration", "INFO")
    current_env = load_env_file()
    new_env = {}
    
    new_env['SECRET_KEY'] = get_env_input('SECRET_KEY', current_env.get('SECRET_KEY', 'default-secret-key'))
    
    # Database
    default_db = 'sqlite:///attendance.db'
    new_env['SQLALCHEMY_DATABASE_URI'] = get_env_input('SQLALCHEMY_DATABASE_URI', current_env.get('SQLALCHEMY_DATABASE_URI', default_db))
    
    # Email
    print(f"\n{Colors.WARNING}--- Gmail App Password Settings ---{Colors.ENDC}")
    new_env['MAIL_SERVER'] = 'smtp.gmail.com'
    new_env['MAIL_PORT'] = '587'
    new_env['MAIL_USE_TLS'] = 'True'
    new_env['MAIL_USERNAME'] = get_env_input('MAIL_USERNAME', current_env.get('MAIL_USERNAME'))
    new_env['MAIL_PASSWORD'] = get_env_input('MAIL_PASSWORD', current_env.get('MAIL_PASSWORD'), secret=True)
    
    # External
    print(f"\n{Colors.WARNING}--- Google Drive Integration ---{Colors.ENDC}")
    new_env['GOOGLE_DRIVE_FOLDER_ID'] = get_env_input('GOOGLE_DRIVE_FOLDER_ID', current_env.get('GOOGLE_DRIVE_FOLDER_ID'))
    
    save_env_file(new_env)
    print("-" * 70)

    # Step 3: Build
    log("Phase 3: Building Executable", "INFO")
    input(f"{Colors.BLUE}[*]{Colors.ENDC} Press Enter to start compilation...")
    
    if build_executable():
        exe_path = os.path.join(os.getcwd(), 'dist', 'FacultyAttendance.exe')
        print("-" * 70)
        log(f"Executable available at: {Colors.BOLD}{exe_path}{Colors.ENDC}", "SUCCESS")
        
        # Step 4: Run
        print(f"\n{Colors.CYAN}[?]{Colors.ENDC} Launch Application now? (Y/n): ", end="")
        choice = input().lower().strip()
        if choice in ['y', 'yes', '']:
            log("Launching...", "INFO")
            subprocess.Popen([exe_path], creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    main()
