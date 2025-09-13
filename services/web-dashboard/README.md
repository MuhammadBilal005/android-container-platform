# Android Container Platform - Web Dashboard

A modern React-based web dashboard for managing Android container instances with real-time monitoring, device spoofing, and location simulation capabilities.

## 🚀 Features

### Core Functionality
- **🔐 JWT Authentication** - Secure login with token-based authentication
- **📊 Real-time Dashboard** - Live instance statistics and system metrics
- **📱 Instance Management** - Create, configure, and control Android containers
- **🗺️ Location Control** - GPS simulation with interactive map integration
- **🌐 Network Configuration** - Proxy and VPN management
- **📝 Live Logging** - Real-time log streaming and debugging
- **🔧 Device Profiles** - Hardware fingerprint management
- **⚡ Bulk Operations** - Manage multiple instances simultaneously

### Technical Features
- **WebSocket Integration** - Real-time updates and notifications
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Material-UI Components** - Modern, accessible user interface
- **TypeScript** - Type-safe development with full IntelliSense
- **React Query** - Efficient data fetching and caching
- **Chart Integration** - Beautiful visualizations with Recharts
- **Map Integration** - Interactive maps with Leaflet

## 🛠 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Docker (for containerized deployment)
- API Gateway running on localhost:3000

### Development Setup

1. **Clone and install dependencies**:
   ```bash
   cd services/web-dashboard
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start development server**:
   ```bash
   npm start
   ```

4. **Open dashboard**:
   Navigate to `http://localhost:3001`

### Production Deployment

#### Using Docker

1. **Build container**:
   ```bash
   docker build -t android-dashboard .
   ```

2. **Run container**:
   ```bash
   docker run -p 80:80 \
     -e REACT_APP_API_URL=http://your-api-server:3000 \
     -e REACT_APP_WS_URL=http://your-api-server:3000 \
     android-dashboard
   ```

#### Using Docker Compose
```yaml
version: '3.8'
services:
  web-dashboard:
    build: ./services/web-dashboard
    ports:
      - "80:80"
    environment:
      - REACT_APP_API_URL=http://api-gateway:3000
      - REACT_APP_WS_URL=http://api-gateway:3000
    depends_on:
      - api-gateway
```

## 📁 Project Structure

```
services/web-dashboard/
├── public/                    # Static assets
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── Layout.tsx       # Main application layout
│   │   └── Login.tsx        # Authentication component
│   ├── pages/               # Main application pages
│   │   ├── Dashboard.tsx    # Overview dashboard
│   │   ├── Instances.tsx    # Instance management
│   │   └── LocationControl.tsx # GPS simulation
│   ├── contexts/            # React context providers
│   │   ├── AuthContext.tsx  # Authentication state
│   │   └── AppContext.tsx   # Application state
│   ├── services/           # API and WebSocket services
│   │   ├── api.ts          # HTTP API client
│   │   └── websocket.ts    # WebSocket client
│   ├── types/              # TypeScript type definitions
│   ├── hooks/              # Custom React hooks
│   ├── utils/              # Utility functions
│   └── App.tsx             # Main application component
├── Dockerfile              # Container definition
├── nginx.conf              # Production web server config
├── docker-entrypoint.sh    # Container startup script
└── package.json            # Dependencies and scripts
```

## 🎯 Core Pages

### Dashboard
- **System Overview** - Total instances, running status, health metrics
- **Real-time Charts** - CPU, memory, network usage visualization
- **Quick Actions** - Direct access to common operations
- **Status Distribution** - Visual breakdown of instance states
- **Recent Activity** - Latest instance changes and alerts

### Instance Management
- **Grid/List Views** - Flexible instance display options
- **Bulk Operations** - Start/stop/restart multiple instances
- **Advanced Filtering** - Filter by status, Android version, profile
- **Real-time Status** - Live updates via WebSocket
- **Resource Monitoring** - CPU, memory, disk usage per instance

### Location Control
- **Interactive Map** - Click-to-set location with visual feedback
- **Movement Simulation** - Create walking/driving/cycling paths
- **Preset Locations** - Quick access to major cities worldwide
- **Real-time Updates** - Live GPS coordinate changes
- **Path Management** - Save, edit, and replay movement patterns

## 🔧 Configuration

