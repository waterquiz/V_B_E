import os
import json
import time
import urllib.request
import websocket

EXTENSION_PATH = "/app/extensions/violentmonkey"
EXTENSION_ID = "oclhhmlkjfdjmklecinlepakkifmkaja"
TARGET_URL = "https://teaserfast.ru/login/"

def init_preferences():
    profile_dir = '/app/chrome_profile/Default'
    os.makedirs(profile_dir, exist_ok=True)
    prefs_file = os.path.join(profile_dir, 'Preferences')
    
    prefs = {}
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
        except Exception:
            prefs = {}
    
    prefs.setdefault('extensions', {})
    prefs['extensions'].setdefault('ui', {})
    prefs['extensions']['ui']['developer_mode'] = True
    
    pinned = prefs['extensions'].get('pinned_extensions', [])
    if EXTENSION_ID not in pinned:
        pinned.append(EXTENSION_ID)
    prefs['extensions']['pinned_extensions'] = pinned
    
    # Reset any crash state in profile
    prefs.setdefault('profile', {})
    prefs['profile']['exit_type'] = 'Normal'
    prefs['profile']['exited_cleanly'] = True
    
    try:
        with open(prefs_file, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2)
        print(f"Preferences initialized in {prefs_file}")
    except Exception as e:
        print(f"Error writing preferences: {e}")

def configure_running_chrome():
    print("Waiting for Chrome DevTools port 9222...")
    ws_url = None
    for attempt in range(40):
        try:
            with urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                ws_url = data.get('webSocketDebuggerUrl')
                if ws_url:
                    print(f"Connected to Chrome browser endpoint (attempt {attempt+1})")
                    break
        except Exception:
            pass
        time.sleep(0.5)
    
    if not ws_url:
        print("Could not connect to Chrome debugging port after 20s.")
        return False

    # 1. Load unpacked extension via browser WebSocket
    try:
        ws = websocket.create_connection(ws_url, timeout=5)
        print(f"Loading extension from {EXTENSION_PATH} via CDP...")
        ws.send(json.dumps({
            'id': 1,
            'method': 'Extensions.loadUnpacked',
            'params': {'path': EXTENSION_PATH}
        }))
        res = json.loads(ws.recv())
        print(f"Extension load response: {res}")
        ws.close()
    except Exception as e:
        print(f"Error loading unpacked extension via CDP: {e}")

    # Brief delay for extension initialization
    time.sleep(1)

    # 2. Find the primary page target and navigate to target URL
    try:
        with urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=2) as resp:
            targets = json.loads(resp.read().decode('utf-8'))
        
        page_targets = [t for t in targets if t.get('type') == 'page']
        if page_targets:
            target = page_targets[0]
            page_ws_url = target.get('webSocketDebuggerUrl')
            if page_ws_url:
                page_ws = websocket.create_connection(page_ws_url, timeout=5)
                print(f"Navigating page target ({target.get('id')}) to {TARGET_URL}...")
                page_ws.send(json.dumps({
                    'id': 2,
                    'method': 'Page.navigate',
                    'params': {'url': TARGET_URL}
                }))
                nav_res = json.loads(page_ws.recv())
                print(f"Navigation response: {nav_res}")
                page_ws.close()
                return True
    except Exception as e:
        print(f"Error navigating page target via CDP: {e}")

    return False

if __name__ == "__main__":
    import sys
    if "--init" in sys.argv:
        init_preferences()
    else:
        init_preferences()
        configure_running_chrome()
