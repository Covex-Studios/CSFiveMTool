import sys
import os
import json
import subprocess
import webbrowser
import re
import requests

from PyQt6.QtWidgets import (
    QApplication, QWidget, QListWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

# ---------------- app metadata ----------------

APP_NAME = "CS FiveM Management Tool"
APP_PUBLISHER = "Covex Studios"
APP_VERSION = "1.0.0"

# GitHub URLs – update these to match your repo
# version.json in your repo root:
# {
#   "version": "1.0.0"
# }
UPDATE_JSON_URL = "https://raw.githubusercontent.com/Covex-Studios/CSFiveMTool/main/version.json"

# Releases page (for manual viewing if needed)
RELEASE_PAGE_URL = "https://github.com/Covex-Studios/CSFiveMTool/releases"

# Direct link to latest installer .exe (uploaded in Releases)
INSTALLER_DOWNLOAD_URL = "https://github.com/Covex-Studios/CSFiveMTool/releases/latest/download/CSFiveMToolSetup.exe"

DB_FILE = "servers.json"


# ---------------- config IO ----------------

def load_servers():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_servers(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def find_server(servers, name_or_key: str):
    target = name_or_key.strip().lower()
    for s in servers:
        if s["key"].lower() == target or s["name"].strip().lower() == target:
            return s
    return None


# ---------------- BAT generation + server control ----------------

def generate_bat(server: dict):
    """
    Create or update <key>.bat in the FXServer folder.
    """
    key = server["key"]
    name = server["name"]
    dirp = server["dir"]
    profile = server.get("profile", "").strip()

    bat_path = os.path.join(dirp, f"{key}.bat")

    lines = [
        "@echo off",
        f'echo Starting {name}...',
        f'cd /d "{dirp}"',
    ]

    if profile:
        lines.append(f'FXServer.exe +set serverProfile "{profile}"')
    else:
        lines.append("FXServer.exe")

    lines.append("pause")
    content = "\r\n".join(lines) + "\r\n"

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(content)

    return bat_path


def start_server_process(server: dict):
    """
    Start server by running its <key>.bat (auto-creates if missing).
    """
    dirp = server["dir"]
    bat_path = os.path.join(dirp, f"{server['key']}.bat")

    if not os.path.exists(bat_path):
        bat_path = generate_bat(server)

    subprocess.Popen(["cmd", "/c", bat_path], cwd=dirp)


def kill_fxserver_for_dir(server: dict):
    """
    Best-effort: stop FXServer only for this server's folder if possible.
    Fallback: kills all FXServer.exe.
    """
    dirp = os.path.abspath(server["dir"])

    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='FXServer.exe'", "get", "ProcessId,ExecutablePath"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if len(lines) <= 1:
            return

        for line in lines[1:]:
            parts = re.split(r"\s{2,}", line)
            if len(parts) < 2:
                continue
            exe_path, pid_str = parts[0].strip(), parts[1].strip()
            if not exe_path or not pid_str:
                continue

            try:
                exe_dir = os.path.dirname(os.path.abspath(exe_path))
                common = os.path.commonpath([exe_dir, dirp])
                if common == dirp:
                    subprocess.call(
                        ["taskkill", "/F", "/PID", pid_str],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
            except Exception:
                continue
    except Exception:
        # fallback: kill all FXServer.exe
        subprocess.call(
            ["taskkill", "/F", "/IM", "FXServer.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def is_server_running(server: dict) -> bool:
    """
    Returns True if an FXServer.exe process appears to be running from this server's folder.
    """
    dirp = os.path.abspath(server["dir"])
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='FXServer.exe'", "get", "ExecutablePath"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        lines = [l.strip() for l in out.splitlines() if l.strip() and "ExecutablePath" not in l]
        for line in lines:
            exe_path = line.strip()
            if not exe_path:
                continue
            try:
                exe_dir = os.path.dirname(os.path.abspath(exe_path))
                common = os.path.commonpath([exe_dir, dirp])
                if common == dirp:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# ---------------- CLI handling ----------------

ASCII_LOGO = r"""
_________   _________ _________                                       
\_   ___ \ /   _____//   _____/ ______________  __ ___________  ______
/    \  \/ \_____  \ \_____  \_/ __ \_  __ \  \/ // __ \_  __ \/  ___/
\     \____/        \/        \  ___/|  | \/\   /\  ___/|  | \/\___ \ 
 \______  /_______  /_______  /\___  >__|    \_/  \___  >__|  /____  >
        \/        \/        \/     \/                 \/           \/  
                                                /_/  by Covex Studios
""".strip("\n")


def print_help():
    exe = "csservers"
    print(ASCII_LOGO)
    print()
    print(f"{APP_NAME} CLI")
    print()
    print("Usage:")
    print(f"  {exe}              # open GUI")
    print(f"  {exe} list")
    print(f"  {exe} start <name_or_key>")
    print(f"  {exe} stop <name_or_key>")
    print(f"  {exe} restart <name_or_key>")
    print()
    print("Examples:")
    print(f"  {exe} start dev")
    print(f"  {exe} start dev-server")
    print(f"  {exe} restart live")
    print()


def handle_cli(args: list):
    servers = load_servers()
    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return

    cmd = args[0].lower()

    if cmd == "list":
        if not servers:
            print("No servers configured yet.")
            print('Run "csservers" to open the GUI and add one.')
            return
        print("Configured servers:")
        for s in servers:
            print(f'  {s["key"]:<12} | {s["name"]:<25} | {s["dir"]} | profile={s.get("profile","")}')
        return

    if cmd in ("start", "stop", "restart"):
        if len(args) < 2:
            print(f"Missing server name/key. Usage: csservers {cmd} <name_or_key>")
            return

        s = find_server(servers, args[1])
        if not s:
            print(f'Server "{args[1]}" not found.')
            return

        if cmd in ("stop", "restart"):
            print(f"Stopping {s['name']}...")
            kill_fxserver_for_dir(s)

        if cmd in ("start", "restart"):
            print(f"Starting {s['name']}...")
            start_server_process(s)

        return

    print("Unknown command.")
    print_help()


# ---------------- main window ----------------

class ServerManagerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} | {APP_PUBLISHER}")
        self.setMinimumSize(950, 520)

        self.servers = load_servers()
        self.build_ui()
        self.refresh_list()

        # auto-update check on startup
        self.check_for_updates()

    # -------- UI --------

    def build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(16)

        left = QVBoxLayout()
        right = QVBoxLayout()

        # ======== LEFT: SERVER LIST ========

        label_servers = QLabel("Server List")
        label_servers.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        left.addWidget(label_servers)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_select)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #121212;
                border: 1px solid #2b2b2b;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        left.addWidget(self.list_widget, stretch=1)

        # status label (per selected server, best-effort)
        self.status_label = QLabel("Status: No server selected")
        self.status_label.setStyleSheet("color: #bbbbbb; font-size: 11px; margin-top: 4px;")
        left.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        for text, func in [
            ("New", self.new_server),
            ("Remove", self.remove_server),
            ("Start", self.start_server),
            ("Stop", self.stop_server),
            ("Restart", self.restart_server),
        ]:
            b = QPushButton(text)
            b.clicked.connect(func)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #E8B500;
                    color: #000;
                    padding: 6px 10px;
                    border-radius: 6px;
                    font-weight: 600;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #FFCC2E;
                }
                QPushButton:pressed {
                    background-color: #C99A00;
                }
            """)
            btn_row.addWidget(b)
        left.addLayout(btn_row)

        main.addLayout(left, 2)

        # ======== RIGHT: TITLE + FORM ========

        title = QLabel("CS FiveM Server Manager")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        right.addWidget(title)

        subtitle = QLabel("Manage multiple FXServer / TXAdmin profiles from one place.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        right.addWidget(subtitle)
        right.addSpacing(18)

        section_title = QLabel("Server Configuration")
        section_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        right.addWidget(section_title)
        right.addSpacing(10)

        def make_row(text):
            h = QHBoxLayout()
            label = QLabel(text)
            label.setStyleSheet("color: white; min-width: 190px;")
            box = QLineEdit()
            box.setStyleSheet("""
                QLineEdit {
                    background-color:#141414;
                    color:white;
                    border:1px solid #333;
                    padding:8px;
                    border-radius: 5px;
                }
                QLineEdit:focus {
                    border: 1px solid #E8B500;
                }
            """)
            h.addWidget(label)
            h.addWidget(box)
            return h, box

        row1, self.box_key = make_row("Key (dev / dev-server):")
        row2, self.box_name = make_row("Display name:")
        row3, self.box_dir = make_row("FXServer folder:")
        row4, self.box_profile = make_row("TXAdmin profile (no .base):")

        right.addLayout(row1)
        right.addLayout(row2)
        right.addLayout(row3)
        right.addLayout(row4)

        right.addSpacing(10)

        # extra actions row: open folder, open txAdmin
        extra_row = QHBoxLayout()
        self.btn_open_folder = QPushButton("Open Server Folder")
        self.btn_open_folder.clicked.connect(self.open_server_folder)
        self.btn_open_folder.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                padding: 7px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        extra_row.addWidget(self.btn_open_folder)

        self.btn_open_txadmin = QPushButton("Open txAdmin")
        self.btn_open_txadmin.clicked.connect(self.open_txadmin)
        self.btn_open_txadmin.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                padding: 7px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        extra_row.addWidget(self.btn_open_txadmin)

        right.addLayout(extra_row)

        # browse & save
        self.btn_browse = QPushButton("Browse FXServer folder...")
        self.btn_browse.clicked.connect(self.browse_folder)
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #E8B500;
                padding: 9px;
                border-radius: 6px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                background-color: #FFCC2E;
            }
            QPushButton:pressed {
                background-color: #C99A00;
            }
        """)
        right.addWidget(self.btn_browse)

        self.btn_save = QPushButton("Save Server")
        self.btn_save.clicked.connect(self.save_server)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #E8B500;
                padding: 9px;
                border-radius: 6px;
                font-weight: 700;
                border: none;
            }
            QPushButton:hover {
                background-color: #FFCC2E;
            }
            QPushButton:pressed {
                background-color: #C99A00;
            }
        """)
        right.addWidget(self.btn_save)

        right.addStretch()

        # footer
        footer = QHBoxLayout()

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setStyleSheet("color: #777; font-size: 10px;")
        footer.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignLeft)

        github_label = QLabel(
            '<a href="https://github.com/Covex-Studios/CSFiveMTool">GitHub: CS FiveM Tool</a>'
        )
        github_label.setOpenExternalLinks(True)
        github_label.setStyleSheet("color: #58a6ff; font-size: 10px;")
        footer.addWidget(github_label, alignment=Qt.AlignmentFlag.AlignRight)

        right.addLayout(footer)

        main.addLayout(right, 3)

        self.setStyleSheet("background-color: #0f0f0f;")

    # -------- list / selection --------

    def refresh_list(self):
        self.list_widget.clear()
        for s in self.servers:
            self.list_widget.addItem(s["name"])
        self.update_status_label()

    def current_server(self):
        idx = self.list_widget.currentRow()
        if idx < 0 or idx >= len(self.servers):
            return None
        return self.servers[idx]

    def on_select(self, idx: int):
        s = self.current_server()
        if not s:
            self.box_key.clear()
            self.box_name.clear()
            self.box_dir.clear()
            self.box_profile.clear()
            self.update_status_label()
            return

        self.box_key.setText(s["key"])
        self.box_name.setText(s["name"])
        self.box_dir.setText(s["dir"])
        self.box_profile.setText(s.get("profile", ""))
        self.update_status_label()

    def update_status_label(self):
        s = self.current_server()
        if not s:
            self.status_label.setText("Status: No server selected")
            self.status_label.setStyleSheet("color: #bbbbbb; font-size: 11px;")
            return
        if is_server_running(s):
            self.status_label.setText("Status: Running")
            self.status_label.setStyleSheet("color: #4caf50; font-size: 11px;")
        else:
            self.status_label.setText("Status: Not running")
            self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")

    # -------- actions --------

    def new_server(self):
        self.box_key.clear()
        self.box_name.clear()
        self.box_dir.clear()
        self.box_profile.clear()
        self.list_widget.clearSelection()
        self.update_status_label()

    def remove_server(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this server?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        s = self.servers[row]
        bat_path = os.path.join(s["dir"], f"{s['key']}.bat")
        try:
            if os.path.exists(bat_path):
                os.remove(bat_path)
        except Exception:
            pass

        del self.servers[row]
        save_servers(self.servers)
        self.refresh_list()

    def save_server(self):
        key = self.box_key.text().strip()
        name = self.box_name.text().strip()
        dirp = self.box_dir.text().strip()
        prof = self.box_profile.text().strip()

        if not key or not name or not dirp:
            QMessageBox.warning(
                self,
                "Missing Data",
                "Key, Name and FXServer folder are required."
            )
            return

        if not os.path.isdir(dirp):
            QMessageBox.warning(
                self,
                "Invalid folder",
                "FXServer folder does not exist."
            )
            return

        data = {"key": key, "name": name, "dir": dirp, "profile": prof}

        row = self.list_widget.currentRow()
        if row < 0:
            self.servers.append(data)
        else:
            self.servers[row] = data

        save_servers(self.servers)

        try:
            generate_bat(data)
        except Exception as e:
            QMessageBox.warning(
                self,
                "BAT creation error",
                f"Saved server, but failed to create .bat:\n{e}"
            )

        self.refresh_list()

    def browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select FXServer Folder")
        if d:
            self.box_dir.setText(d)

    def open_server_folder(self):
        s = self.current_server()
        if not s:
            return
        if os.path.isdir(s["dir"]):
            os.startfile(s["dir"])

    def open_txadmin(self):
        """
        Simple: open default txAdmin URL.
        Change port/host here if needed.
        """
        webbrowser.open("http://localhost:40120/")

    # -------- start / stop / restart --------

    def start_server(self):
        s = self.current_server()
        if not s:
            return
        try:
            start_server_process(s)
        except Exception as e:
            QMessageBox.warning(self, "Start error", str(e))
        self.update_status_label()

    def stop_server(self):
        s = self.current_server()
        if not s:
            return
        kill_fxserver_for_dir(s)
        self.update_status_label()

    def restart_server(self):
        s = self.current_server()
        if not s:
            return
        kill_fxserver_for_dir(s)
        try:
            start_server_process(s)
        except Exception as e:
            QMessageBox.warning(self, "Restart error", str(e))
        self.update_status_label()

    # -------- update check + auto-download --------

    def check_for_updates(self):
        if not UPDATE_JSON_URL.startswith("http"):
            return

        def parse_ver(v: str):
            try:
                return tuple(int(x) for x in v.split("."))
            except Exception:
                return (0,)

        try:
            resp = requests.get(UPDATE_JSON_URL, timeout=3)
            if resp.status_code != 200:
                return

            data = resp.json()
            latest = data.get("version", APP_VERSION).strip()

            if parse_ver(latest) <= parse_ver(APP_VERSION):
                return  # up to date or newer dev build

            reply = QMessageBox.question(
                self,
                "Update available",
                f"A new version ({latest}) is available.\n"
                f"You are on {APP_VERSION}.\n\n"
                "Do you want to download and run the installer now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.download_and_run_installer(latest)

        except Exception:
            # silent fail if no internet / GitHub down
            pass

    def download_and_run_installer(self, latest_version: str):
        if not INSTALLER_DOWNLOAD_URL.startswith("http"):
            QMessageBox.warning(self, "Update",
                                "Installer URL is not configured.")
            return

        try:
            download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(download_dir, exist_ok=True)
            installer_path = os.path.join(
                download_dir,
                f"CSFiveMToolSetup_{latest_version}.exe"
            )

            resp = requests.get(INSTALLER_DOWNLOAD_URL, stream=True, timeout=15)
            resp.raise_for_status()

            with open(installer_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            QMessageBox.information(
                self,
                "Update downloaded",
                f"Installer downloaded to:\n{installer_path}\n\n"
                "The installer will now run. Please close this app when asked."
            )

            subprocess.Popen([installer_path], shell=False)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Update failed",
                f"Failed to download or run installer:\n{e}"
            )


# ---------------- entry ----------------

if __name__ == "__main__":
    # CLI mode: any arguments = CLI
    if len(sys.argv) > 1:
        handle_cli(sys.argv[1:])
        sys.exit(0)

    # GUI mode
    app = QApplication(sys.argv)
    win = ServerManagerApp()
    win.show()
    sys.exit(app.exec())
