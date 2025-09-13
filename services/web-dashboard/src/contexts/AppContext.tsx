import React, { createContext, useContext, useReducer, ReactNode, useEffect } from 'react';
import { DashboardState, AndroidInstance, BulkOperation, AppError } from '@/types';
import websocketService from '@/services/websocket';
import { useAuth } from './AuthContext';

// App Context Type
interface AppContextType {
  // Dashboard State
  dashboardState: DashboardState;
  
  // Data
  instances: AndroidInstance[];
  bulkOperations: BulkOperation[];
  
  // UI State
  loading: boolean;
  error: AppError | null;
  
  // Actions
  setSelectedInstances: (instanceIds: string[]) => void;
  setBulkOperations: (operations: BulkOperation[]) => void;
  setFilters: (filters: DashboardState['filters']) => void;
  setViewMode: (mode: 'grid' | 'list') => void;
  setSorting: (sortBy: string, sortOrder: 'asc' | 'desc') => void;
  updateInstance: (instance: AndroidInstance) => void;
  removeInstance: (instanceId: string) => void;
  addInstance: (instance: AndroidInstance) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: AppError | null) => void;
  clearError: () => void;
}

// App Actions
type AppAction =
  | { type: 'SET_SELECTED_INSTANCES'; payload: string[] }
  | { type: 'SET_BULK_OPERATIONS'; payload: BulkOperation[] }
  | { type: 'SET_FILTERS'; payload: DashboardState['filters'] }
  | { type: 'SET_VIEW_MODE'; payload: 'grid' | 'list' }
  | { type: 'SET_SORTING'; payload: { sortBy: string; sortOrder: 'asc' | 'desc' } }
  | { type: 'SET_INSTANCES'; payload: AndroidInstance[] }
  | { type: 'UPDATE_INSTANCE'; payload: AndroidInstance }
  | { type: 'REMOVE_INSTANCE'; payload: string }
  | { type: 'ADD_INSTANCE'; payload: AndroidInstance }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: AppError | null }
  | { type: 'CLEAR_ERROR' }
  | { type: 'UPDATE_BULK_OPERATION'; payload: BulkOperation };

// Initial State
const initialDashboardState: DashboardState = {
  selectedInstances: [],
  bulkOperations: [],
  filters: {},
  viewMode: 'grid',
  sortBy: 'name',
  sortOrder: 'asc',
};

interface AppState {
  dashboardState: DashboardState;
  instances: AndroidInstance[];
  bulkOperations: BulkOperation[];
  loading: boolean;
  error: AppError | null;
}

const initialState: AppState = {
  dashboardState: initialDashboardState,
  instances: [],
  bulkOperations: [],
  loading: false,
  error: null,
};

// App Reducer
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_SELECTED_INSTANCES':
      return {
        ...state,
        dashboardState: {
          ...state.dashboardState,
          selectedInstances: action.payload,
        },
      };

    case 'SET_BULK_OPERATIONS':
      return {
        ...state,
        bulkOperations: action.payload,
        dashboardState: {
          ...state.dashboardState,
          bulkOperations: action.payload,
        },
      };

    case 'UPDATE_BULK_OPERATION':
      const updatedOperations = state.bulkOperations.map(op =>
        op.id === action.payload.id ? action.payload : op
      );
      return {
        ...state,
        bulkOperations: updatedOperations,
        dashboardState: {
          ...state.dashboardState,
          bulkOperations: updatedOperations,
        },
      };

    case 'SET_FILTERS':
      return {
        ...state,
        dashboardState: {
          ...state.dashboardState,
          filters: action.payload,
        },
      };

    case 'SET_VIEW_MODE':
      return {
        ...state,
        dashboardState: {
          ...state.dashboardState,
          viewMode: action.payload,
        },
      };

    case 'SET_SORTING':
      return {
        ...state,
        dashboardState: {
          ...state.dashboardState,
          sortBy: action.payload.sortBy,
          sortOrder: action.payload.sortOrder,
        },
      };

    case 'SET_INSTANCES':
      return {
        ...state,
        instances: action.payload,
      };

    case 'UPDATE_INSTANCE':
      return {
        ...state,
        instances: state.instances.map(instance =>
          instance.id === action.payload.id ? action.payload : instance
        ),
      };

    case 'REMOVE_INSTANCE':
      return {
        ...state,
        instances: state.instances.filter(instance => instance.id !== action.payload),
        dashboardState: {
          ...state.dashboardState,
          selectedInstances: state.dashboardState.selectedInstances.filter(
            id => id !== action.payload
          ),
        },
      };

    case 'ADD_INSTANCE':
      return {
        ...state,
        instances: [...state.instances, action.payload],
      };

    case 'SET_LOADING':
      return {
        ...state,
        loading: action.payload,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };

    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };

    default:
      return state;
  }
}

// Create Context
const AppContext = createContext<AppContextType | undefined>(undefined);

