# Admin Dashboard - Vietnamese Marketplace Auto-Categorization System

**Status:** ✅ **Phase 3 Complete (100%)** - All 7 management pages implemented

A modern, full-featured admin dashboard built with React 18 + Vite 5 for managing the Vietnamese marketplace auto-categorization system.

## 🎯 Features

### Implemented Pages (9 total)
✅ **Login** - JWT authentication with beautiful gradient design  
✅ **Dashboard** - Overview with system stats and health monitoring  
✅ **Users Management** - Full CRUD with role management (admin/developer/viewer)  
✅ **API Keys Management** - Create/delete keys, rate limits, show key once  
✅ **Categories Management** - Import/export JSON, sync, rebuild Qdrant index  
✅ **Training Data Management** - View/validate samples, bulk operations, filters  
✅ **Request Logs Viewer** - Search/filter logs, view details, export CSV  
✅ **System Control Panel** - Service management, metrics, cache control  
✅ **Configuration Management** - System config CRUD, secret toggle, bulk update  

### Key Capabilities
- 🔒 JWT authentication with protected routes
- 📊 Real-time health monitoring (auto-refresh every 30s)
- 🎨 Responsive design (mobile, tablet, desktop)
- 🌙 Dark mode support (ready, toggle not yet in UI)
- 🔔 Toast notifications for all actions
- 📥 Export data (JSON, CSV)
- 🔍 Advanced search and filtering
- 📦 Bulk operations (validate, update)
- 🎯 Statistics cards on every page
- 🔐 Secret value masking with show/hide toggle

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Navigate to dashboard directory
cd admin-dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Open http://localhost:3001 in your browser
```

### Default Credentials
- **Username:** admin
- **Password:** admin123

## 📦 Technology Stack

- **React 18.3.1** - UI framework with hooks
- **Vite 5.2.11** - Fast build tool with HMR
- **React Router 6.23.0** - Client-side routing
- **Axios 1.7.2** - HTTP client with interceptors
- **Zustand 4.5.2** - Lightweight state management
- **TailwindCSS 3.4.3** - Utility-first CSS framework
- **Lucide React 0.378.0** - Modern icon library
- **React Hot Toast 2.4.1** - Elegant notifications
- **Recharts 2.12.7** - Charting library (ready for analytics)
- **date-fns 3.6.0** - Date utilities

## 🏗️ Project Structure

```
admin-dashboard/
├── public/               # Static assets
├── src/
│   ├── components/       # Reusable components
│   │   └── Layout.jsx    # Main layout with sidebar + navbar
│   ├── pages/            # Page components
│   │   ├── Login.jsx     # Login page
│   │   ├── Dashboard.jsx # Overview dashboard
│   │   ├── Users.jsx     # Users management
│   │   ├── ApiKeys.jsx   # API keys management
│   │   ├── Categories.jsx # Categories management
│   │   ├── TrainingData.jsx # Training data management
│   │   ├── RequestLogs.jsx # Request logs viewer
│   │   ├── SystemControl.jsx # System control panel
│   │   └── Configuration.jsx # Configuration management
│   ├── services/         # API integration
│   │   └── api.js        # Axios client with all 49 endpoints
│   ├── store/            # State management
│   │   └── authStore.js  # Zustand auth store
│   ├── App.jsx           # Main app with routing
│   ├── main.jsx          # React entry point
│   └── index.css         # Global styles + custom Tailwind classes
├── index.html            # HTML entry point
├── package.json          # Dependencies
├── vite.config.js        # Vite configuration
├── tailwind.config.js    # Tailwind configuration
└── README.md             # This file
```

## 🔧 Custom Tailwind Classes

The dashboard uses custom Tailwind component classes defined in `src/index.css`:

### Buttons
- `.btn` - Base button style
- `.btn-sm` - Small button variant
- `.btn-primary` - Primary blue button
- `.btn-secondary` - Secondary gray button
- `.btn-danger` - Red danger button

### Cards & Inputs
- `.card` - White card with shadow
- `.input` - Form input styling

### Badges
- `.badge` - Base badge style
- `.badge-success` - Green badge
- `.badge-warning` - Yellow badge
- `.badge-danger` - Red badge
- `.badge-info` - Blue badge
- `.badge-secondary` - Gray badge

## 📡 API Integration

All 49 backend API endpoints are integrated via `src/services/api.js`:

### Domains
- **authAPI** - Login, logout, me, changePassword
- **usersAPI** - CRUD operations for users
- **apiKeysAPI** - Create, list, delete API keys
- **logsAPI** - Request logs with stats and cleanup
- **trainingAPI** - Training data management with bulk validate
- **configAPI** - System configuration with bulk update
- **categoriesAPI** - Category sync, import/export, rebuild index
- **systemAPI** - Health monitoring, service control, metrics

### Axios Configuration
- Base URL: `/api` (proxied to `http://localhost:8000` by Vite)
- Timeout: 30,000ms
- Request interceptor: Adds Bearer token from localStorage
- Response interceptor: Auto-redirect to /login on 401 errors

