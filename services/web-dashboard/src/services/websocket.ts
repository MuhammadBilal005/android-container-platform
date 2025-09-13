import { io, Socket } from 'socket.io-client';
import { WebSocketEvent, InstanceStatusEvent, MetricsUpdateEvent, LogEvent } from '@/types';

class WebSocketService {
  private socket: Socket | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;

  constructor(private url: string = process.env.REACT_APP_WS_URL || 'http://localhost:3000') {}

  connect(token?: string): Promise<void> {
    if (this.socket?.connected || this.isConnecting) {
      return Promise.resolve();
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        const socketOptions: any = {
          transports: ['websocket', 'polling'],
          timeout: 20000,
          forceNew: true,
        };

        // Add authentication token if provided
        if (token) {
          socketOptions.auth = { token };
        }

        this.socket = io(this.url, socketOptions);

        this.socket.on('connect', () => {
          console.log('WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          resolve();
        });

        this.socket.on('disconnect', (reason) => {
          console.log('WebSocket disconnected:', reason);
          this.isConnecting = false;
          
          if (reason === 'io server disconnect') {
            // Server disconnected, try to reconnect
            this.scheduleReconnect();
          }
        });

        this.socket.on('connect_error', (error) => {
          console.error('WebSocket connection error:', error);
          this.isConnecting = false;
          
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          } else {
            reject(error);
          }
        });

        // Instance status updates
        this.socket.on('instance_status', (data: InstanceStatusEvent['data']) => {
          this.emit('instance_status', data);
        });

        // Metrics updates
        this.socket.on('metrics_update', (data: MetricsUpdateEvent['data']) => {
          this.emit('metrics_update', data);
        });

        // Log entries
        this.socket.on('log_entry', (data: LogEvent['data']) => {
          this.emit('log_entry', data);
        });

        // Bulk operation updates
        this.socket.on('bulk_operation_update', (data: any) => {
          this.emit('bulk_operation_update', data);
        });

        // Health check updates
        this.socket.on('health_update', (data: any) => {
          this.emit('health_update', data);
        });

        // System alerts
        this.socket.on('system_alert', (data: any) => {
          this.emit('system_alert', data);
        });

        // Error notifications
        this.socket.on('error_notification', (data: any) => {
          this.emit('error_notification', data);
        });

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.listeners.clear();
    this.isConnecting = false;
    this.reconnectAttempts = 0;
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      if (!this.socket?.connected && !this.isConnecting) {
        const token = localStorage.getItem('auth_token');
        this.connect(token || undefined).catch(console.error);
      }
    }, delay);
  }

  // Subscribe to specific events
  subscribe(event: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    
    this.listeners.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.unsubscribe(event, callback);
    };
  }

  // Unsubscribe from events
  unsubscribe(event: string, callback: (data: any) => void): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(callback);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
      }
    }
  }

  // Emit events to subscribers
  private emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${event}:`, error);
        }
      });
    }
  }

  // Send data to server
  emit_to_server(event: string, data: any): void {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('Cannot emit event - WebSocket not connected');
    }
  }

  // Join specific rooms for targeted updates
  joinRoom(room: string): void {
    this.emit_to_server('join_room', { room });
  }

  leaveRoom(room: string): void {
    this.emit_to_server('leave_room', { room });
  }

  // Subscribe to instance-specific updates
  subscribeToInstance(instanceId: string): void {
    this.joinRoom(`instance:${instanceId}`);
  }

  unsubscribeFromInstance(instanceId: string): void {
    this.leaveRoom(`instance:${instanceId}`);
  }

  // Subscribe to bulk operation updates
  subscribeToBulkOperation(operationId: string): void {
    this.joinRoom(`bulk_operation:${operationId}`);
  }

  unsubscribeFromBulkOperation(operationId: string): void {
    this.leaveRoom(`bulk_operation:${operationId}`);
  }

  // Connection status
  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  getConnectionState(): 'connected' | 'disconnected' | 'connecting' {
    if (this.isConnecting) return 'connecting';
    if (this.socket?.connected) return 'connected';
    return 'disconnected';
  }

  // Heartbeat/ping functionality
  ping(): Promise<number> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      const startTime = Date.now();
      
      this.socket.emit('ping', startTime, (response: any) => {
        const latency = Date.now() - startTime;
        resolve(latency);
      });
    });
  }
}

// Create singleton instance
export const websocketService = new WebSocketService();
export default websocketService;