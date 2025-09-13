FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    iptables \
    iproute2 \
    dnsutils \
    curl \
    netcat-openbsd \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

# Enable IP forwarding and network capabilities
RUN echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]