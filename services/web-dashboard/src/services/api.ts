import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  AndroidInstance, 
  ApiResponse, 
  BulkOperation, 
  CreateInstanceForm, 
  DeviceProfile, 
  InstanceMetrics, 
  LogEntry, 
  LogFilter, 
  LoginRequest, 
  LoginResponse, 
  PaginatedResponse, 
  PaginationParams, 
  SystemMetrics, 
  UpdateInstanceForm,
  User
} from '@/types';

class ApiService {
  private client: AxiosInstance;

  constructor(baseURL: string = process.env.REACT_APP_API_URL || 'http://localhost:3000') {
    this.client = axios.create({
      baseURL: `${baseURL}/api`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.client.post<ApiResponse<LoginResponse>>('/auth/login', credentials);
    return response.data.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<ApiResponse<User>>('/auth/me');
    return response.data.data;
  }

  async refreshToken(): Promise<string> {
    const response = await this.client.post<ApiResponse<{ token: string }>>('/auth/refresh');
    return response.data.data.token;
  }

  // Android Instances
  async getInstances(params?: PaginationParams): Promise<PaginatedResponse<AndroidInstance>> {
    const response = await this.client.get<ApiResponse<PaginatedResponse<AndroidInstance>>>('/instances', {
      params
    });
    return response.data.data;
  }

  async getInstance(id: string): Promise<AndroidInstance> {
    const response = await this.client.get<ApiResponse<AndroidInstance>>(`/instances/${id}`);
    return response.data.data;
  }

  async createInstance(data: CreateInstanceForm): Promise<AndroidInstance> {
    const response = await this.client.post<ApiResponse<AndroidInstance>>('/instances', data);
    return response.data.data;
  }

  async updateInstance(id: string, data: UpdateInstanceForm): Promise<AndroidInstance> {
    const response = await this.client.put<ApiResponse<AndroidInstance>>(`/instances/${id}`, data);
    return response.data.data;
  }

  async deleteInstance(id: string): Promise<void> {
    await this.client.delete(`/instances/${id}`);
  }

  async startInstance(id: string): Promise<AndroidInstance> {
    const response = await this.client.post<ApiResponse<AndroidInstance>>(`/instances/${id}/start`);
    return response.data.data;
  }

  async stopInstance(id: string): Promise<AndroidInstance> {
    const response = await this.client.post<ApiResponse<AndroidInstance>>(`/instances/${id}/stop`);
    return response.data.data;
  }

  async restartInstance(id: string): Promise<AndroidInstance> {
    const response = await this.client.post<ApiResponse<AndroidInstance>>(`/instances/${id}/restart`);
    return response.data.data;
  }

  // Bulk Operations
  async createBulkOperation(type: string, instanceIds: string[], options?: any): Promise<BulkOperation> {
    const response = await this.client.post<ApiResponse<BulkOperation>>('/bulk-operations', {
      type,
      instanceIds,
      options
    });
    return response.data.data;
  }

  async getBulkOperations(): Promise<BulkOperation[]> {
    const response = await this.client.get<ApiResponse<BulkOperation[]>>('/bulk-operations');
    return response.data.data;
  }

  async getBulkOperation(id: string): Promise<BulkOperation> {
    const response = await this.client.get<ApiResponse<BulkOperation>>(`/bulk-operations/${id}`);
    return response.data.data;
  }

  async cancelBulkOperation(id: string): Promise<void> {
    await this.client.post(`/bulk-operations/${id}/cancel`);
  }

  // Device Profiles
  async getDeviceProfiles(): Promise<DeviceProfile[]> {
    const response = await this.client.get<ApiResponse<DeviceProfile[]>>('/device-profiles');
    return response.data.data;
  }

  async getDeviceProfile(id: string): Promise<DeviceProfile> {
    const response = await this.client.get<ApiResponse<DeviceProfile>>(`/device-profiles/${id}`);
    return response.data.data;
  }

  async createDeviceProfile(data: Omit<DeviceProfile, 'id'>): Promise<DeviceProfile> {
    const response = await this.client.post<ApiResponse<DeviceProfile>>('/device-profiles', data);
    return response.data.data;
  }

  async updateDeviceProfile(id: string, data: Partial<DeviceProfile>): Promise<DeviceProfile> {
    const response = await this.client.put<ApiResponse<DeviceProfile>>(`/device-profiles/${id}`, data);
    return response.data.data;
  }

  async deleteDeviceProfile(id: string): Promise<void> {
    await this.client.delete(`/device-profiles/${id}`);
  }

  // Location Management
  async updateInstanceLocation(id: string, location: { latitude: number; longitude: number; altitude?: number }): Promise<void> {
    await this.client.put(`/instances/${id}/location`, location);
  }

  async simulateMovement(id: string, path: Array<{ latitude: number; longitude: number; duration: number }>): Promise<void> {
    await this.client.post(`/instances/${id}/simulate-movement`, { path });
  }

  async stopMovementSimulation(id: string): Promise<void> {
    await this.client.post(`/instances/${id}/stop-simulation`);
  }

  // Network Configuration
  async updateNetworkConfig(id: string, config: any): Promise<void> {
    await this.client.put(`/instances/${id}/network`, config);
  }

  async testProxyConnection(config: any): Promise<{ success: boolean; latency?: number; error?: string }> {
    const response = await this.client.post<ApiResponse<{ success: boolean; latency?: number; error?: string }>>('/network/test-proxy', config);
    return response.data.data;
  }

  // Metrics and Monitoring
  async getSystemMetrics(timeRange?: string): Promise<SystemMetrics> {
    const response = await this.client.get<ApiResponse<SystemMetrics>>('/metrics/system', {
      params: { timeRange }
    });
    return response.data.data;
  }

  async getInstanceMetrics(id: string, timeRange?: string): Promise<InstanceMetrics> {
    const response = await this.client.get<ApiResponse<InstanceMetrics>>(`/metrics/instances/${id}`, {
      params: { timeRange }
    });
    return response.data.data;
  }

  async getMultipleInstanceMetrics(ids: string[], timeRange?: string): Promise<InstanceMetrics[]> {
    const response = await this.client.post<ApiResponse<InstanceMetrics[]>>('/metrics/instances/batch', {
      instanceIds: ids,
      timeRange
    });
    return response.data.data;
  }

  // Logging
  async getLogs(filter?: LogFilter & PaginationParams): Promise<PaginatedResponse<LogEntry>> {
    const response = await this.client.get<ApiResponse<PaginatedResponse<LogEntry>>>('/logs', {
      params: filter
    });
    return response.data.data;
  }

  async getInstanceLogs(id: string, filter?: LogFilter & PaginationParams): Promise<PaginatedResponse<LogEntry>> {
    const response = await this.client.get<ApiResponse<PaginatedResponse<LogEntry>>>(`/instances/${id}/logs`, {
      params: filter
    });
    return response.data.data;
  }

  async exportLogs(filter?: LogFilter): Promise<Blob> {
    const response = await this.client.get('/logs/export', {
      params: filter,
      responseType: 'blob'
    });
    return response.data;
  }

  // Health Checks
  async checkInstanceHealth(id: string): Promise<any> {
    const response = await this.client.get<ApiResponse<any>>(`/instances/${id}/health`);
    return response.data.data;
  }

  async runDiagnostics(id: string): Promise<any> {
    const response = await this.client.post<ApiResponse<any>>(`/instances/${id}/diagnostics`);
    return response.data.data;
  }

  // Configuration
  async getSystemConfig(): Promise<any> {
    const response = await this.client.get<ApiResponse<any>>('/config');
    return response.data.data;
  }

  async updateSystemConfig(config: any): Promise<any> {
    const response = await this.client.put<ApiResponse<any>>('/config', config);
    return response.data.data;
  }

  // File Operations
  async downloadFile(instanceId: string, path: string): Promise<Blob> {
    const response = await this.client.get(`/instances/${instanceId}/files/download`, {
      params: { path },
      responseType: 'blob'
    });
    return response.data;
  }

  async uploadFile(instanceId: string, file: File, path: string): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', path);

    await this.client.post(`/instances/${instanceId}/files/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // Statistics and Analytics
  async getDashboardStats(): Promise<any> {
    const response = await this.client.get<ApiResponse<any>>('/stats/dashboard');
    return response.data.data;
  }

  async getUsageAnalytics(timeRange?: string): Promise<any> {
    const response = await this.client.get<ApiResponse<any>>('/analytics/usage', {
      params: { timeRange }
    });
    return response.data.data;
  }

  // Error Reporting
  async reportError(error: any, context?: any): Promise<void> {
    await this.client.post('/errors/report', { error, context });
  }
}

export const apiService = new ApiService();
export default apiService;