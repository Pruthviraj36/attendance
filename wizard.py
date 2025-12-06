import os
import subprocess
import sys
import shutil
import time
import getpass

# --- ANSI Colors ---
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
    print(Colors.HEADER + Colors.BOLD)
    print(r"""
      █████╗ ████████╗████████╗███████╗███╗   ██╗██████╗  █████╗ ███╗   ██╗
     ██╔══██╗╚══██╔══╝╚══██╔══╝██╔════╝████╗  ██║██╔══██╗██╔══██╗████╗  ██║
     ███████║   ██║      ██║   █████╗  ██╔██╗ ██║██║  ██║███████║██╔██╗ ██║
     ██╔══██║   ██║      ██║   ██╔══╝  ██║╚██╗██║██║  ██║██╔══██║██║╚██╗██║
     ██║  ██║   ██║      ██║   ███████╗██║ ╚████║██████╔╝██║  ██║██║ ╚████║
     ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝
    """ + Colors.ENDC)
    print(Colors.CYAN + "    [*] Faculty Attendance System - Management Wizard" + Colors.ENDC)
    print("-" * 70)

def log(msg, type="INFO"):
    if type == "INFO": print(f"{Colors.BLUE}[*]{Colors.ENDC} {msg}")
    elif type == "SUCCESS": print(f"{Colors.GREEN}[+]{Colors.ENDC} {msg}")
    elif type == "WARN": print(f"{Colors.WARNING}[!]{Colors.ENDC} {msg}")
    elif type == "ERROR": print(f"{Colors.FAIL}[-]{Colors.ENDC} {msg}")

def install_requirements():
    log("Checking Python dependencies...", "INFO")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        log("Dependencies are installed.", "SUCCESS")
    except:
        log("Failed to install dependencies.", "ERROR")

def setup_configuration():
    print(f"\n{Colors.BOLD}--- Configuration Wizard ---{Colors.ENDC}")
    log("We will set up your environment variables now.", "INFO")
    
    current_config = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    current_config[k] = v

    def prompt(key, default, is_secret=False):
        current_val = current_config.get(key, default)
        display_val = '********' if is_secret and current_val else current_val
        val = input(f"{Colors.CYAN}[?]{Colors.ENDC} {key} [{display_val}]: ").strip()
        return val if val else current_val

    config = {}
    config['SECRET_KEY'] = prompt("SECRET_KEY", "force-change-this-key", is_secret=True)
    config['SQLALCHEMY_DATABASE_URI'] = prompt("DATABASE_URI", "sqlite:///attendance.db")
    
    print(f"\n{Colors.WARNING}Gmail Settings (Required for absent alerts){Colors.ENDC}")
    config['MAIL_SERVER'] = 'smtp.gmail.com'
    config['MAIL_PORT'] = '587'
    config['MAIL_USE_TLS'] = 'True'
    config['MAIL_USERNAME'] = prompt("MAIL_USERNAME", "")
    config['MAIL_PASSWORD'] = prompt("MAIL_PASSWORD", "", is_secret=True)
    
    print(f"\n{Colors.WARNING}Google Drive (Required for backups){Colors.ENDC}")
    config['GOOGLE_DRIVE_FOLDER_ID'] = prompt("GOOGLE_DRIVE_FOLDER_ID", "")

    with open('.env', 'w') as f:
        for k, v in config.items():
            f.write(f"{k}={v}\n")
    log("Configuration saved to .env", "SUCCESS")

def init_database():
    log("Initializing Database...", "INFO")
    try:
        subprocess.run([sys.executable, 'reset_db.py'], check=True)
        log("Database initialized successfully (Tables created, Admin added).", "SUCCESS")
    except:
        log("Failed to initialize database.", "ERROR")

