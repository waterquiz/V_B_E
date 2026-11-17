import urllib.request
import json
import time
import os
import websocket

EXTENSION_ID = "oclhhmlkjfdjmklecinlepakkifmkaja"

def configure():
    print("=== Chrome Configuration Agent ===")
    
    # 1. Wait for Chrome debug port to open
    debug_url = "http://127.0.0.1:9222/json/version"
    browser_ws_url = None
    
    for i in range(30):
        try:
            req = urllib.request.urlopen(debug_url, timeout=2)
            version_info = json.loads(req.read().decode())
            browser_ws_url = version_info.get("webSocketDebuggerUrl")
            if browser_ws_url:
                print("Connected to Chrome debugging port!")
                break
        except Exception:
            print(f"Waiting for Chrome debugging port to be ready... ({i}/30)")
            time.sleep(1)
            
    if not browser_ws_url:
        print("Warning: Could not connect to Chrome debugging port.")
        return False

    browser_ws = None
    target_id = None
    try:
        print(f"Connecting to browser WebSocket: {browser_ws_url}")
        browser_ws = websocket.create_connection(browser_ws_url, timeout=10)

        # 2. Dynamically load unpacked extension just in case
        try:
            load_cmd = {
                "id": 101,
                "method": "Extensions.loadUnpacked",
                "params": {
                    "path": "/app/extensions/violentmonkey"
                }
            }
            browser_ws.send(json.dumps(load_cmd))
            load_res = json.loads(browser_ws.recv())
            print(f"Extensions.loadUnpacked result: {load_res}")
        except Exception as e:
            print(f"Note on loadUnpacked: {e}")

        # 3. Create target for chrome://extensions
        print("Opening chrome://extensions target via CDP...")
        create_cmd = {
            "id": 102,
            "method": "Target.createTarget",
            "params": {
                "url": "chrome://extensions"
            }
        }
        browser_ws.send(json.dumps(create_cmd))
        create_res = json.loads(browser_ws.recv())
        target_id = create_res.get("result", {}).get("targetId")
        print(f"Target created: {target_id}")

        if not target_id:
            # Fallback to search in existing targets
            browser_ws.send(json.dumps({"id": 103, "method": "Target.getTargets"}))
            targets_res = json.loads(browser_ws.recv())
            for t in targets_res.get("result", {}).get("targetInfos", []):
                if "chrome://extensions" in t.get("url", ""):
                    target_id = t.get("targetId")
                    break

        if target_id:
            # 4. Attach to the target
            print(f"Attaching to target {target_id}...")
            attach_cmd = {
                "id": 104,
                "method": "Target.attachToTarget",
                "params": {
                    "targetId": target_id,
                    "flatten": True
                }
            }
            browser_ws.send(json.dumps(attach_cmd))
            attach_res = json.loads(browser_ws.recv())
            session_id = attach_res.get("result", {}).get("sessionId")
            print(f"Session ID: {session_id}")

            if session_id:
                # 5. Execute configuration script inside chrome://extensions
                js_code = """
                (async () => {
                    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
                    
                    // Enable Developer Mode
                    if (chrome && chrome.developerPrivate && chrome.developerPrivate.updateProfileConfiguration) {
                        await new Promise((resolve) => {
                            chrome.developerPrivate.updateProfileConfiguration({ inDeveloperMode: true }, () => resolve(true));
                        });
                    }
                    
                    await sleep(1000);
                    
                    // Get all extensions
                    let extensions = [];
                    if (chrome && chrome.developerPrivate && chrome.developerPrivate.getExtensionsInfo) {
                        for (let i = 0; i < 15; i++) {
                            extensions = await new Promise((resolve) => {
                                chrome.developerPrivate.getExtensionsInfo({ includeDisabled: true, includeTerminated: true }, (res) => resolve(res || []));
                            });
                            if (extensions && extensions.length > 0) break;
                            await sleep(500);
                        }
                    }
                    
                    // Find Violentmonkey
                    const ext = extensions.find(e => 
                        e.id === "oclhhmlkjfdjmklecinlepakkifmkaja" ||
                        e.name.toLowerCase().includes("hanomonkey") || 
                        e.name.toLowerCase().includes("vilan monkey") || 
                        e.name.toLowerCase().includes("violentmonkey") || 
                        (e.path && e.path.toLowerCase().includes("violentmonkey"))
                    );
                    
                    if (ext && chrome && chrome.developerPrivate && chrome.developerPrivate.updateExtensionConfiguration) {
                        await new Promise((resolve) => {
                            chrome.developerPrivate.updateExtensionConfiguration({
                                extensionId: ext.id,
                                userScriptsAccess: true,
                                incognitoAccess: true
                            }, () => resolve(true));
                        });
                        return { status: "success", extension: ext.name, id: ext.id };
                    }
                    return { status: "ready", available: (extensions || []).map(e => e.name + ' (' + e.id + ')') };
                })()
                """

                eval_cmd = {
                    "id": 105,
                    "sessionId": session_id,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js_code,
                        "awaitPromise": True,
                        "returnByValue": True
                    }
                }
                browser_ws.send(json.dumps(eval_cmd))
                
                # Wait for response (filtering out background events if any)
                for _ in range(10):
                    raw = browser_ws.recv()
                    msg = json.loads(raw)
                    if msg.get("id") == 105:
                        print("Evaluation result:", json.dumps(msg, indent=2))
                        break

            # 6. Close the chrome://extensions tab so user sees the login page
            print(f"Closing chrome://extensions tab (target ID: {target_id})...")
            close_cmd = {
                "id": 106,
                "method": "Target.closeTarget",
                "params": {
                    "targetId": target_id
                }
            }
            browser_ws.send(json.dumps(close_cmd))
            print("Target closed:", browser_ws.recv())

    except Exception as e:
        print(f"CDP configuration warning: {e}")
    finally:
        if browser_ws:
            try:
                browser_ws.close()
            except Exception:
                pass

    return True

def update_preferences_file():
    print("Running Toolbar Pinning & Preferences utility...")
    prefs_file = '/app/chrome_profile/Default/Preferences'
    if not os.path.exists(prefs_file):
        prefs_file = os.path.expanduser('~/.config/google-chrome/Default/Preferences')
        
    for i in range(10):
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
        time.sleep(1)
    return False

if __name__ == "__main__":
    time.sleep(2)
    configure()
    update_preferences_file()