## 🎨 UI/UX Patterns

### Modal Pattern
All create/edit/delete operations use modal overlays to maintain page context.

### Confirmation Modals
Destructive operations (delete user, delete API key, rebuild index, cleanup logs) require explicit confirmation.

### Statistics Cards
Every page displays relevant metrics at the top for quick insights.

### Search & Filter
Consistent search input with icon + dropdown filters across all list pages.

### Toast Notifications
All mutations provide immediate feedback with loading/success/error toasts.

### Pagination
Implemented on pages with large datasets:
- Training Data: 20 items per page
- Request Logs: 50 items per page

### Loading States
All async operations show loading indicators (spinning RefreshCw icon or disabled button state).

### Empty States
Tables show helpful empty state UI with icons when no data is available.

## 🔒 Security Features

- JWT tokens stored in localStorage with automatic injection via Axios interceptors
- Protected routes redirect to login if unauthenticated
- API keys shown only once on creation (cannot be retrieved later)
- Confirmation modals for dangerous operations
- Password fields masked with type="password"
- Secret config values with show/hide toggle (eye icon)

## 🔄 Auto-Refresh

Certain pages automatically refresh data:
- **Dashboard:** Every 30 seconds (system health + stats)
- **System Control:** Every 30 seconds (toggle on/off)

## 📊 Performance Optimizations

- Parallel API calls with `Promise.all` for initial data fetching
- Pagination for large datasets
- Client-side filtering (no backend calls on search)
- Lazy loading modals (only rendered when shown)
- Debounced search inputs

## 🧪 Testing Checklist

Before deployment, test:

1. **Authentication**
   - [ ] Login with admin/admin123
   - [ ] Logout and re-login
   - [ ] Protected routes redirect when logged out
   - [ ] Token expiry handling (401 auto-redirect)

2. **All Pages**
   - [ ] Dashboard: Stats load, health monitoring works
   - [ ] Users: Create/edit/delete user, search/filter
   - [ ] API Keys: Create key (verify shown once), delete, show/hide
   - [ ] Categories: Export, sync, rebuild confirmation
   - [ ] Training Data: View sample, validate, create, bulk validate, export
   - [ ] Request Logs: Filters work, details modal, CSV export
   - [ ] System Control: Service status, metrics, cache clear
   - [ ] Configuration: CRUD operations, secret toggle, bulk update

3. **Responsive Design**
   - [ ] Mobile viewport (< 640px)
   - [ ] Tablet viewport (640-1024px)
   - [ ] Desktop viewport (> 1024px)

4. **Browser Console**
   - [ ] No errors in console
   - [ ] No 404s or failed API calls

## 🛠️ Build Commands

```bash
# Development
npm run dev          # Start dev server with HMR

# Production
npm run build        # Build for production (output: dist/)
npm run preview      # Preview production build locally

# Linting
npm run lint         # Run ESLint (if configured)
```

## 📝 Environment Configuration

Vite uses environment variables:

```bash
# .env.local (create this file)
VITE_API_BASE_URL=http://localhost:8000
```

If not set, defaults to `/api` (proxied to `http://localhost:8000` by vite.config.js).

## 🔗 Backend Integration

The dashboard connects to the backend API on port 8000. Ensure the backend is running:

