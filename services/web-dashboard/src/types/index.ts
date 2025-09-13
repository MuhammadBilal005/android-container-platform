// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

// Authentication Types
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
  createdAt: string;
  lastLogin?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  token: string;
}

// Container Instance Types
export interface AndroidInstance {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'starting' | 'stopping' | 'error';
  androidVersion: string;
  architecture: 'arm64' | 'x86_64';
  deviceProfile: DeviceProfile;
  location: GeoLocation;
  network: NetworkConfig;
  resources: ResourceUsage;
  createdAt: string;
  updatedAt: string;
  adbPort: number;
  dockerId?: string;
  health: HealthStatus;
}

export interface DeviceProfile {
  id: string;
  name: string;
  manufacturer: string;
  brand: string;
  model: string;
  androidVersion: string;
  buildFingerprint: string;
  features: string[];
  display: {
    resolution: string;
    density: number;
    widthPx: number;
    heightPx: number;
  };
  spoofingConfig: {
    imeiPattern: string;
    serialPattern: string;
    macAddressOui: string;
    userAgent: string;
  };
}

export interface GeoLocation {
  latitude: number;
  longitude: number;
  altitude: number;
  accuracy: number;
  provider: string;
  timestamp: string;
}

export interface NetworkConfig {
  proxyEnabled: boolean;
  proxyHost?: string;
  proxyPort?: number;
  proxyAuth?: {
    username: string;
    password: string;
  };
  dnsServers: string[];
  vpnEnabled: boolean;
  vpnConfig?: {
    server: string;
    protocol: string;
    credentials: any;
  };
}

export interface ResourceUsage {
  cpu: {
    usage: number;
    limit: number;
  };
  memory: {
    used: number;
    total: number;
    limit: number;
  };
  disk: {
    used: number;
    total: number;
  };
  network: {
    bytesIn: number;
    bytesOut: number;
    packetsIn: number;
    packetsOut: number;
  };
}

export interface HealthStatus {
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  timestamp: string;
  checks: {
    [key: string]: {
      status: 'pass' | 'fail' | 'warn';
      message: string;
      duration: number;
    };
  };
}

// Metrics and Analytics Types
export interface MetricDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface InstanceMetrics {
  instanceId: string;
  cpu: MetricDataPoint[];
  memory: MetricDataPoint[];
  network: MetricDataPoint[];
  disk: MetricDataPoint[];
}

export interface SystemMetrics {
  totalInstances: number;
  runningInstances: number;
  healthyInstances: number;
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkTraffic: number;
}

// Bulk Operations Types
export interface BulkOperation {
  id: string;
  type: 'start' | 'stop' | 'restart' | 'delete' | 'update';
  instanceIds: string[];
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startedAt: string;
  completedAt?: string;
  results: BulkOperationResult[];
}

export interface BulkOperationResult {
  instanceId: string;
  status: 'success' | 'error';
  message?: string;
}

// Log Entry Types
export interface LogEntry {
  id: string;
  instanceId: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: string;
  message: string;
  metadata?: any;
}

export interface LogFilter {
  instanceIds?: string[];
  levels?: string[];
  sources?: string[];
  startDate?: string;
  endDate?: string;
  search?: string;
}

// WebSocket Event Types
export interface WebSocketEvent {
  type: string;
  data: any;
  timestamp: string;
}

export interface InstanceStatusEvent extends WebSocketEvent {
  type: 'instance_status';
  data: {
    instanceId: string;
    status: AndroidInstance['status'];
    health: HealthStatus;
  };
}

export interface MetricsUpdateEvent extends WebSocketEvent {
  type: 'metrics_update';
  data: {
    instanceId: string;
    metrics: Partial<ResourceUsage>;
  };
}

export interface LogEvent extends WebSocketEvent {
  type: 'log_entry';
  data: LogEntry;
}

// UI State Types
export interface DashboardState {
  selectedInstances: string[];
  bulkOperations: BulkOperation[];
  filters: {
    status?: string[];
    androidVersion?: string[];
    deviceProfile?: string[];
  };
  viewMode: 'grid' | 'list';
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

// Form Types
export interface CreateInstanceForm {
  name: string;
  androidVersion: string;
  architecture: 'arm64' | 'x86_64';
  deviceProfileId: string;
  location: {
    latitude: number;
    longitude: number;
    altitude: number;
  };
  network: Partial<NetworkConfig>;
  resources: {
    cpuLimit: number;
    memoryLimit: number;
    diskLimit: number;
  };
}

export interface UpdateInstanceForm extends Partial<CreateInstanceForm> {
  id: string;
}

// Configuration Types
export interface AppConfig {
  apiBaseUrl: string;
  websocketUrl: string;
  mapProvider: 'openstreetmap' | 'google' | 'mapbox';
  mapApiKey?: string;
  refreshInterval: number;
  maxLogEntries: number;
  theme: 'light' | 'dark' | 'auto';
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

// Pagination Types
export interface PaginationParams {
  page: number;
  limit: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

// Chart Data Types
export interface ChartDataPoint {
  x: string | number;
  y: number;
  label?: string;
  color?: string;
}

export interface ChartSeries {
  name: string;
  data: ChartDataPoint[];
  color?: string;
}

// Map Types
export interface MapMarker {
  id: string;
  position: [number, number];
  popup: string;
  icon?: string;
  color?: string;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}