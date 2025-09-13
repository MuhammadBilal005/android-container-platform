import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Button,
  Alert,
  Paper,
  Tooltip,
  useTheme,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  NetworkCheck as NetworkIcon,
  Speed as SpeedIcon,
  AndroidOutlined,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar } from 'recharts';
import { useApp } from '@/contexts/AppContext';
import { useAuth } from '@/contexts/AuthContext';
import apiService from '@/services/api';
import websocketService from '@/services/websocket';
import { AndroidInstance, SystemMetrics, MetricDataPoint } from '@/types';

const Dashboard: React.FC = () => {
  const theme = useTheme();
  const { instances, setLoading, setError, clearError } = useApp();
  const { user } = useAuth();

  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<MetricDataPoint[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  // Status colors
  const statusColors = {
    running: theme.palette.success.main,
    stopped: theme.palette.grey[500],
    starting: theme.palette.warning.main,
    stopping: theme.palette.warning.main,
    error: theme.palette.error.main,
  };

  // Load dashboard data
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      clearError();

      // Load system metrics
      const metrics = await apiService.getSystemMetrics('1h');
      setSystemMetrics(metrics);

      // Load instances if not already loaded
      if (instances.length === 0) {
        await apiService.getInstances();
      }

    } catch (error: any) {
      console.error('Failed to load dashboard data:', error);
      setError({
        code: 'DASHBOARD_LOAD_ERROR',
        message: 'Failed to load dashboard data',
        details: error.message,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  // Refresh dashboard data
  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  // Load data on component mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  // Set up real-time metrics updates
  useEffect(() => {
    const unsubscribe = websocketService.subscribe('metrics_update', (data) => {
      // Update metrics history
      setMetricsHistory(prev => {
        const newHistory = [...prev, {
          timestamp: new Date().toISOString(),
          value: data.metrics.cpu?.usage || 0,
        }];
        
        // Keep only last 20 data points
        return newHistory.slice(-20);
      });
    });

    return unsubscribe;
  }, []);

  // Calculate summary statistics
  const runningInstances = instances.filter(i => i.status === 'running').length;
  const healthyInstances = instances.filter(i => i.health?.status === 'healthy').length;
  const errorInstances = instances.filter(i => i.status === 'error' || i.health?.status === 'critical').length;

  // Status distribution data for pie chart
  const statusDistribution = [
    { name: 'Running', value: runningInstances, color: statusColors.running },
    { name: 'Stopped', value: instances.filter(i => i.status === 'stopped').length, color: statusColors.stopped },
    { name: 'Error', value: errorInstances, color: statusColors.error },
  ].filter(item => item.value > 0);

  // Android version distribution
  const androidVersions = instances.reduce((acc, instance) => {
    const version = instance.androidVersion;
    acc[version] = (acc[version] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const androidVersionData = Object.entries(androidVersions).map(([version, count]) => ({
    name: `Android ${version}`,
    value: count,
  }));

  // Resource usage data
  const resourceData = [
    { name: 'CPU', usage: systemMetrics?.cpuUsage || 0, color: theme.palette.primary.main },
    { name: 'Memory', usage: systemMetrics?.memoryUsage || 0, color: theme.palette.secondary.main },
    { name: 'Disk', usage: systemMetrics?.diskUsage || 0, color: theme.palette.warning.main },
    { name: 'Network', usage: Math.min(systemMetrics?.networkTraffic || 0, 100), color: theme.palette.info.main },
  ];

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome back, {user?.username}!
          </Typography>
          <Typography variant="subtitle1" color="textSecondary">
            Monitor and manage your Android container instances
          </Typography>
        </Box>
        
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </Box>

      {/* System Status Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Total Instances
                  </Typography>
                  <Typography variant="h4" component="div">
                    {instances.length}
                  </Typography>
                </Box>
                <AndroidOutlined sx={{ fontSize: 40, color: theme.palette.primary.main }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Running
                  </Typography>
                  <Typography variant="h4" component="div" color="success.main">
                    {runningInstances}
                  </Typography>
                </Box>
                <CheckCircleIcon sx={{ fontSize: 40, color: theme.palette.success.main }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Healthy
                  </Typography>
                  <Typography variant="h4" component="div" color="success.main">
                    {healthyInstances}
                  </Typography>
                </Box>
                <SpeedIcon sx={{ fontSize: 40, color: theme.palette.info.main }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Errors
                  </Typography>
                  <Typography variant="h4" component="div" color="error.main">
                    {errorInstances}
                  </Typography>
                </Box>
                <ErrorIcon sx={{ fontSize: 40, color: theme.palette.error.main }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Resource Usage */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Resource Usage
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={resourceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <RechartsTooltip formatter={(value) => [`${value}%`, 'Usage']} />
                    <Bar 
                      dataKey="usage" 
                      fill={theme.palette.primary.main}
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Status Distribution */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Instance Status Distribution
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      dataKey="value"
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      {statusDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Instance Overview */}
      <Grid container spacing={3}>
        {/* Recent Instances */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Instances
              </Typography>
              
              {instances.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <AndroidOutlined sx={{ fontSize: 64, color: theme.palette.grey[400], mb: 2 }} />
                  <Typography variant="h6" color="textSecondary" gutterBottom>
                    No instances found
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Create your first Android instance to get started
                  </Typography>
                  <Button 
                    variant="contained" 
                    sx={{ mt: 2 }}
                    onClick={() => window.location.href = '/instances'}
                  >
                    Create Instance
                  </Button>
                </Box>
              ) : (
                <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
                  {instances.slice(0, 5).map((instance) => (
                    <Paper 
                      key={instance.id} 
                      sx={{ 
                        p: 2, 
                        mb: 1, 
                        display: 'flex', 
                        alignItems: 'center',
                        '&:last-child': { mb: 0 }
                      }}
                      variant="outlined"
                    >
                      <AndroidOutlined sx={{ mr: 2, color: statusColors[instance.status] }} />
                      
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography variant="subtitle1">
                          {instance.name}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Android {instance.androidVersion} • {instance.architecture}
                        </Typography>
                      </Box>

                      <Chip
                        label={instance.status}
                        size="small"
                        sx={{ 
                          backgroundColor: statusColors[instance.status],
                          color: 'white',
                          mr: 1
                        }}
                      />

                      <Tooltip title={instance.status === 'running' ? 'Stop' : 'Start'}>
                        <IconButton 
                          size="small"
                          onClick={() => {
                            if (instance.status === 'running') {
                              apiService.stopInstance(instance.id);
                            } else {
                              apiService.startInstance(instance.id);
                            }
                          }}
                        >
                          {instance.status === 'running' ? <StopIcon /> : <PlayIcon />}
                        </IconButton>
                      </Tooltip>
                    </Paper>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Stats */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Android Versions
              </Typography>
              
              {androidVersionData.length === 0 ? (
                <Typography variant="body2" color="textSecondary">
                  No instances to display
                </Typography>
              ) : (
                androidVersionData.map((item, index) => (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">{item.name}</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {item.value}
                      </Typography>
                    </Box>
                    <LinearProgress 
                      variant="determinate" 
                      value={(item.value / instances.length) * 100} 
                      sx={{ height: 6, borderRadius: 3 }}
                    />
                  </Box>
                ))
              )}
            </CardContent>
          </Card>

          {/* System Health Alert */}
          {errorInstances > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                System Alert
              </Typography>
              <Typography variant="body2">
                {errorInstances} instance{errorInstances > 1 ? 's' : ''} {errorInstances > 1 ? 'require' : 'requires'} attention
              </Typography>
            </Alert>
          )}

          {/* Quick Actions */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              
              <Button
                fullWidth
                variant="outlined"
                startIcon={<AndroidOutlined />}
                sx={{ mb: 1 }}
                onClick={() => window.location.href = '/instances'}
              >
                Manage Instances
              </Button>
              
              <Button
                fullWidth
                variant="outlined"
                startIcon={<TrendingUpIcon />}
                sx={{ mb: 1 }}
                onClick={() => window.location.href = '/logs'}
              >
                View Logs
              </Button>
              
              <Button
                fullWidth
                variant="outlined"
                startIcon={<NetworkIcon />}
                onClick={() => window.location.href = '/network'}
              >
                Network Config
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;