```bash
# Start backend (from autocategory directory)
docker-compose up -d

# Check backend health
curl http://localhost:8000/api/system/health
```

## 📚 Documentation

- **`PHASE3_COMPLETE.md`** - Comprehensive completion report with all features
- **`PHASE3_PROGRESS.md`** - Historical development tracking

## 🎉 Completion Status

✅ **Phase 3: Admin Dashboard Frontend** - 100% Complete (7/7 pages)

All deliverables met:
- 9 pages implemented (Login + 8 admin pages)
- All 49 backend APIs integrated
- Responsive design (mobile, tablet, desktop)
- Dark mode support (ready)
- Production-ready code (error handling, loading states, validations)
- Consistent UX patterns (modals, toasts, badges, buttons)
- Security best practices (JWT, protected routes, secret masking)
- Performance optimized (parallel API calls, pagination, auto-refresh)

**Status:** ✅ Ready for User Acceptance Testing (UAT)

## 🚀 Next Steps

See **`PHASE3_COMPLETE.md`** for:
- Detailed feature breakdown
- Code statistics
- Screenshots descriptions
- Next phases (4-8) overview

---

**Generated:** 2025-01-05  
**Developer:** GitHub Copilot
- **React Hot Toast** - Notifications
- **Recharts** - Charts (for future analytics)

## 📊 API Integration

Dashboard tích hợp với tất cả 49 API endpoints từ backend:

```javascript
// Example: Fetch system health
import { systemAPI } from '@/services/api'

const health = await systemAPI.health()
console.log(health.data)
```

All API calls automatically include JWT token trong Authorization header.

## 🎨 Styling

### TailwindCSS Custom Classes

```css
/* Buttons */
.btn               /* Base button */
.btn-primary       /* Primary blue button */
.btn-secondary     /* Gray button */
.btn-danger        /* Red button */

/* Cards */
.card              /* White card with shadow */

/* Inputs */
.input             /* Form input */

/* Badges */
.badge             /* Base badge */
.badge-success     /* Green badge */
.badge-warning     /* Yellow badge */
.badge-danger      /* Red badge */
.badge-info        /* Blue badge */
```

### Dark Mode Support

TailwindCSS dark mode được enable:
```jsx
<div className="bg-white dark:bg-gray-800">
```

## 🔄 State Management

### Auth State (Zustand)

```javascript
import { useAuthStore } from '@/store/authStore'

function Component() {
  const { user, isAuthenticated, login, logout } = useAuthStore()
  
  // ...
}
```

State được persist trong localStorage.

## 🚀 Deployment

### Option 1: Docker

```dockerfile
# Dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Option 2: Static Hosting

Build and deploy dist folder to:
- Vercel
- Netlify
- GitHub Pages
- Cloudflare Pages

### Option 3: Nginx

```nginx
server {
    listen 80;
    server_name admin.autocategory.com;
    
    root /var/www/admin-dashboard;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

## 📝 Next Steps

1. **Complete remaining pages:**
   - Users management (CRUD)
   - API keys management
   - Category tree viewer
   - Training data annotation
   - Log viewer with filters

2. **Add real-time updates:**
   - WebSocket connection
   - Live system metrics
   - Real-time notifications

3. **Improve UX:**
   - Loading skeletons
   - Error boundaries
   - Pagination
   - Search & filters
   - Bulk operations

4. **Add charts & analytics:**
   - Request trends (Recharts)
   - Category distribution
   - Model performance
   - Error rate over time

## 🐛 Troubleshooting

### CORS Issues
Make sure backend has CORS enabled for `http://localhost:3001`:

```python
# api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Proxy
Vite dev server proxies `/api` to `http://localhost:8000`:

```javascript
// vite.config.js
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

### Token Expired
If you see "401 Unauthorized", token might be expired. Logout and login again.

## 📚 Resources

- [React Docs](https://react.dev)
- [Vite Docs](https://vitejs.dev)
- [TailwindCSS Docs](https://tailwindcss.com)
- [React Router Docs](https://reactrouter.com)
- [Zustand Docs](https://github.com/pmndrs/zustand)

---

**Status:** Phase 3 - In Progress  
**Completion:** 30% (Login + Dashboard + Layout)  
**Next:** Implement remaining pages
