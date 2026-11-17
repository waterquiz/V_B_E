import os
import json
import time

EXTENSION_ID = "oclhhmlkjfdjmklecinlepakkifmkaja"

def configure_profile():
    profile_dir = '/app/chrome_profile/Default'
    os.makedirs(profile_dir, exist_ok=True)
    prefs_file = os.path.join(profile_dir, 'Preferences')
    
    prefs = {}
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
        except Exception as e:
            print(f"Reading existing prefs error: {e}")
            prefs = {}
    
    prefs.setdefault('extensions', {})
    prefs['extensions'].setdefault('ui', {})
    prefs['extensions']['ui']['developer_mode'] = True
    
    pinned = prefs['extensions'].get('pinned_extensions', [])
    if EXTENSION_ID not in pinned:
        pinned.append(EXTENSION_ID)
    prefs['extensions']['pinned_extensions'] = pinned
    prefs['extensions']['toolbar'] = pinned
    
    settings = prefs['extensions'].setdefault('settings', {})
    ext_conf = settings.setdefault(EXTENSION_ID, {})
    ext_conf['user_scripts_granted'] = True
    ext_conf['incognito_access'] = True
    
    with open(prefs_file, 'w', encoding='utf-8') as f:
        json.dump(prefs, f, indent=2)
    print(f"Extension {EXTENSION_ID} pre-pinned and configured in {prefs_file}")

if __name__ == "__main__":
    configure_profile()
