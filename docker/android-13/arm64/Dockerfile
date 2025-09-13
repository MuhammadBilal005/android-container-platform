# Android 13 ARM64 Container with Device Spoofing
FROM redroid/redroid:13.0.0-latest

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
ENV ANDROID_VERSION=13
ENV ARCH=arm64
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

# Install Magisk for root management
RUN cd /tmp && \
    wget https://github.com/topjohnwu/Magisk/releases/download/v26.4/Magisk-v26.4.apk -O magisk.apk && \
    unzip magisk.apk lib/arm64-v8a/libmagisk64.so -d magisk && \
    cp magisk/lib/arm64-v8a/libmagisk64.so /system/bin/magisk && \
    chmod 755 /system/bin/magisk && \
    rm -rf /tmp/magisk*

# Install LSPosed framework for system modifications
RUN cd /tmp && \
    wget https://github.com/LSPosed/LSPosed/releases/download/v1.9.2/LSPosed-v1.9.2-7024-zygisk-release.zip -O lsposed.zip && \
    unzip lsposed.zip -d /system/framework/ && \
    rm lsposed.zip

# Install Play Integrity Fix (Android 13 specific)
RUN cd /tmp && \
    wget https://github.com/chiteroman/PlayIntegrityFix/releases/download/v15.9/PlayIntegrityFix-v15.9.zip -O pif.zip && \
    mkdir -p /data/adb/modules/playintegrityfix && \
    unzip pif.zip -d /data/adb/modules/playintegrityfix/ && \
    rm pif.zip

# Install Tricky Store for advanced Play Integrity bypass
RUN cd /tmp && \
    wget https://github.com/5ec1cff/TrickyStore/releases/download/v1.2.0/app-release.apk -O trickystore.apk && \
    mkdir -p /system/priv-app/TrickyStore && \
    cp trickystore.apk /system/priv-app/TrickyStore/TrickyStore.apk && \
    chmod 644 /system/priv-app/TrickyStore/TrickyStore.apk && \
    rm trickystore.apk

# Configure system properties for device spoofing (Android 13 Samsung Galaxy S23)
RUN echo "# Device Spoofing Properties for Android 13" >> /system/build.prop && \
    echo "ro.product.brand=samsung" >> /system/build.prop && \
    echo "ro.product.name=SM-S911B" >> /system/build.prop && \
    echo "ro.product.model=Galaxy S23" >> /system/build.prop && \
    echo "ro.product.manufacturer=samsung" >> /system/build.prop && \
    echo "ro.product.device=dm1q" >> /system/build.prop && \
    echo "ro.build.fingerprint=samsung/dm1qxxx/dm1q:13/TP1A.220624.014/S911BXXU3AWGC:user/release-keys" >> /system/build.prop && \
    echo "ro.build.description=dm1qxxx-user 13 TP1A.220624.014 S911BXXU3AWGC release-keys" >> /system/build.prop && \
    echo "ro.system.build.version.release=13" >> /system/build.prop && \
    echo "ro.build.version.release=13" >> /system/build.prop && \
    echo "ro.build.version.sdk=33" >> /system/build.prop

# Android 13 specific security features bypass
RUN echo "ro.debuggable=0" >> /system/build.prop && \
    echo "ro.secure=1" >> /system/build.prop && \
    echo "ro.boot.verifiedbootstate=green" >> /system/build.prop && \
    echo "ro.boot.flash.locked=1" >> /system/build.prop && \
    echo "ro.boot.veritymode=enforcing" >> /system/build.prop && \
    echo "ro.boot.warranty_bit=0" >> /system/build.prop && \
    echo "ro.warranty_bit=0" >> /system/build.prop

# Install Shamiko for advanced hiding
RUN mkdir -p /data/adb/modules/shamiko && \
    echo "id=shamiko" > /data/adb/modules/shamiko/module.prop && \
    echo "name=Shamiko" >> /data/adb/modules/shamiko/module.prop && \
    echo "version=v0.7.4" >> /data/adb/modules/shamiko/module.prop && \
    echo "versionCode=384" >> /data/adb/modules/shamiko/module.prop && \
    echo "author=LSPosed Developers" >> /data/adb/modules/shamiko/module.prop && \
    echo "description=Hide Magisk better" >> /data/adb/modules/shamiko/module.prop

# Configure Themed Icons and Material You bypass
RUN echo "persist.sys.themed_icons_overlay_enabled=false" >> /system/build.prop && \
    echo "ro.config.themed_system_ui=false" >> /system/build.prop

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