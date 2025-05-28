# Step 1: Base Image and Initial Setup
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-17-jdk \
    wget \
    unzip \
    tar \
    git \
    python3 \
    python3-pip \
    python3-venv \
    libgl1-mesa-glx \
    libpulse0 \
    libsdl2-2.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcursor1 \
    libxrandr2 \
    libxcomposite1 \
    libxi6 \
    libxtst6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
ENV ANDROID_SDK_ROOT="/opt/android-sdk" 
ENV PATH="${PATH}:${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin:${ANDROID_SDK_ROOT}/platform-tools:${ANDROID_SDK_ROOT}/emulator"
WORKDIR /agent

# Step 2: Install Android SDK Command-Line Tools
ENV CMDLINE_TOOLS_VERSION="11076708" 
RUN mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip -P /tmp && \
    unzip -q /tmp/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip -d ${ANDROID_SDK_ROOT}/cmdline-tools/tmp_tools && \
    mkdir -p ${ANDROID_SDK_ROOT}/cmdline-tools/latest && \
    mv ${ANDROID_SDK_ROOT}/cmdline-tools/tmp_tools/cmdline-tools/* ${ANDROID_SDK_ROOT}/cmdline-tools/latest/ && \
    rm -rf ${ANDROID_SDK_ROOT}/cmdline-tools/tmp_tools && \
    rm /tmp/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip
RUN yes | ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager --licenses > /dev/null || true

# Step 3: Install Essential Android SDK Packages
ENV ANDROID_BUILD_TOOLS_VERSION="34.0.0" 
ENV ANDROID_SYSTEM_IMAGE="system-images;android-30;google_apis;x86_64" 

# Install SDK packages using sdkmanager
RUN ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager \
    "platform-tools" \
    "build-tools;${ANDROID_BUILD_TOOLS_VERSION}" \
    "emulator" \
    "${ANDROID_SYSTEM_IMAGE}"

# Create a basic AVD (Android Virtual Device) using avdmanager
RUN echo "no" | ${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/avdmanager create avd \
    --force \
    --name "agent_avd" \
    --package "${ANDROID_SYSTEM_IMAGE}" \
    --tag "google_apis" \
    --abi "x86_64"

# (The rest of your Dockerfile - Step 4 and Step 5 - follows here)

# (Optional) You can pre-configure the AVD further by editing its config.ini
# For example, to enable hardware keyboard and set default orientation:
# RUN echo "hw.keyboard=yes" >> /root/.android/avd/agent_avd.avd/config.ini
# RUN echo "hw.initialOrientation=portrait" >> /root/.android/avd/agent_avd.avd/config.ini

# Step 4: Set up Python Environment and Copy Agent Files

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./scripts ./scripts

COPY workflow_manager.py .
COPY apk_info.py .
COPY install_apk.py .
COPY check_package.py .

COPY config.yaml .

# Step 5: Define Entrypoint and Default Command

# Copy the entrypoint script into the image and make it executable
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose the default ADB port (emulator port + 1) and emulator console port
# These are informational; you'll still use -p in docker run for actual mapping
EXPOSE 5555 
EXPOSE 5554 

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Define default command (arguments to the entrypoint script)
# These will be used if no arguments are provided to 'docker run <image_name>'
# The user will typically override these.
# Provide placeholders or sensible defaults.
# $1: APK path inside container
# $2: Task Description
# $3: Model (optional)
# $4: API Key (optional)
CMD ["/mnt/apks/default.apk", "Default task: Explore the app and summarize its main features.", "None", "None"]
