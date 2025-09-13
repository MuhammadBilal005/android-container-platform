import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  Divider,
  Tooltip,
  Alert,
  LinearProgress,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  LocationOn as LocationIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Navigation as NavigationIcon,
  Timeline as TimelineIcon,
  MyLocation as MyLocationIcon,
  DirectionsWalk as WalkIcon,
  DriveEta as DriveIcon,
  DirectionsBike as BikeIcon,
} from '@mui/icons-material';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents } from 'react-leaflet';
import { LatLngTuple, Icon } from 'leaflet';
import { useApp } from '@/contexts/AppContext';
import { AndroidInstance, GeoLocation } from '@/types';
import apiService from '@/services/api';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in react-leaflet
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

const defaultIcon = new Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// Movement simulation types
interface MovementPath {
  id: string;
  name: string;
  instanceId: string;
  points: Array<{
    latitude: number;
    longitude: number;
    duration: number; // seconds to spend at this point
  }>;
  type: 'walk' | 'drive' | 'bike' | 'custom';
  speed: number; // km/h
  isActive: boolean;
  startedAt?: string;
}

// Predefined locations
const PRESET_LOCATIONS = [
  { name: 'New York, NY', lat: 40.7128, lng: -74.0060 },
  { name: 'Los Angeles, CA', lat: 34.0522, lng: -118.2437 },
  { name: 'London, UK', lat: 51.5074, lng: -0.1278 },
  { name: 'Tokyo, Japan', lat: 35.6762, lng: 139.6503 },
  { name: 'Paris, France', lat: 48.8566, lng: 2.3522 },
  { name: 'Sydney, Australia', lat: -33.8688, lng: 151.2093 },
  { name: 'Dubai, UAE', lat: 25.2048, lng: 55.2708 },
  { name: 'Singapore', lat: 1.3521, lng: 103.8198 },
];

