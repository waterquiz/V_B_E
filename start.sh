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
    pkill -f tint2 2>/dev/null || true
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

# Set desktop background
xsetroot -solid "#2c3e50" 2>/dev/null || true

# 3. Start Window Manager (Openbox + tint2 panel)
echo "Starting openbox..."
openbox --sm-disable &
sleep 1

echo "Starting tint2 panel..."
tint2 &
sleep 1

# 4. Initialize clean profile directory if needed
mkdir -p /app/chrome_profile

# 5. Launch Google Chrome in supervised loop with memory constraints
echo "Starting Chrome supervisor..."
(
    while true; do
        echo "Launching Google Chrome with Violentmonkey..."
        google-chrome-stable \
            --display="${DISPLAY}" \
            --no-sandbox \
            --disable-dev-shm-usage \
            --disable-gpu \
            --start-maximized \
            --no-first-run \
            --no-default-browser-check \
            --window-size=1280,720 \
            --window-position=0,0 \
            --disable-background-networking \
            --disable-sync \
            --mute-audio \
            --js-flags="--max-old-space-size=256" \
            --renderer-process-limit=2 \
            --disable-features=Translate,OptimizationHints,MediaRouter \
            --user-data-dir=/app/chrome_profile \
            --load-extension=/app/extensions/violentmonkey \
            https://teaserfast.ru/login/ || true
        echo "Chrome exited, restarting in 2 seconds..."
        sleep 2
    done
) &

# Ensure visible Chrome window is active and raised
(
    for i in $(seq 1 30); do
        sleep 1
        WID=$(xdotool search --onlyvisible --class "google-chrome" 2>/dev/null | tail -n 1 || true)
        if [ -z "$WID" ]; then
            WID=$(xdotool search --onlyvisible --class "chromium" 2>/dev/null | tail -n 1 || true)
        fi
        if [ -n "$WID" ]; then
            echo "Activating visible Chrome window: $WID"
            xdotool windowactivate "$WID" 2>/dev/null || true
            xdotool windowraise "$WID" 2>/dev/null || true
            break
        fi
    done
) &

# 6. Run Chrome preferences & pinning agent in background
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
