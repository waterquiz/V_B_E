#!/bin/bash
set -e

ulimit -n 65535 2>/dev/null || ulimit -n 4096 2>/dev/null || true

DISPLAY_NUM=99
DISPLAY=":${DISPLAY_NUM}"
RESOLUTION="1280x720x24"
VNC_PORT=5900
WEB_PORT="${PORT:-5000}"
VNC_PASSWORD="${VNC_PASSWORD:-}"
NOVNC_DIR="$(dirname "$0")/novnc"

echo "=== Starting Browser Desktop ==="
echo "Web port: $WEB_PORT"

cleanup() {
    echo "Cleaning up processes..."
    pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
    pkill -f x11vnc 2>/dev/null || true
    pkill -f websockify 2>/dev/null || true
    pkill -f "google-chrome" 2>/dev/null || true
    pkill -f "chromium-browser" 2>/dev/null || true
    pkill -f openbox 2>/dev/null || true
    pkill -f dbus-daemon 2>/dev/null || true
}
trap cleanup EXIT

# 1. Machine ID & D-Bus
if [ ! -s /etc/machine-id ]; then
    dbus-uuidgen > /etc/machine-id 2>/dev/null || true
fi
mkdir -p /var/lib/dbus /var/run/dbus
cp -f /etc/machine-id /var/lib/dbus/machine-id 2>/dev/null || true

dbus-daemon --system --fork 2>/dev/null || true
eval $(dbus-launch --sh-syntax 2>/dev/null || echo "")
export DBUS_SESSION_BUS_ADDRESS

# Clean existing Xvfb locks if any
pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
rm -f /tmp/.X${DISPLAY_NUM}-lock /tmp/.X11-unix/X${DISPLAY_NUM} 2>/dev/null || true
sleep 1

# 2. Start Xvfb
echo "Starting Xvfb on ${DISPLAY}..."
Xvfb "${DISPLAY}" -screen 0 "${RESOLUTION}" -ac +extension GLX +render -noreset &
sleep 2

for i in 1 2 3 4 5; do
    if DISPLAY="${DISPLAY}" xdpyinfo >/dev/null 2>&1; then
        echo "X display ready!"
        break
    fi
    echo "Waiting for X display... attempt $i"
    sleep 1
done

export DISPLAY="${DISPLAY}"

# Set a background color
xsetroot -solid "#2c3e50" 2>/dev/null || true

# 3. Pre-configure Developer Mode and pinned extension in Preferences
echo "Pre-configuring Chrome Preferences..."
mkdir -p /app/chrome_profile/Default

cat <<EOF > /app/chrome_profile/Default/Preferences
{
  "extensions": {
    "ui": {
      "developer_mode": true
    },
    "pinned_extensions": [
      "oclhhmlkjfdjmklecinlepakkifmkaja"
    ],
    "settings": {
      "oclhhmlkjfdjmklecinlepakkifmkaja": {
        "user_scripts_granted": true,
        "incognito_access": true
      }
    }
  }
}
EOF

# 4. Openbox Window Manager Configuration
mkdir -p /root/.config/openbox /etc/xdg/openbox
cat << 'EOF' > /root/.config/openbox/rc.xml
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <theme>
    <titleLayout></titleLayout>
  </theme>
  <applications>
    <application class="*">
      <maximized>yes</maximized>
      <decor>no</decor>
      <focus>yes</focus>
    </application>
  </applications>
</openbox_config>
EOF
cp /root/.config/openbox/rc.xml /etc/xdg/openbox/rc.xml 2>/dev/null || true

echo "Starting openbox window manager..."
openbox --sm-disable &
sleep 1

# 5. Launch Chrome
echo "Launching Chrome with Violentmonkey..."
chromium-browser \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --ozone-platform=x11 \
    --enable-features=UseOzonePlatform \
    --start-maximized \
    --no-first-run \
    --no-default-browser-check \
    --disable-translate \
    --disable-notifications \
    --disable-default-apps \
    --window-size=1280,720 \
    --window-position=0,0 \
    --noerrdialogs \
    --remote-debugging-port=9222 \
    --remote-allow-origins=* \
    --user-data-dir=/app/chrome_profile \
    --load-extension=/app/extensions/violentmonkey \
    --disable-features=Translate \
    https://teaserfast.ru/login/ &

# Ensure Chrome window is mapped, raised, and active
(
    for i in $(seq 1 30); do
        sleep 1
        WIDS=$(xdotool search --class "chrome" 2>/dev/null || xdotool search --class "chromium" 2>/dev/null || true)
        if [ -n "$WIDS" ]; then
            for W in $WIDS; do
                xdotool windowactivate "$W" 2>/dev/null || true
                xdotool windowraise "$W" 2>/dev/null || true
                xdotool windowmap "$W" 2>/dev/null || true
            done
            echo "Chrome window activated via xdotool: $WIDS"
            break
        fi
    done
) &

# 6. Run Chrome configuration agent in background
python3 /app/configure_chrome.py &

# 7. Start x11vnc with polling and damage
echo "Starting x11vnc..."
if [ -n "$VNC_PASSWORD" ]; then
    x11vnc -display "${DISPLAY}" -rfbport "${VNC_PORT}" \
        -passwd "${VNC_PASSWORD}" -forever -shared -bg -wait 50 -defer 50 \
        -o /tmp/x11vnc.log 2>/dev/null
else
    x11vnc -display "${DISPLAY}" -rfbport "${VNC_PORT}" \
        -nopw -forever -shared -bg -wait 50 -defer 50 \
        -o /tmp/x11vnc.log 2>/dev/null
fi
sleep 2

# 8. Start noVNC / websockify
echo "Starting noVNC on port ${WEB_PORT}..."
websockify --web "${NOVNC_DIR}" "${WEB_PORT}" "localhost:${VNC_PORT}" &

echo ""
echo "=== Desktop ready! ==="
echo "Open the preview and go to /vnc.html to connect"
wait