// Map click handler component
const MapClickHandler: React.FC<{ onLocationSelect: (lat: number, lng: number) => void }> = ({
  onLocationSelect,
}) => {
  useMapEvents({
    click: (e) => {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

const LocationControl: React.FC = () => {
  const { instances, setLoading, setError } = useApp();
  
  const [selectedInstance, setSelectedInstance] = useState<AndroidInstance | null>(null);
  const [movementPaths, setMovementPaths] = useState<MovementPath[]>([]);
  const [pathDialogOpen, setPathDialogOpen] = useState(false);
  const [newLocationDialogOpen, setNewLocationDialogOpen] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [mapCenter, setMapCenter] = useState<LatLngTuple>([40.7128, -74.0060]);
  const [zoom, setZoom] = useState(13);
  const [pathCreation, setPathCreation] = useState({
    name: '',
    type: 'walk' as const,
    speed: 5,
    points: [] as Array<{ latitude: number; longitude: number; duration: number }>,
  });

  // Load movement paths for selected instance
  useEffect(() => {
    if (selectedInstance) {
      setMapCenter([selectedInstance.location.latitude, selectedInstance.location.longitude]);
    }
  }, [selectedInstance]);

  // Set initial selected instance
  useEffect(() => {
    if (instances.length > 0 && !selectedInstance) {
      setSelectedInstance(instances[0]);
    }
  }, [instances, selectedInstance]);

  // Handle location update
  const handleUpdateLocation = async (lat: number, lng: number, altitude: number = 10) => {
    if (!selectedInstance) return;

    try {
      setLoading(true);
      await apiService.updateInstanceLocation(selectedInstance.id, {
        latitude: lat,
        longitude: lng,
        altitude,
      });
      
      // Update local instance state would happen via WebSocket
      setNewLocationDialogOpen(false);
      setSelectedLocation(null);
    } catch (error: any) {
      setError({
        code: 'UPDATE_LOCATION_ERROR',
        message: `Failed to update location: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle preset location selection
  const handlePresetLocation = async (preset: typeof PRESET_LOCATIONS[0]) => {
    await handleUpdateLocation(preset.lat, preset.lng);
  };

  // Handle map click for location selection
  const handleMapClick = (lat: number, lng: number) => {
    setSelectedLocation({ lat, lng });
    setNewLocationDialogOpen(true);
  };

  // Create movement path
  const handleCreatePath = async () => {
    if (!selectedInstance || pathCreation.points.length < 2) return;

    try {
      setLoading(true);
      
      const newPath: MovementPath = {
        id: Date.now().toString(),
        name: pathCreation.name,
        instanceId: selectedInstance.id,
        points: pathCreation.points,
        type: pathCreation.type,
        speed: pathCreation.speed,
        isActive: false,
      };

      setMovementPaths(prev => [...prev, newPath]);
      setPathDialogOpen(false);
      
      // Reset form
      setPathCreation({
        name: '',
        type: 'walk',
        speed: 5,
        points: [],
      });
    } catch (error: any) {
      setError({
        code: 'CREATE_PATH_ERROR',
        message: `Failed to create movement path: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  // Start movement simulation
  const handleStartSimulation = async (pathId: string) => {
    const path = movementPaths.find(p => p.id === pathId);
    if (!path || !selectedInstance) return;

    try {
      setLoading(true);
      await apiService.simulateMovement(selectedInstance.id, path.points);
      
      setMovementPaths(prev => 
        prev.map(p => 
          p.id === pathId 
            ? { ...p, isActive: true, startedAt: new Date().toISOString() }
            : p
        )
      );
    } catch (error: any) {
      setError({
        code: 'START_SIMULATION_ERROR',
        message: `Failed to start movement simulation: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  // Stop movement simulation
  const handleStopSimulation = async (pathId: string) => {
    const path = movementPaths.find(p => p.id === pathId);
    if (!path || !selectedInstance) return;

    try {
      setLoading(true);
      await apiService.stopMovementSimulation(selectedInstance.id);
      
      setMovementPaths(prev => 
        prev.map(p => 
          p.id === pathId 
            ? { ...p, isActive: false, startedAt: undefined }
            : p
        )
      );
    } catch (error: any) {
      setError({
        code: 'STOP_SIMULATION_ERROR',
        message: `Failed to stop movement simulation: ${error.message}`,
        details: error,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  // Add point to path creation
  const addPointToPath = (lat: number, lng: number, duration: number = 30) => {
    setPathCreation(prev => ({
      ...prev,
      points: [...prev.points, { latitude: lat, longitude: lng, duration }],
    }));
  };

  // Get movement type icon
  const getMovementIcon = (type: string) => {
    switch (type) {
      case 'walk': return <WalkIcon />;
      case 'drive': return <DriveIcon />;
      case 'bike': return <BikeIcon />;
      default: return <NavigationIcon />;
    }
  };

  // Active movement paths for selected instance
  const instancePaths = movementPaths.filter(path => 
    selectedInstance ? path.instanceId === selectedInstance.id : false
  );

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Location Control
        </Typography>
        <Typography variant="subtitle1" color="textSecondary">
          Manage GPS locations and simulate movement for Android instances
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Instance Selection and Controls */}
        <Grid item xs={12} lg={4}>
          {/* Instance Selector */}
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Select Instance
              </Typography>
              
              <FormControl fullWidth>
                <InputLabel>Instance</InputLabel>
                <Select
                  value={selectedInstance?.id || ''}
                  label="Instance"
                  onChange={(e) => {
                    const instance = instances.find(i => i.id === e.target.value);
                    setSelectedInstance(instance || null);
                  }}
                >
                  {instances.map(instance => (
                    <MenuItem key={instance.id} value={instance.id}>
                      {instance.name} - {instance.status}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {selectedInstance && (
                <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="body2" gutterBottom>
                    <strong>Current Location:</strong>
                  </Typography>
                  <Typography variant="body2">
                    Lat: {selectedInstance.location.latitude.toFixed(6)}
                  </Typography>
                  <Typography variant="body2">
                    Lng: {selectedInstance.location.longitude.toFixed(6)}
                  </Typography>
                  <Typography variant="body2">
                    Alt: {selectedInstance.location.altitude}m
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Preset Locations */}
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Locations
              </Typography>
              
              <List dense>
                {PRESET_LOCATIONS.map((location, index) => (
                  <ListItem key={index}>
                    <ListItemText 
                      primary={location.name}
                      secondary={`${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}`}
                    />
                    <ListItemSecondaryAction>
                      <IconButton 
                        edge="end" 
                        onClick={() => handlePresetLocation(location)}
                        disabled={!selectedInstance}
                      >
                        <LocationIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>

          {/* Movement Paths */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Movement Paths
                </Typography>
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={() => setPathDialogOpen(true)}
                  disabled={!selectedInstance}
                >
                  Create
                </Button>
              </Box>

              {instancePaths.length === 0 ? (
                <Typography variant="body2" color="textSecondary" sx={{ textAlign: 'center', py: 2 }}>
                  No movement paths created
                </Typography>
              ) : (
                <List dense>
                  {instancePaths.map((path) => (
                    <ListItem key={path.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mr: 1 }}>
                        {getMovementIcon(path.type)}
                      </Box>
                      
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle2">{path.name}</Typography>
                            {path.isActive && <Chip label="Active" color="success" size="small" />}
                          </Box>
                        }
                        secondary={`${path.points.length} points • ${path.speed} km/h`}
                      />
                      
                      <ListItemSecondaryAction>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          {path.isActive ? (
                            <IconButton
                              size="small"
                              onClick={() => handleStopSimulation(path.id)}
                              color="warning"
                            >
                              <StopIcon />
                            </IconButton>
                          ) : (
                            <IconButton
                              size="small"
                              onClick={() => handleStartSimulation(path.id)}
                              color="success"
                            >
                              <PlayIcon />
                            </IconButton>
                          )}
                          
                          <IconButton
                            size="small"
                            onClick={() => {
                              setMovementPaths(prev => prev.filter(p => p.id !== path.id));
                            }}
                            color="error"
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Map */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Interactive Map
              </Typography>
              
              <Alert severity="info" sx={{ mb: 2 }}>
                Click on the map to set a new location for the selected instance
              </Alert>

              <Box sx={{ height: 600, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                <MapContainer
                  center={mapCenter}
                  zoom={zoom}
                  style={{ height: '100%', width: '100%' }}
                >
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  />
                  
                  <MapClickHandler onLocationSelect={handleMapClick} />

                  {/* Current instance location */}
                  {selectedInstance && (
                    <Marker
                      position={[selectedInstance.location.latitude, selectedInstance.location.longitude]}
                      icon={defaultIcon}
                    >
                      <Popup>
                        <div>
                          <strong>{selectedInstance.name}</strong><br />
                          Current Location<br />
                          Lat: {selectedInstance.location.latitude.toFixed(6)}<br />
                          Lng: {selectedInstance.location.longitude.toFixed(6)}
                        </div>
                      </Popup>
                    </Marker>
                  )}

                  {/* Movement path visualization */}
                  {instancePaths.map((path) => (
                    <Polyline
                      key={path.id}
                      positions={path.points.map(p => [p.latitude, p.longitude] as LatLngTuple)}
                      color={path.isActive ? "#4caf50" : "#2196f3"}
                      weight={path.isActive ? 4 : 2}
                      opacity={path.isActive ? 0.8 : 0.6}
                    />
                  ))}

                  {/* Selected location marker */}
                  {selectedLocation && (
                    <Marker
                      position={[selectedLocation.lat, selectedLocation.lng]}
                      icon={defaultIcon}
                    >
                      <Popup>
                        <div>
                          New Location<br />
                          Lat: {selectedLocation.lat.toFixed(6)}<br />
                          Lng: {selectedLocation.lng.toFixed(6)}
                        </div>
                      </Popup>
                    </Marker>
                  )}
                </MapContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* New Location Dialog */}
      <Dialog open={newLocationDialogOpen} onClose={() => setNewLocationDialogOpen(false)}>
        <DialogTitle>Set New Location</DialogTitle>
        <DialogContent>
          {selectedLocation && (
            <>
              <Typography gutterBottom>
                Set location for: <strong>{selectedInstance?.name}</strong>
              </Typography>
              
              <TextField
                fullWidth
                label="Latitude"
                value={selectedLocation.lat.toFixed(6)}
                InputProps={{ readOnly: true }}
                sx={{ mb: 2 }}
              />
              
              <TextField
                fullWidth
                label="Longitude"
                value={selectedLocation.lng.toFixed(6)}
                InputProps={{ readOnly: true }}
                sx={{ mb: 2 }}
              />
              
              <TextField
                fullWidth
                label="Altitude (meters)"
                type="number"
                defaultValue={10}
                inputProps={{ id: 'altitude-input' }}
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewLocationDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => {
              if (selectedLocation) {
                const altitudeInput = document.getElementById('altitude-input') as HTMLInputElement;
                const altitude = parseFloat(altitudeInput.value) || 10;
                handleUpdateLocation(selectedLocation.lat, selectedLocation.lng, altitude);
              }
            }}
            variant="contained"
          >
            Set Location
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create Path Dialog */}
      <Dialog 
        open={pathDialogOpen} 
        onClose={() => setPathDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create Movement Path</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Path Name"
            value={pathCreation.name}
            onChange={(e) => setPathCreation(prev => ({ ...prev, name: e.target.value }))}
            sx={{ mb: 2, mt: 1 }}
          />

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Movement Type</InputLabel>
            <Select
              value={pathCreation.type}
              label="Movement Type"
              onChange={(e) => setPathCreation(prev => ({ 
                ...prev, 
                type: e.target.value as any,
                speed: e.target.value === 'walk' ? 5 : e.target.value === 'bike' ? 15 : 50
              }))}
            >
              <MenuItem value="walk">Walking (5 km/h)</MenuItem>
              <MenuItem value="bike">Cycling (15 km/h)</MenuItem>
              <MenuItem value="drive">Driving (50 km/h)</MenuItem>
              <MenuItem value="custom">Custom Speed</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="Speed (km/h)"
            type="number"
            value={pathCreation.speed}
            onChange={(e) => setPathCreation(prev => ({ ...prev, speed: parseFloat(e.target.value) }))}
            sx={{ mb: 2 }}
          />

          <Typography variant="body2" color="textSecondary" gutterBottom>
            Click on the map to add waypoints to your path. You need at least 2 points.
          </Typography>
          
          <Typography variant="body2">
            Current points: {pathCreation.points.length}
          </Typography>

          {pathCreation.points.length > 0 && (
            <List dense sx={{ maxHeight: 200, overflow: 'auto', mt: 1 }}>
              {pathCreation.points.map((point, index) => (
                <ListItem key={index}>
                  <ListItemText
                    primary={`Point ${index + 1}`}
                    secondary={`${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)}`}
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      size="small"
                      onClick={() => {
                        setPathCreation(prev => ({
                          ...prev,
                          points: prev.points.filter((_, i) => i !== index)
                        }));
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPathDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreatePath}
            variant="contained"
            disabled={pathCreation.points.length < 2 || !pathCreation.name}
          >
            Create Path
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LocationControl;