def check_git_installed():
    try:
        subprocess.check_call(['git', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def git_wizard():
    print()
    log("Starting Git Repository Setup Wizard...", "INFO")
    
    if not check_git_installed():
        log("Git is not installed or not found in PATH.", "ERROR")
        return

    # Check if .git exists
    if not os.path.exists('.git'):
        log("Git repository not initialized. Initializing now...", "WARN")
        subprocess.check_call(['git', 'init'])
        
    # Check remote
    try:
        remote_output = subprocess.check_output(['git', 'remote', '-v']).decode()
        if 'origin' in remote_output:
            log("Remote 'origin' already exists.", "INFO")
            print(f"{Colors.WARNING}Current Remote:{Colors.ENDC}\n{remote_output.strip()}")
            
            print(f"\n{Colors.CYAN}[?]{Colors.ENDC} Do you want to change the remote URL? (y/N): ", end="")
            if input().lower().strip() == 'y':
                print(f"{Colors.CYAN}[?]{Colors.ENDC} Enter new Repository URL: ", end="")
                new_url = input().strip()
                if new_url:
                    subprocess.check_call(['git', 'remote', 'set-url', 'origin', new_url])
                    log("Remote updated.", "SUCCESS")
        else:
            print(f"{Colors.CYAN}[?]{Colors.ENDC} Enter Repository URL (e.g., https://github.com/user/repo.git): ", end="")
            repo_url = input().strip()
            if repo_url:
                subprocess.check_call(['git', 'remote', 'add', 'origin', repo_url])
                log("Remote added.", "SUCCESS")
            else:
                log("No URL provided. Skipping upload.", "WARN")
                return

        # Prepare for push
        log("Preparing to push code...", "INFO")
        
        # Ensure ignoring is correct
        if not os.path.exists('.gitignore'):
            log("No .gitignore found! Creating one...", "WARN")
            with open('.gitignore', 'w') as f:
                f.write("venv/\n__pycache__/\n*.pyc\n.env\nbuild/\ndist/\n")
        
        subprocess.check_call(['git', 'add', '.'])
        
        log("Committing changes...", "INFO")
        try:
            subprocess.check_call(['git', 'commit', '-m', 'Update via Wizard'])
        except subprocess.CalledProcessError:
            log("Nothing to commit (clean working tree).", "INFO")

        current_branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip() or 'master'
        
        log(f"Pushing to origin/{current_branch}...", "INFO")
        try:
            subprocess.check_call(['git', 'push', '-u', 'origin', current_branch])
            log("Code successfully uploaded to Git!", "SUCCESS")
        except subprocess.CalledProcessError:
             log("Push failed. Trying to force push (fixing history issues)...", "WARN")
             try:
                 subprocess.check_call(['git', 'push', '-u', 'origin', current_branch, '--force'])
                 log("Force push successful! Repo is clean.", "SUCCESS")
             except subprocess.CalledProcessError:
                 log("Push failed. Check your internet or permissions.", "ERROR")

    except Exception as e:
        log(f"An unexpected error occurred: {e}", "ERROR")

def main_menu():
    while True:
        clear_screen()
        print_banner()
        print(f"{Colors.BOLD}1.{Colors.ENDC} ⚡ First Time Setup (Install + Config + DB)")
        print(f"{Colors.BOLD}2.{Colors.ENDC} 🚀 Run Application")
        print(f"{Colors.BOLD}3.{Colors.ENDC} 🔧 Configuration Only (.env)")
        print(f"{Colors.BOLD}4.{Colors.ENDC} 💾 Build Executable (exe)")
        print(f"{Colors.BOLD}5.{Colors.ENDC} ☁️  Git Upload / Fix")
        print(f"{Colors.BOLD}6.{Colors.ENDC} Exit")
        print("-" * 70)
        
        choice = input(f"{Colors.CYAN}[?]{Colors.ENDC} Select option: ").strip()
        
        if choice == '1':
            install_requirements()
            setup_configuration()
            init_database()
            input("\nSetup Complete! Press Enter to return...")
        elif choice == '2':
            os.system(f"{sys.executable} app.py")
        elif choice == '3':
            setup_configuration()
        elif choice == '4':
            os.system(f"{sys.executable} setup_build.py")
        elif choice == '5':
            git_wizard()
            input("\nPress Enter to return...")
        elif choice == '6':
            break

if __name__ == "__main__":
    main_menu()