### Environment Variables
```bash
# API Configuration
REACT_APP_API_URL=http://localhost:3000
REACT_APP_WS_URL=http://localhost:3000

# Map Configuration
REACT_APP_MAP_PROVIDER=openstreetmap
REACT_APP_MAP_API_KEY=your_api_key_here

# Application Settings
REACT_APP_APP_NAME=Android Container Platform
REACT_APP_VERSION=1.0.0
REACT_APP_ENVIRONMENT=production

# Feature Flags
REACT_APP_ENABLE_DEBUG=false
REACT_APP_ENABLE_ANALYTICS=true

# Performance Settings
REACT_APP_CACHE_TIMEOUT=300000
REACT_APP_REFRESH_INTERVAL=30000
```

### Nginx Configuration
The production deployment includes:
- **Reverse Proxy** - API requests routed to backend
- **WebSocket Support** - Real-time connections handled properly
- **Static Asset Caching** - Optimized delivery of JS/CSS/images
- **Security Headers** - CORS, CSP, and other security measures
- **Gzip Compression** - Reduced bandwidth usage
- **Rate Limiting** - API abuse protection

## 📊 Real-time Features

### WebSocket Integration
- **Instance Status Updates** - Live status changes
- **Metrics Streaming** - Real-time resource usage
- **Log Streaming** - Live log entries
- **Bulk Operation Progress** - Real-time progress updates
- **System Alerts** - Immediate notifications

### State Management
- **Context API** - Global application state
- **React Query** - Server state caching and synchronization
- **Local Storage** - Persistent user preferences
- **Real-time Sync** - WebSocket state updates

## 🎨 UI Components

### Material-UI Integration
- **Consistent Design** - Material Design principles
- **Dark/Light Theme** - Automatic theme switching
- **Responsive Grid** - Adaptive layouts for all screen sizes
- **Accessibility** - WCAG compliance and screen reader support
- **Custom Theme** - Brand colors and typography

### Charts and Visualizations
- **Line Charts** - Time-series metrics display
- **Pie Charts** - Status and distribution visualization
- **Bar Charts** - Resource usage comparison
- **Progress Bars** - Loading and progress indication
- **Real-time Updates** - Live chart data updates

## 🔒 Security

### Authentication
- **JWT Tokens** - Secure API authentication
- **Token Refresh** - Automatic token renewal
- **Protected Routes** - Route-level access control
- **Session Management** - Automatic logout on expiration

### Security Headers
- **CSP (Content Security Policy)** - XSS protection
- **HSTS** - Force HTTPS connections
- **X-Frame-Options** - Clickjacking prevention
- **Rate Limiting** - API abuse protection

## 📱 Mobile Support

### Responsive Design
- **Adaptive Layout** - Optimized for all screen sizes
- **Touch-friendly** - Mobile gesture support
- **Progressive Web App** - Installable on mobile devices
- **Offline Support** - Basic functionality without internet

## 🚀 Performance

### Optimization Features
- **Code Splitting** - Lazy loading of route components
- **Asset Caching** - Efficient browser caching
- **Bundle Analysis** - Optimized JavaScript bundles
- **Image Optimization** - Compressed and responsive images
- **Service Workers** - Background sync and caching

## 🔧 Development

### Available Scripts
```bash
npm start          # Start development server
npm run build      # Build production bundle
npm test           # Run test suite
npm run lint       # Run ESLint
npm run lint:fix   # Fix ESLint issues
npm run format     # Format code with Prettier
```

### Development Features
- **Hot Reload** - Instant updates during development
- **Source Maps** - Easy debugging in browser dev tools
- **TypeScript Support** - Full type checking and IntelliSense
- **ESLint Integration** - Code quality enforcement
- **Prettier Integration** - Consistent code formatting

## 🐛 Troubleshooting

### Common Issues

1. **API Connection Failed**
   ```bash
   # Check API URL configuration
   echo $REACT_APP_API_URL
   
   # Test API connectivity
   curl http://localhost:3000/api/health
   ```

2. **WebSocket Connection Issues**
   ```bash
   # Check WebSocket URL
   echo $REACT_APP_WS_URL
   
   # Verify WebSocket endpoint
   wscat -c ws://localhost:3000/socket.io/
   ```

3. **Build Failures**
   ```bash
   # Clear cache and reinstall
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

4. **Map Not Loading**
   ```bash
   # Check map provider configuration
   echo $REACT_APP_MAP_PROVIDER
   
   # For providers requiring API keys
   echo $REACT_APP_MAP_API_KEY
   ```

### Debug Mode
Enable debug logging by setting:
```bash
REACT_APP_ENABLE_DEBUG=true
```

## 📄 License

This project is part of the Android Container Platform and is released under the MIT License.

---

**🎯 Dashboard Access**: http://localhost:3001  
**📚 API Documentation**: http://localhost:3000/api/docs  
**🔧 Default Credentials**: admin / password