// App Provider Props
interface AppProviderProps {
  children: ReactNode;
}

// App Provider Component
export function AppProvider({ children }: AppProviderProps) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const { isAuthenticated } = useAuth();

  // Setup WebSocket listeners
  useEffect(() => {
    if (!isAuthenticated) return;

    // Instance status updates
    const unsubscribeInstanceStatus = websocketService.subscribe(
      'instance_status',
      (data) => {
        dispatch({
          type: 'UPDATE_INSTANCE',
          payload: data.instance,
        });
      }
    );

    // Bulk operation updates
    const unsubscribeBulkOperation = websocketService.subscribe(
      'bulk_operation_update',
      (data) => {
        dispatch({
          type: 'UPDATE_BULK_OPERATION',
          payload: data,
        });
      }
    );

    // System alerts (converted to errors)
    const unsubscribeSystemAlert = websocketService.subscribe(
      'system_alert',
      (data) => {
        dispatch({
          type: 'SET_ERROR',
          payload: {
            code: 'SYSTEM_ALERT',
            message: data.message,
            details: data,
            timestamp: new Date().toISOString(),
          },
        });
      }
    );

    // Error notifications
    const unsubscribeErrorNotification = websocketService.subscribe(
      'error_notification',
      (data) => {
        dispatch({
          type: 'SET_ERROR',
          payload: {
            code: data.code || 'UNKNOWN_ERROR',
            message: data.message,
            details: data.details,
            timestamp: new Date().toISOString(),
          },
        });
      }
    );

    // Cleanup function
    return () => {
      unsubscribeInstanceStatus();
      unsubscribeBulkOperation();
      unsubscribeSystemAlert();
      unsubscribeErrorNotification();
    };
  }, [isAuthenticated]);

  // Load dashboard preferences from localStorage
  useEffect(() => {
    const savedPreferences = localStorage.getItem('dashboard_preferences');
    if (savedPreferences) {
      try {
        const preferences = JSON.parse(savedPreferences);
        
        if (preferences.viewMode) {
          dispatch({ type: 'SET_VIEW_MODE', payload: preferences.viewMode });
        }
        
        if (preferences.sortBy && preferences.sortOrder) {
          dispatch({
            type: 'SET_SORTING',
            payload: {
              sortBy: preferences.sortBy,
              sortOrder: preferences.sortOrder,
            },
          });
        }
        
        if (preferences.filters) {
          dispatch({ type: 'SET_FILTERS', payload: preferences.filters });
        }
      } catch (error) {
        console.error('Failed to load dashboard preferences:', error);
      }
    }
  }, []);

  // Save dashboard preferences to localStorage
  useEffect(() => {
    const preferences = {
      viewMode: state.dashboardState.viewMode,
      sortBy: state.dashboardState.sortBy,
      sortOrder: state.dashboardState.sortOrder,
      filters: state.dashboardState.filters,
    };
    
    localStorage.setItem('dashboard_preferences', JSON.stringify(preferences));
  }, [state.dashboardState]);

  // Actions
  const setSelectedInstances = (instanceIds: string[]) => {
    dispatch({ type: 'SET_SELECTED_INSTANCES', payload: instanceIds });
  };

  const setBulkOperations = (operations: BulkOperation[]) => {
    dispatch({ type: 'SET_BULK_OPERATIONS', payload: operations });
  };

  const setFilters = (filters: DashboardState['filters']) => {
    dispatch({ type: 'SET_FILTERS', payload: filters });
  };

  const setViewMode = (mode: 'grid' | 'list') => {
    dispatch({ type: 'SET_VIEW_MODE', payload: mode });
  };

  const setSorting = (sortBy: string, sortOrder: 'asc' | 'desc') => {
    dispatch({ type: 'SET_SORTING', payload: { sortBy, sortOrder } });
  };

  const updateInstance = (instance: AndroidInstance) => {
    dispatch({ type: 'UPDATE_INSTANCE', payload: instance });
  };

  const removeInstance = (instanceId: string) => {
    dispatch({ type: 'REMOVE_INSTANCE', payload: instanceId });
  };

  const addInstance = (instance: AndroidInstance) => {
    dispatch({ type: 'ADD_INSTANCE', payload: instance });
  };

  const setLoading = (loading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: loading });
  };

  const setError = (error: AppError | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  // Context value
  const contextValue: AppContextType = {
    dashboardState: state.dashboardState,
    instances: state.instances,
    bulkOperations: state.bulkOperations,
    loading: state.loading,
    error: state.error,
    setSelectedInstances,
    setBulkOperations,
    setFilters,
    setViewMode,
    setSorting,
    updateInstance,
    removeInstance,
    addInstance,
    setLoading,
    setError,
    clearError,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}

// Custom hook to use app context
export function useApp(): AppContextType {
  const context = useContext(AppContext);
  
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  
  return context;
}

export default AppContext;