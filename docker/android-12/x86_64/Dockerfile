# Android 12 x86_64 Container with Device Spoofing
FROM redroid/redroid:12.0.0-x86_64-latest

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
ENV ANDROID_VERSION=12
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

# Install Play Integrity Fix (Android 12 specific)
RUN cd /tmp && \
    wget https://github.com/chiteroman/PlayIntegrityFix/releases/download/v15.9/PlayIntegrityFix-v15.9.zip -O pif.zip && \
    mkdir -p /data/adb/modules/playintegrityfix && \
    unzip pif.zip -d /data/adb/modules/playintegrityfix/ && \
    rm pif.zip

# Configure system properties for device spoofing (Android 12 Pixel 6)
RUN echo "# Device Spoofing Properties for Android 12" >> /system/build.prop && \
    echo "ro.product.brand=google" >> /system/build.prop && \
    echo "ro.product.name=oriole" >> /system/build.prop && \
    echo "ro.product.model=Pixel 6" >> /system/build.prop && \
    echo "ro.product.manufacturer=Google" >> /system/build.prop && \
    echo "ro.product.device=oriole" >> /system/build.prop && \
    echo "ro.build.fingerprint=google/oriole/oriole:12/SQ3A.220705.004/8836240:user/release-keys" >> /system/build.prop && \
    echo "ro.build.description=oriole-user 12 SQ3A.220705.004 8836240 release-keys" >> /system/build.prop && \
    echo "ro.system.build.version.release=12" >> /system/build.prop && \
    echo "ro.build.version.release=12" >> /system/build.prop && \
    echo "ro.build.version.sdk=31" >> /system/build.prop

# Android 12 specific security bypass
RUN mkdir -p /data/adb/modules/shamiko && \
    echo "id=shamiko" > /data/adb/modules/shamiko/module.prop && \
    echo "name=Shamiko" >> /data/adb/modules/shamiko/module.prop && \
    echo "version=v0.7.4" >> /data/adb/modules/shamiko/module.prop && \
    echo "versionCode=384" >> /data/adb/modules/shamiko/module.prop && \
    echo "author=LSPosed Developers" >> /data/adb/modules/shamiko/module.prop && \
    echo "description=Hide Magisk better" >> /data/adb/modules/shamiko/module.prop

# Configure Android 12 Material You theming bypass
RUN echo "persist.sys.theme=0" >> /system/build.prop && \
    echo "ro.boot.dynamic_partitions=true" >> /system/build.prop && \
    echo "ro.build.ab_update=true" >> /system/build.prop

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