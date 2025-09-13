# Deployment Guide

This guide covers deploying the Android Container Platform in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Compose Deployment](#docker-compose-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Configuration](#configuration)
5. [Security Hardening](#security-hardening)
6. [Monitoring Setup](#monitoring-setup)
7. [Backup and Recovery](#backup-and-recovery)
8. [Scaling](#scaling)

## Prerequisites

### Hardware Requirements

**Minimum for Development:**
- 8GB RAM
- 4 CPU cores
- 50GB storage
- Docker support

**Recommended for Production:**
- 32GB+ RAM
- 16+ CPU cores
- 500GB+ SSD storage
- Hardware virtualization (KVM support)
- High-speed network connection

### Software Requirements

- **Operating System**: Ubuntu 20.04+ LTS or RHEL 8+
- **Container Runtime**: Docker 20.10+ or containerd
- **Orchestration**: Docker Compose 2.0+ or Kubernetes 1.20+
- **Database**: PostgreSQL 13+ (can be external)
- **Cache**: Redis 6.0+ (can be external)

### Network Requirements

- **Ports**: 80, 443, 3000-3001, 5432, 6379, 8001-8004, 9090
- **Outbound**: HTTPS to package repositories and image registries
- **Internal**: Service-to-service communication
- **Optional**: VPN access for management

## Docker Compose Deployment

### Quick Development Setup

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-org/android-container-platform.git
   cd android-container-platform
   ```

2. **Setup environment:**
   ```bash
   make setup
   ```

3. **Start services:**
   ```bash
   make dev
   ```

### Production Docker Compose

1. **Create production configuration:**
   ```bash
   cp docker-compose.yml docker-compose.prod.yml
   ```

2. **Update production settings:**
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   
   services:
     postgres:
       environment:
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       restart: unless-stopped
       deploy:
         resources:
           limits:
             cpus: '2.0'
             memory: 4G
           reservations:
             cpus: '1.0'
             memory: 2G
     
     redis:
       restart: unless-stopped
       deploy:
         resources:
           limits:
             cpus: '0.5'
             memory: 1G
   
     api-gateway:
       environment:
         JWT_SECRET: ${JWT_SECRET}
         DATABASE_URL: ${DATABASE_URL}
       restart: unless-stopped
       deploy:
         replicas: 3
         resources:
           limits:
             cpus: '1.0'
             memory: 1G
   ```

3. **Set environment variables:**
   ```bash
   # Create .env file
   cat > .env << EOF
   POSTGRES_PASSWORD=$(openssl rand -base64 32)
   JWT_SECRET=$(openssl rand -base64 32)
   DATABASE_URL=postgresql://acp_user:${POSTGRES_PASSWORD}@postgres:5432/android_platform
   ENVIRONMENT=production
   EOF
   ```

4. **Deploy:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Verify deployment:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   curl http://localhost:3000/health
   ```

## Kubernetes Deployment

### Cluster Setup

1. **Create namespace:**
   ```bash
   kubectl create namespace android-platform
   kubectl label namespace android-platform name=android-platform
   ```

2. **Setup RBAC:**
   ```bash
   kubectl apply -f k8s/rbac.yaml
   ```

3. **Deploy configuration:**
   ```bash
   # Update secrets first
   kubectl create secret generic platform-secrets \
     --from-literal=postgres-password=$(openssl rand -base64 32) \
     --from-literal=jwt-secret=$(openssl rand -base64 32) \
     -n android-platform
   
   kubectl apply -f k8s/configmap.yaml
   ```

### Database Deployment

1. **Deploy PostgreSQL:**
   ```bash
   kubectl apply -f k8s/postgres.yaml
   ```

2. **Wait for database to be ready:**
   ```bash
   kubectl wait --for=condition=ready pod -l app=postgres -n android-platform --timeout=300s
   ```

3. **Initialize database:**
   ```bash
   kubectl exec -it deployment/postgres -n android-platform -- \
     psql -U acp_user -d android_platform -f /docker-entrypoint-initdb.d/init.sql
   ```

### Cache Deployment

1. **Deploy Redis:**
   ```bash
   kubectl apply -f k8s/redis.yaml
   ```

2. **Verify Redis:**
   ```bash
   kubectl wait --for=condition=ready pod -l app=redis -n android-platform --timeout=120s
   ```

### Application Services

1. **Deploy core services:**
   ```bash
   kubectl apply -f k8s/services.yaml
   ```

2. **Check deployment status:**
   ```bash
   kubectl get pods -n android-platform -w
   ```

3. **Verify service health:**
   ```bash
   kubectl get services -n android-platform
   
   # Port forward for testing
   kubectl port-forward svc/api-gateway 3000:80 -n android-platform
   curl http://localhost:3000/health
   ```

### Monitoring Deployment

1. **Deploy monitoring stack:**
   ```bash
   kubectl apply -f k8s/monitoring.yaml
   ```

2. **Access Grafana:**
   ```bash
   kubectl port-forward svc/grafana 3001:80 -n android-platform
   # Open http://localhost:3001 (admin/admin)
   ```

## Configuration

### Environment Variables

Create a comprehensive environment configuration:

```yaml
# k8s/configmap-prod.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: platform-config
  namespace: android-platform
data:
  # Database Configuration
  DATABASE_URL: "postgresql://acp_user:$(POSTGRES_PASSWORD)@postgres:5432/android_platform"
  DATABASE_POOL_SIZE: "20"
  DATABASE_MAX_OVERFLOW: "30"
  
  # Redis Configuration
  REDIS_URL: "redis://redis:6379/0"
  REDIS_POOL_SIZE: "10"
  
  # Service URLs
  IDENTITY_SERVICE_URL: "http://identity-manager:8001"
  LOCATION_SERVICE_URL: "http://location-manager:8002"
  NETWORK_SERVICE_URL: "http://network-manager:8003"
  LIFECYCLE_SERVICE_URL: "http://lifecycle-manager:8004"
  
  # Security Configuration
  JWT_EXPIRATION_HOURS: "24"
  RATE_LIMIT_PER_HOUR: "1000"
  BCRYPT_ROUNDS: "12"
  
  # Platform Limits
  MAX_INSTANCES_PER_USER: "10"
  DEFAULT_INSTANCE_MEMORY: "4G"
  DEFAULT_INSTANCE_CPU: "2.0"
  
  # Monitoring
  METRICS_ENABLED: "true"
  LOG_LEVEL: "INFO"
  
  # Feature Flags
  ENABLE_DEVICE_SPOOFING: "true"
  ENABLE_LOCATION_INJECTION: "true"
  ENABLE_NETWORK_ISOLATION: "true"
```

### TLS/SSL Configuration

1. **Generate certificates:**
   ```bash
   # Self-signed for testing
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout tls.key -out tls.crt \
     -subj "/CN=android-platform.local"
   
   kubectl create secret tls platform-tls \
     --cert=tls.crt --key=tls.key \
     -n android-platform
   ```

2. **Configure ingress:**
   ```yaml
   # k8s/ingress.yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: platform-ingress
     namespace: android-platform
     annotations:
       kubernetes.io/ingress.class: nginx
       cert-manager.io/cluster-issuer: letsencrypt-prod
   spec:
     tls:
     - hosts:
       - api.android-platform.com
       secretName: platform-tls
     rules:
     - host: api.android-platform.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: api-gateway
               port:
                 number: 80
   ```

## Security Hardening

### Network Security

1. **Network policies:**
   ```yaml
   # k8s/network-policy.yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: platform-network-policy
     namespace: android-platform
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: android-platform
       ports:
       - protocol: TCP
         port: 8001
       - protocol: TCP
         port: 8002
       - protocol: TCP
         port: 8003
       - protocol: TCP
         port: 8004
     egress:
     - to: []
       ports:
       - protocol: TCP
         port: 53
       - protocol: UDP
         port: 53
     - to:
       - namespaceSelector:
           matchLabels:
             name: android-platform
   ```

2. **Pod security policies:**
   ```yaml
   # k8s/pod-security-policy.yaml
   apiVersion: policy/v1beta1
   kind: PodSecurityPolicy
   metadata:
     name: platform-psp
   spec:
     privileged: false
     allowPrivilegeEscalation: false
     requiredDropCapabilities:
       - ALL
     volumes:
       - 'configMap'
       - 'emptyDir'
       - 'projected'
       - 'secret'
       - 'downwardAPI'
       - 'persistentVolumeClaim'
     runAsUser:
       rule: 'MustRunAsNonRoot'
     seLinux:
       rule: 'RunAsAny'
     fsGroup:
       rule: 'RunAsAny'
   ```

### Container Security

1. **Security contexts:**
   ```yaml
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     fsGroup: 2000
     capabilities:
       drop:
       - ALL
     readOnlyRootFilesystem: true
   ```

2. **Resource limits:**
   ```yaml
   resources:
     limits:
       cpu: 1000m
       memory: 2Gi
       ephemeral-storage: 1Gi
     requests:
       cpu: 100m
       memory: 256Mi
       ephemeral-storage: 100Mi
   ```

### Secrets Management

1. **External secrets operator:**
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
   ```

2. **HashiCorp Vault integration:**
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: SecretStore
   metadata:
     name: vault-backend
     namespace: android-platform
   spec:
     provider:
       vault:
         server: "https://vault.company.com"
         path: "secret"
         version: "v2"
         auth:
           kubernetes:
             mountPath: "kubernetes"
             role: "android-platform"
   ```

## Monitoring Setup

### Prometheus Configuration

1. **Extended Prometheus config:**
   ```yaml
   # monitoring/prometheus-prod.yml
   global:
     scrape_interval: 15s
     evaluation_interval: 15s
     external_labels:
       cluster: 'android-platform-prod'
       replica: '1'
   
   rule_files:
     - "alert_rules.yml"
     - "recording_rules.yml"
   
   alerting:
     alertmanagers:
     - static_configs:
       - targets:
         - alertmanager:9093
   
   scrape_configs:
     # Application metrics
     - job_name: 'api-gateway'
       kubernetes_sd_configs:
       - role: endpoints
         namespaces:
           names: ['android-platform']
       relabel_configs:
       - source_labels: [__meta_kubernetes_service_name]
         action: keep
         regex: api-gateway
     
     # Database metrics
     - job_name: 'postgres'
       static_configs:
       - targets: ['postgres-exporter:9187']
     
     # Redis metrics  
     - job_name: 'redis'
       static_configs:
       - targets: ['redis-exporter:9121']
     
     # Container metrics
     - job_name: 'cadvisor'
       kubernetes_sd_configs:
       - role: node
       relabel_configs:
       - target_label: __address__
         replacement: kubernetes.default.svc:443
       - source_labels: [__meta_kubernetes_node_name]
         regex: (.+)
         target_label: __metrics_path__
         replacement: /api/v1/nodes/${1}/proxy/metrics/cadvisor
   ```

2. **Custom recording rules:**
   ```yaml
   # monitoring/recording_rules.yml
   groups:
   - name: android_platform_recording_rules
     interval: 30s
     rules:
     - record: android_platform:instance_creation_rate
       expr: rate(android_instances_created_total[5m])
     
     - record: android_platform:instance_failure_rate
       expr: rate(android_instances_failed_total[5m])
     
     - record: android_platform:api_request_duration_p99
       expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
     
     - record: android_platform:resource_utilization
       expr: |
         (
           android_platform:total_cpu_usage / android_platform:total_cpu_limit
         ) * 100
   ```

### Grafana Dashboards

1. **Platform overview dashboard:**
   ```json
   {
     "dashboard": {
       "title": "Android Platform Overview",
       "panels": [
         {
           "title": "Active Instances",
           "type": "stat",
           "targets": [
             {
               "expr": "android_instances_active_total",
               "legendFormat": "Active Instances"
             }
           ]
         },
         {
           "title": "API Request Rate",
           "type": "graph",
           "targets": [
             {
               "expr": "rate(http_requests_total[5m])",
               "legendFormat": "{{method}} {{endpoint}}"
             }
           ]
         }
       ]
     }
   }
   ```

### Log Aggregation

1. **ELK Stack deployment:**
   ```bash
   helm repo add elastic https://helm.elastic.co
   helm install elasticsearch elastic/elasticsearch -n logging --create-namespace
   helm install kibana elastic/kibana -n logging
   helm install filebeat elastic/filebeat -n logging
   ```

2. **Fluent Bit configuration:**
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: fluent-bit-config
   data:
     fluent-bit.conf: |
       [SERVICE]
           Flush         1
           Log_Level     info
           Daemon        off
           Parsers_File  parsers.conf
       
       [INPUT]
           Name              tail
           Path              /var/log/containers/*android-platform*.log
           Parser            cri
           Tag               android.*
           Refresh_Interval  5
       
       [OUTPUT]
           Name  es
           Match *
           Host  elasticsearch
           Port  9200
           Index android-platform
   ```

## Backup and Recovery

### Database Backup

1. **Automated PostgreSQL backups:**
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: postgres-backup
     namespace: android-platform
   spec:
     schedule: "0 2 * * *"  # Daily at 2 AM
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: postgres-backup
               image: postgres:13
               command:
               - /bin/bash
               - -c
               - |
                 pg_dump -h postgres -U acp_user android_platform | \
                 gzip > /backup/android_platform_$(date +%Y%m%d_%H%M%S).sql.gz
               volumeMounts:
               - name: backup-storage
                 mountPath: /backup
               env:
               - name: PGPASSWORD
                 valueFrom:
                   secretKeyRef:
                     name: platform-secrets
                     key: postgres-password
             volumes:
             - name: backup-storage
               persistentVolumeClaim:
                 claimName: backup-pvc
             restartPolicy: OnFailure
   ```

2. **Backup retention script:**
   ```bash
   #!/bin/bash
   # cleanup-old-backups.sh
   
   BACKUP_DIR="/backup"
   RETENTION_DAYS=30
   
   find $BACKUP_DIR -name "android_platform_*.sql.gz" -mtime +$RETENTION_DAYS -delete
   
   # Log backup status
   echo "$(date): Cleaned up backups older than $RETENTION_DAYS days" >> /var/log/backup-cleanup.log
   ```

### Disaster Recovery

1. **Database restoration:**
   ```bash
   # Restore from backup
   kubectl exec -it deployment/postgres -n android-platform -- \
     pg_restore -h localhost -U acp_user -d android_platform /backup/latest_backup.sql.gz
   ```

2. **Full system restore:**
   ```bash
   # Restore persistent volumes
   kubectl apply -f backup/persistent-volumes.yaml
   
   # Restore application state
   kubectl apply -f k8s/
   
   # Verify restoration
   ./scripts/test-integrity.sh
   ./scripts/test-performance.sh
   ```

### Multi-Region Setup

1. **Database replication:**
   ```yaml
   # Primary region
   apiVersion: postgresql.cnpg.io/v1
   kind: Cluster
   metadata:
     name: postgres-primary
   spec:
     instances: 3
     primaryUpdateStrategy: unsupervised
     
     postgresql:
       parameters:
         wal_level: replica
         max_wal_senders: 10
         max_replication_slots: 10
   ```

2. **Cross-region backup:**
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: cross-region-backup
   spec:
     schedule: "0 6 * * *"  # Daily at 6 AM
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: backup-sync
               image: amazon/aws-cli
               command:
               - aws
               - s3
               - sync
               - /backup
               - s3://android-platform-backups-us-west-2/
   ```

## Scaling

### Horizontal Scaling

1. **Auto-scaling configuration:**
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: api-gateway-hpa
     namespace: android-platform
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: api-gateway
     minReplicas: 3
     maxReplicas: 20
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
     behavior:
       scaleUp:
         stabilizationWindowSeconds: 60
         policies:
         - type: Percent
           value: 100
           periodSeconds: 15
       scaleDown:
         stabilizationWindowSeconds: 300
         policies:
         - type: Percent
           value: 50
           periodSeconds: 60
   ```

### Vertical Scaling

1. **Vertical Pod Autoscaler:**
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: lifecycle-manager-vpa
     namespace: android-platform
   spec:
     targetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: lifecycle-manager
     updatePolicy:
       updateMode: "Auto"
     resourcePolicy:
       containerPolicies:
       - containerName: lifecycle-manager
         maxAllowed:
           cpu: 4
           memory: 8Gi
         minAllowed:
           cpu: 100m
           memory: 256Mi
   ```

### Cluster Scaling

1. **Node auto-scaling:**
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cluster-autoscaler-status
     namespace: kube-system
   data:
     cluster-autoscaler: |
       nodes.max: 50
       nodes.min: 5
       scale-down-delay-after-add: 10m
       scale-down-unneeded-time: 10m
   ```

2. **Multi-zone deployment:**
   ```yaml
   # Ensure pods are spread across zones
   spec:
     affinity:
       podAntiAffinity:
         preferredDuringSchedulingIgnoredDuringExecution:
         - weight: 100
           podAffinityTerm:
             labelSelector:
               matchExpressions:
               - key: app
                 operator: In
                 values:
                 - api-gateway
             topologyKey: topology.kubernetes.io/zone
   ```

This completes the comprehensive deployment guide. The platform is now ready for production use with proper security, monitoring, and scaling capabilities.