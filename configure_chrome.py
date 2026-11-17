import os
import json
import time

EXTENSION_ID = "oclhhmlkjfdjmklecinlepakkifmkaja"

def update_preferences_file():
    print("=== Chrome Preferences & Pinning Utility ===")
    prefs_file = '/app/chrome_profile/Default/Preferences'
    if not os.path.exists(prefs_file):
        prefs_file = os.path.expanduser('~/.config/google-chrome/Default/Preferences')
        
    for i in range(15):
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    prefs = json.loads(f.read())
                
                prefs.setdefault('extensions', {})
                prefs['extensions'].setdefault('ui', {})
                prefs['extensions']['ui']['developer_mode'] = True
                
                # Pinned extensions list
                pinned = prefs['extensions'].get('pinned_extensions', [])
                if EXTENSION_ID not in pinned:
                    pinned.append(EXTENSION_ID)
                prefs['extensions']['pinned_extensions'] = pinned
                
                # Extension settings
                settings = prefs['extensions'].setdefault('settings', {})
                ext_conf = settings.setdefault(EXTENSION_ID, {})
                ext_conf['user_scripts_granted'] = True
                ext_conf['incognito_access'] = True
                
                with open(prefs_file, 'w') as f:
                    json.dump(prefs, f, indent=2)
                print(f"Extension {EXTENSION_ID} pinned and preferences updated successfully in {prefs_file}")
                return True
            except Exception as e:
                print(f"Preferences file update note: {e}")
        time.sleep(2)
    return False

if __name__ == "__main__":
    time.sleep(3)
    update_preferences_file()
