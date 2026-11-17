import os
import json
import time

EXTENSION_ID = "oclhhmlkjfdjmklecinlepakkifmkaja"

def update_preferences_file():
    print("=== Chrome Preferences & Pinning Utility ===")
    prefs_file = '/app/chrome_profile/Default/Preferences'
    
    # Wait for Chrome to initialize its profile and write Preferences
    for i in range(30):
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ensure Chrome has written a real preferences file
                if len(content) > 100:
                    prefs = json.loads(content)
                    
                    prefs.setdefault('extensions', {})
                    prefs['extensions'].setdefault('ui', {})
                    prefs['extensions']['ui']['developer_mode'] = True
                    
                    pinned = prefs['extensions'].get('pinned_extensions', [])
                    if EXTENSION_ID not in pinned:
                        pinned.append(EXTENSION_ID)
                    prefs['extensions']['pinned_extensions'] = pinned
                    
                    settings = prefs['extensions'].setdefault('settings', {})
                    ext_conf = settings.setdefault(EXTENSION_ID, {})
                    ext_conf['user_scripts_granted'] = True
                    ext_conf['incognito_access'] = True
                    
                    with open(prefs_file, 'w', encoding='utf-8') as f:
                        json.dump(prefs, f, indent=2)
                    print(f"Extension {EXTENSION_ID} pinned and preferences updated successfully in {prefs_file}")
                    return True
            except Exception as e:
                print(f"Preferences check ({i}/30): {e}")
        time.sleep(2)
    return False

if __name__ == "__main__":
    time.sleep(5)
    update_preferences_file()
