# Android 11 x86_64 Container with Device Spoofing
FROM redroid/redroid:11.0.0-x86_64-latest

# Install required tools and dependencies
RUN apt-get update && apt-get install -y \
    adb \
    curl \
    wget \
    unzip \
    python3 \
    python3-pip \
    sqlite3 \
    nano \
    vim \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV ANDROID_VERSION=11
ENV ARCH=x86_64
ENV REDROID_GPU_MODE=auto
ENV REDROID_WIDTH=1080
ENV REDROID_HEIGHT=1920
ENV REDROID_DPI=320

# Copy spoofing tools and scripts
COPY ../../scripts/android-setup.sh /system/bin/android-setup.sh
COPY ../../scripts/integrity-bypass.sh /system/bin/integrity-bypass.sh
COPY ../../scripts/gps-injection.sh /system/bin/gps-injection.sh
COPY ../../modules/device-profiles/ /system/etc/device-profiles/
COPY ../../modules/bypass-tools/ /system/etc/bypass-tools/
COPY ../../modules/gps-injection/ /system/etc/gps-injection/

# Make scripts executable
RUN chmod +x /system/bin/android-setup.sh \
    && chmod +x /system/bin/integrity-bypass.sh \
    && chmod +x /system/bin/gps-injection.sh

# Install Magisk for root management (x86_64 version)
RUN cd /tmp && \
    wget https://github.com/topjohnwu/Magisk/releases/download/v26.4/Magisk-v26.4.apk -O magisk.apk && \
    unzip magisk.apk lib/x86_64/libmagisk64.so -d magisk && \
    cp magisk/lib/x86_64/libmagisk64.so /system/bin/magisk && \
    chmod 755 /system/bin/magisk && \
    rm -rf /tmp/magisk*

# Install LSPosed framework for system modifications
RUN cd /tmp && \
    wget https://github.com/LSPosed/LSPosed/releases/download/v1.9.2/LSPosed-v1.9.2-7024-zygisk-release.zip -O lsposed.zip && \
    unzip lsposed.zip -d /system/framework/ && \
    rm lsposed.zip

# Install privacy/spoofing modules
RUN cd /tmp && \
    wget https://github.com/JingMatrix/ChromeXt/releases/download/v118.8/ChromeXt.apk -O chromext.apk && \
    mkdir -p /system/priv-app/ChromeXt && \
    cp chromext.apk /system/priv-app/ChromeXt/ChromeXt.apk && \
    chmod 644 /system/priv-app/ChromeXt/ChromeXt.apk

# Configure system properties for device spoofing (x86_64 optimized)
RUN echo "# Device Spoofing Properties" >> /system/build.prop && \
    echo "ro.product.brand=google" >> /system/build.prop && \
    echo "ro.product.name=sdk_gphone64_x86_64" >> /system/build.prop && \
    echo "ro.product.model=Pixel 5" >> /system/build.prop && \
    echo "ro.product.manufacturer=Google" >> /system/build.prop && \
    echo "ro.product.device=redfin" >> /system/build.prop && \
    echo "ro.build.fingerprint=google/redfin/redfin:11/RQ3A.211001.001/7641976:user/release-keys" >> /system/build.prop && \
    echo "ro.build.description=redfin-user 11 RQ3A.211001.001 7641976 release-keys" >> /system/build.prop

# SafetyNet/Play Integrity bypass configuration
RUN mkdir -p /data/adb/modules/playintegrityfix && \
    echo "id=playintegrityfix" > /data/adb/modules/playintegrityfix/module.prop && \
    echo "name=Play Integrity Fix" >> /data/adb/modules/playintegrityfix/module.prop && \
    echo "version=v15.9" >> /data/adb/modules/playintegrityfix/module.prop && \
    echo "versionCode=15900" >> /data/adb/modules/playintegrityfix/module.prop && \
    echo "author=chiteroman" >> /data/adb/modules/playintegrityfix/module.prop && \
    echo "description=Universal SafetyNet & Play Integrity Fix" >> /data/adb/modules/playintegrityfix/module.prop

# Configure startup script
RUN echo '#!/system/bin/sh' > /system/bin/container-init.sh && \
    echo 'export PATH=/system/bin:$PATH' >> /system/bin/container-init.sh && \
    echo '/system/bin/android-setup.sh' >> /system/bin/container-init.sh && \
    echo '/system/bin/integrity-bypass.sh' >> /system/bin/container-init.sh && \
    echo '/system/bin/gps-injection.sh' >> /system/bin/container-init.sh && \
    chmod +x /system/bin/container-init.sh

# Health check script
COPY ../../health-checks/android-health.sh /usr/local/bin/health-check.sh
RUN chmod +x /usr/local/bin/health-check.sh

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD /usr/local/bin/health-check.sh

# Expose ADB port
EXPOSE 5555

# Set entrypoint
ENTRYPOINT ["/system/bin/container-init.sh"]
CMD ["/init"]