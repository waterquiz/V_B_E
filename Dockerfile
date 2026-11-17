FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PORT=5000
ENV DISPLAY=:99
ENV RESOLUTION=1280x720x24

RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    openbox \
    menu \
    python3 \
    python3-pip \
    wget \
    curl \
    tar \
    xdotool \
    x11-utils \
    x11-xserver-utils \
    libegl1 \
    libgl1 \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    mesa-utils \
    dbus \
    dbus-x11 \
    fonts-liberation \
    fonts-noto-color-emoji \
    libxkbcommon0 \
    gnupg \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN dbus-uuidgen > /etc/machine-id && \
    mkdir -p /var/lib/dbus && \
    cp /etc/machine-id /var/lib/dbus/machine-id

RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/google-chrome-stable /usr/bin/chromium-browser \
    && ln -sf /usr/bin/google-chrome-stable /usr/bin/chromium

RUN pip3 install --no-cache-dir websockify websocket-client

RUN mkdir -p /app/novnc
RUN wget -qO- https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz | \
    tar xz -C /app/novnc --strip-components=1 \
    && ln -sf /app/novnc/vnc.html /app/novnc/index.html

RUN mkdir -p /app/extensions

COPY ["Vilan Monkey", "/app/extensions/violentmonkey"]
COPY configure_chrome.py /app/configure_chrome.py

RUN mkdir -p /etc/opt/chrome/policies/managed \
    /etc/chromium/policies/managed \
    /etc/chromium-browser/policies/managed
COPY pin_extension.json /etc/opt/chrome/policies/managed/pin_extension.json
COPY pin_extension.json /etc/chromium/policies/managed/pin_extension.json
COPY pin_extension.json /etc/chromium-browser/policies/managed/pin_extension.json
RUN chmod 755 /etc/opt/chrome/policies /etc/opt/chrome/policies/managed /etc/chromium/policies /etc/chromium/policies/managed /etc/chromium-browser/policies /etc/chromium-browser/policies/managed && \
    chmod 644 /etc/opt/chrome/policies/managed/pin_extension.json /etc/chromium/policies/managed/pin_extension.json /etc/chromium-browser/policies/managed/pin_extension.json

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app

EXPOSE 5000
EXPOSE 5900

CMD ["/app/start.sh"]
