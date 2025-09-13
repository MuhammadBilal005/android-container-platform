import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Checkbox,
  FormControlLabel,
  Alert,
  Tooltip,
  LinearProgress,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Menu,
  Switch,
  Fab,
  Badge,
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Restart as RestartIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  MoreVert as MoreVertIcon,
  Smartphone as SmartphoneIcon,
  FilterList as FilterIcon,
  ViewModule as ViewModuleIcon,
  ViewList as ViewListIcon,
  CheckBox as CheckBoxIcon,
  AndroidOutlined,
  LocationOn as LocationIcon,
  NetworkCheck as NetworkIcon,
  Storage as StorageIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { useApp } from '@/contexts/AppContext';
import { AndroidInstance, CreateInstanceForm, DeviceProfile } from '@/types';
import apiService from '@/services/api';

const Instances: React.FC = () => {
  const {
    instances,
    dashboardState,
    setSelectedInstances,
    setViewMode,
    setFilters,
    addInstance,
    updateInstance,
    removeInstance,
    setLoading,
    setError,
    clearError,
  } = useApp();

  const [deviceProfiles, setDeviceProfiles] = useState<DeviceProfile[]>([]);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<AndroidInstance | null>(null);
  const [bulkActionsAnchor, setBulkActionsAnchor] = useState<null | HTMLElement>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Form state
  const [createForm, setCreateForm] = useState<CreateInstanceForm>({
    name: '',
    androidVersion: '14',
    architecture: 'arm64',
    deviceProfileId: '',
    location: {
      latitude: 40.7128,
      longitude: -74.0060,
      altitude: 10,
    },
    network: {
      proxyEnabled: false,
      dnsServers: ['8.8.8.8', '8.8.4.4'],
      vpnEnabled: false,
    },
    resources: {
      cpuLimit: 2,
      memoryLimit: 4,
      diskLimit: 10,
    },
  });

  // Load device profiles on mount
  useEffect(() => {
    const loadDeviceProfiles = async () => {
      try {
        const profiles = await apiService.getDeviceProfiles();
        setDeviceProfiles(profiles);
        if (profiles.length > 0 && !createForm.deviceProfileId) {
          setCreateForm(prev => ({ ...prev, deviceProfileId: profiles[0].id }));
        }
      } catch (error) {
        console.error('Failed to load device profiles:', error);
      }
    };

    loadDeviceProfiles();
  }, []);

  // Status colors
  const statusColors = {
    running: 'success' as const,
    stopped: 'default' as const,
    starting: 'warning' as const,
    stopping: 'warning' as const,
    error: 'error' as const,
  };

  // Filter instances based on current filters
  const filteredInstances = instances.filter(instance => {
    const { status, androidVersion, deviceProfile } = dashboardState.filters;
    
    if (status && status.length > 0 && !status.includes(instance.status)) {
      return false;
    }
    
    if (androidVersion && androidVersion.length > 0 && !androidVersion.includes(instance.androidVersion)) {
      return false;
    }
    
    if (deviceProfile && deviceProfile.length > 0 && !deviceProfile.includes(instance.deviceProfile.name)) {
      return false;
    }
    
    return true;
  });

  // Handle instance actions
  const handleStartInstance = async (instanceId: string) => {
    try {
      setLoading(true);
      const updatedInstance = await apiService.startInstance(instanceId);
      updateInstance(updatedInstance);
    } catch (error: any) {
      setError({
        code: 'START_INSTANCE_ERROR',
        message: `Failed to start instance: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStopInstance = async (instanceId: string) => {
    try {
      setLoading(true);
      const updatedInstance = await apiService.stopInstance(instanceId);
      updateInstance(updatedInstance);
    } catch (error: any) {
      setError({
        code: 'STOP_INSTANCE_ERROR',
        message: `Failed to stop instance: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRestartInstance = async (instanceId: string) => {
    try {
      setLoading(true);
      const updatedInstance = await apiService.restartInstance(instanceId);
      updateInstance(updatedInstance);
    } catch (error: any) {
      setError({
        code: 'RESTART_INSTANCE_ERROR',
        message: `Failed to restart instance: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteInstance = async (instanceId: string) => {
    if (!window.confirm('Are you sure you want to delete this instance? This action cannot be undone.')) {
      return;
    }

    try {
      setLoading(true);
      await apiService.deleteInstance(instanceId);
      removeInstance(instanceId);
    } catch (error: any) {
      setError({
        code: 'DELETE_INSTANCE_ERROR',
        message: `Failed to delete instance: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle create instance
  const handleCreateInstance = async () => {
    try {
      setLoading(true);
      clearError();

      const newInstance = await apiService.createInstance(createForm);
      addInstance(newInstance);
      setCreateDialogOpen(false);
      
      // Reset form
      setCreateForm({
        name: '',
        androidVersion: '14',
        architecture: 'arm64',
        deviceProfileId: deviceProfiles[0]?.id || '',
        location: {
          latitude: 40.7128,
          longitude: -74.0060,
          altitude: 10,
        },
        network: {
          proxyEnabled: false,
          dnsServers: ['8.8.8.8', '8.8.4.4'],
          vpnEnabled: false,
        },
        resources: {
          cpuLimit: 2,
          memoryLimit: 4,
          diskLimit: 10,
        },
      });
    } catch (error: any) {
      setError({
        code: 'CREATE_INSTANCE_ERROR',
        message: `Failed to create instance: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle bulk selection
  const handleToggleSelectAll = () => {
    if (dashboardState.selectedInstances.length === filteredInstances.length) {
      setSelectedInstances([]);
    } else {
      setSelectedInstances(filteredInstances.map(i => i.id));
    }
  };

  const handleToggleSelect = (instanceId: string) => {
    const isSelected = dashboardState.selectedInstances.includes(instanceId);
    if (isSelected) {
      setSelectedInstances(dashboardState.selectedInstances.filter(id => id !== instanceId));
    } else {
      setSelectedInstances([...dashboardState.selectedInstances, instanceId]);
    }
  };

  // Bulk actions
  const handleBulkStart = async () => {
    try {
      setLoading(true);
      await apiService.createBulkOperation('start', dashboardState.selectedInstances);
      setBulkActionsAnchor(null);
      setSelectedInstances([]);
    } catch (error: any) {
      setError({
        code: 'BULK_START_ERROR',
        message: `Failed to start instances: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBulkStop = async () => {
    try {
      setLoading(true);
      await apiService.createBulkOperation('stop', dashboardState.selectedInstances);
      setBulkActionsAnchor(null);
      setSelectedInstances([]);
    } catch (error: any) {
      setError({
        code: 'BULK_STOP_ERROR',
        message: `Failed to stop instances: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const renderInstanceCard = (instance: AndroidInstance) => (
    <Grid item xs={12} sm={6} md={4} lg={3} key={instance.id}>
      <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flexGrow: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={dashboardState.selectedInstances.includes(instance.id)}
                  onChange={() => handleToggleSelect(instance.id)}
                />
              }
              label=""
              sx={{ mr: 1 }}
            />
            
            <AndroidOutlined sx={{ mr: 1, fontSize: 24 }} />
            
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              {instance.name}
            </Typography>
            
            <Chip
              label={instance.status}
              color={statusColors[instance.status]}
              size="small"
            />
          </Box>

          <Typography variant="body2" color="textSecondary" gutterBottom>
            {instance.deviceProfile.name}
          </Typography>
          
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Android {instance.androidVersion} • {instance.architecture}
          </Typography>

          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <MemoryIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
              <Typography variant="caption">
                Memory: {Math.round((instance.resources.memory.used / instance.resources.memory.total) * 100)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(instance.resources.memory.used / instance.resources.memory.total) * 100}
                sx={{ flexGrow: 1, ml: 1, height: 4 }}
              />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <SpeedIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
              <Typography variant="caption">
                CPU: {Math.round(instance.resources.cpu.usage)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={instance.resources.cpu.usage}
                sx={{ flexGrow: 1, ml: 1, height: 4 }}
              />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 2 }}>
              <Tooltip title="Location">
                <IconButton size="small">
                  <LocationIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Network">
                <IconButton size="small">
                  <NetworkIcon fontSize="small" />
                </IconButton>
              </Tooltip>

              <Typography variant="caption" color="textSecondary">
                Port: {instance.adbPort}
              </Typography>
            </Box>
          </Box>
        </CardContent>

        <Box sx={{ p: 2, pt: 0 }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {instance.status === 'running' ? (
              <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={<StopIcon />}
                onClick={() => handleStopInstance(instance.id)}
                sx={{ flexGrow: 1 }}
              >
                Stop
              </Button>
            ) : (
              <Button
                size="small"
                variant="outlined"
                color="success"
                startIcon={<PlayIcon />}
                onClick={() => handleStartInstance(instance.id)}
                sx={{ flexGrow: 1 }}
              >
                Start
              </Button>
            )}

            <IconButton
              size="small"
              onClick={() => handleRestartInstance(instance.id)}
              disabled={instance.status === 'stopped'}
            >
              <RestartIcon />
            </IconButton>

            <IconButton
              size="small"
              onClick={() => {
                setSelectedInstance(instance);
                setEditDialogOpen(true);
              }}
            >
              <EditIcon />
            </IconButton>

            <IconButton
              size="small"
              color="error"
              onClick={() => handleDeleteInstance(instance.id)}
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>
      </Card>
    </Grid>
  );

  const renderInstanceList = (instance: AndroidInstance) => (
    <Paper key={instance.id} sx={{ mb: 1 }}>
      <ListItem>
        <Checkbox
          checked={dashboardState.selectedInstances.includes(instance.id)}
          onChange={() => handleToggleSelect(instance.id)}
        />
        
        <AndroidOutlined sx={{ mx: 2 }} />
        
        <ListItemText
          primary={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="subtitle1">{instance.name}</Typography>
              <Chip label={instance.status} color={statusColors[instance.status]} size="small" />
            </Box>
          }
          secondary={
            <Typography variant="body2" color="textSecondary">
              {instance.deviceProfile.name} • Android {instance.androidVersion} • {instance.architecture} • Port: {instance.adbPort}
            </Typography>
          }
        />

        <ListItemSecondaryAction>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {instance.status === 'running' ? (
              <IconButton onClick={() => handleStopInstance(instance.id)} color="warning">
                <StopIcon />
              </IconButton>
            ) : (
              <IconButton onClick={() => handleStartInstance(instance.id)} color="success">
                <PlayIcon />
              </IconButton>
            )}
            
            <IconButton onClick={() => handleRestartInstance(instance.id)}>
              <RestartIcon />
            </IconButton>
            
            <IconButton onClick={() => handleDeleteInstance(instance.id)} color="error">
              <DeleteIcon />
            </IconButton>
          </Box>
        </ListItemSecondaryAction>
      </ListItem>
    </Paper>
  );

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Instance Management
          </Typography>
          <Typography variant="subtitle1" color="textSecondary">
            Create, configure, and manage your Android container instances
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {/* Bulk actions */}
          {dashboardState.selectedInstances.length > 0 && (
            <Button
              variant="outlined"
              onClick={(e) => setBulkActionsAnchor(e.currentTarget)}
            >
              Actions ({dashboardState.selectedInstances.length})
            </Button>
          )}

          {/* View mode toggle */}
          <Box sx={{ display: 'flex', border: 1, borderColor: 'divider', borderRadius: 1 }}>
            <IconButton
              onClick={() => setViewMode('grid')}
              color={dashboardState.viewMode === 'grid' ? 'primary' : 'default'}
            >
              <ViewModuleIcon />
            </IconButton>
            <IconButton
              onClick={() => setViewMode('list')}
              color={dashboardState.viewMode === 'list' ? 'primary' : 'default'}
            >
              <ViewListIcon />
            </IconButton>
          </Box>

          <IconButton onClick={() => setFiltersOpen(!filtersOpen)}>
            <FilterIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Filters */}
      {filtersOpen && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>Filters</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  multiple
                  value={dashboardState.filters.status || []}
                  label="Status"
                  onChange={(e) => setFilters({ ...dashboardState.filters, status: e.target.value as string[] })}
                >
                  <MenuItem value="running">Running</MenuItem>
                  <MenuItem value="stopped">Stopped</MenuItem>
                  <MenuItem value="starting">Starting</MenuItem>
                  <MenuItem value="stopping">Stopping</MenuItem>
                  <MenuItem value="error">Error</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Android Version</InputLabel>
                <Select
                  multiple
                  value={dashboardState.filters.androidVersion || []}
                  label="Android Version"
                  onChange={(e) => setFilters({ ...dashboardState.filters, androidVersion: e.target.value as string[] })}
                >
                  <MenuItem value="11">Android 11</MenuItem>
                  <MenuItem value="12">Android 12</MenuItem>
                  <MenuItem value="13">Android 13</MenuItem>
                  <MenuItem value="14">Android 14</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={4}>
              <Button
                fullWidth
                variant="outlined"
                onClick={() => setFilters({})}
              >
                Clear Filters
              </Button>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Select All */}
      {filteredInstances.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <FormControlLabel
            control={
              <Checkbox
                checked={dashboardState.selectedInstances.length === filteredInstances.length}
                indeterminate={dashboardState.selectedInstances.length > 0 && dashboardState.selectedInstances.length < filteredInstances.length}
                onChange={handleToggleSelectAll}
              />
            }
            label={`Select All (${filteredInstances.length})`}
          />
        </Box>
      )}

      {/* Instances Grid/List */}
      {filteredInstances.length === 0 ? (
        <Paper sx={{ p: 8, textAlign: 'center' }}>
          <SmartphoneIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No instances found
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
            Create your first Android instance to get started
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Instance
          </Button>
        </Paper>
      ) : (
        <>
          {dashboardState.viewMode === 'grid' ? (
            <Grid container spacing={3}>
              {filteredInstances.map(renderInstanceCard)}
            </Grid>
          ) : (
            <List>
              {filteredInstances.map(renderInstanceList)}
            </List>
          )}
        </>
      )}

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="add instance"
        onClick={() => setCreateDialogOpen(true)}
        sx={{ position: 'fixed', bottom: 24, right: 24 }}
      >
        <AddIcon />
      </Fab>

      {/* Create Instance Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Create New Instance</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Instance Name"
                value={createForm.name}
                onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                required
              />
            </Grid>

            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Android Version</InputLabel>
                <Select
                  value={createForm.androidVersion}
                  label="Android Version"
                  onChange={(e) => setCreateForm(prev => ({ ...prev, androidVersion: e.target.value }))}
                >
                  <MenuItem value="11">Android 11</MenuItem>
                  <MenuItem value="12">Android 12</MenuItem>
                  <MenuItem value="13">Android 13</MenuItem>
                  <MenuItem value="14">Android 14</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Architecture</InputLabel>
                <Select
                  value={createForm.architecture}
                  label="Architecture"
                  onChange={(e) => setCreateForm(prev => ({ ...prev, architecture: e.target.value as 'arm64' | 'x86_64' }))}
                >
                  <MenuItem value="arm64">ARM64</MenuItem>
                  <MenuItem value="x86_64">x86_64</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Device Profile</InputLabel>
                <Select
                  value={createForm.deviceProfileId}
                  label="Device Profile"
                  onChange={(e) => setCreateForm(prev => ({ ...prev, deviceProfileId: e.target.value }))}
                >
                  {deviceProfiles.map(profile => (
                    <MenuItem key={profile.id} value={profile.id}>
                      {profile.name} - {profile.manufacturer} {profile.model}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Latitude"
                type="number"
                value={createForm.location.latitude}
                onChange={(e) => setCreateForm(prev => ({
                  ...prev,
                  location: { ...prev.location, latitude: parseFloat(e.target.value) }
                }))}
              />
            </Grid>

            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Longitude"
                type="number"
                value={createForm.location.longitude}
                onChange={(e) => setCreateForm(prev => ({
                  ...prev,
                  location: { ...prev.location, longitude: parseFloat(e.target.value) }
                }))}
              />
            </Grid>

            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Altitude"
                type="number"
                value={createForm.location.altitude}
                onChange={(e) => setCreateForm(prev => ({
                  ...prev,
                  location: { ...prev.location, altitude: parseFloat(e.target.value) }
                }))}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreateInstance} variant="contained">
            Create Instance
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Actions Menu */}
      <Menu
        anchorEl={bulkActionsAnchor}
        open={Boolean(bulkActionsAnchor)}
        onClose={() => setBulkActionsAnchor(null)}
      >
        <MenuItem onClick={handleBulkStart}>
          <PlayIcon sx={{ mr: 1 }} /> Start Selected
        </MenuItem>
        <MenuItem onClick={handleBulkStop}>
          <StopIcon sx={{ mr: 1 }} /> Stop Selected
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default Instances;