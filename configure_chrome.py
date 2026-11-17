import urllib.request
import json
import time
import os
import websocket

EXTENSION_ID = "oclhhmlkjfdjmklecinlepakkifmkaja"

def recv_matching(ws, req_id, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            raw = ws.recv()
            if not raw:
                continue
            msg = json.loads(raw)
            if msg.get("id") == req_id:
                return msg
        except Exception:
            break
    return None

def configure():
    print("=== Chrome Configuration Agent ===")
    
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
    try:
        print(f"Connecting to browser WebSocket: {browser_ws_url}")
        browser_ws = websocket.create_connection(browser_ws_url, timeout=10)

        # 1. Dynamically load unpacked extension
        try:
            load_cmd = {
                "id": 101,
                "method": "Extensions.loadUnpacked",
                "params": {
                    "path": "/app/extensions/violentmonkey"
                }
            }
            browser_ws.send(json.dumps(load_cmd))
            load_res = recv_matching(browser_ws, 101, timeout=5)
            print(f"Extensions.loadUnpacked result: {load_res}")
        except Exception as e:
            print(f"Note on loadUnpacked: {e}")

        # 2. Get existing targets
        browser_ws.send(json.dumps({"id": 102, "method": "Target.getTargets"}))
        targets_res = recv_matching(browser_ws, 102, timeout=5)
        existing_targets = targets_res.get("result", {}).get("targetInfos", []) if targets_res else []
        print(f"Existing targets count: {len(existing_targets)}")
        for t in existing_targets:
            print(f" - Target: {t.get('type')} | {t.get('url')} | {t.get('title')}")

        # 3. Create or find chrome://extensions target
        target_id = None
        for t in existing_targets:
            if "chrome://extensions" in t.get("url", ""):
                target_id = t.get("targetId")
                break

        created_new = False
        if not target_id:
            browser_ws.send(json.dumps({"id": 103, "method": "Target.createTarget", "params": {"url": "chrome://extensions"}}))
            create_res = recv_matching(browser_ws, 103, timeout=5)
            target_id = create_res.get("result", {}).get("targetId") if create_res else None
            created_new = True
            print(f"Target chrome://extensions created: {target_id}")

        if target_id:
            # 4. Attach to the target
            browser_ws.send(json.dumps({"id": 104, "method": "Target.attachToTarget", "params": {"targetId": target_id, "flatten": True}}))
            attach_res = recv_matching(browser_ws, 104, timeout=5)
            session_id = attach_res.get("result", {}).get("sessionId") if attach_res else None
            print(f"Attached session ID: {session_id}")

            if session_id:
                js_code = """
                (async () => {
                    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
                    if (chrome && chrome.developerPrivate && chrome.developerPrivate.updateProfileConfiguration) {
                        await new Promise((resolve) => {
                            chrome.developerPrivate.updateProfileConfiguration({ inDeveloperMode: true }, () => resolve(true));
                        });
                    }
                    await sleep(500);
                    let extensions = [];
                    if (chrome && chrome.developerPrivate && chrome.developerPrivate.getExtensionsInfo) {
                        for (let i = 0; i < 10; i++) {
                            extensions = await new Promise((resolve) => {
                                chrome.developerPrivate.getExtensionsInfo({ includeDisabled: true, includeTerminated: true }, (res) => resolve(res || []));
                            });
                            if (extensions && extensions.length > 0) break;
                            await sleep(300);
                        }
                    }
                    const ext = extensions.find(e => 
                        e.id === "oclhhmlkjfdjmklecinlepakkifmkaja" ||
                        e.name.toLowerCase().includes("hanomonkey") || 
                        e.name.toLowerCase().includes("violentmonkey")
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
                    return { status: "ready" };
                })()
                """
                browser_ws.send(json.dumps({
                    "id": 105,
                    "sessionId": session_id,
                    "method": "Runtime.evaluate",
                    "params": {"expression": js_code, "awaitPromise": True, "returnByValue": True}
                }))
                eval_res = recv_matching(browser_ws, 105, timeout=10)
                print("Evaluation result:", json.dumps(eval_res, indent=2))

                # Navigate target to teaserfast login rather than closing so browser window is never closed
                if created_new:
                    print("Navigating extensions target to teaserfast login...")
                    browser_ws.send(json.dumps({
                        "id": 106,
                        "sessionId": session_id,
                        "method": "Page.navigate",
                        "params": {"url": "https://teaserfast.ru/login/"}
                    }))
                    recv_matching(browser_ws, 106, timeout=5)

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
