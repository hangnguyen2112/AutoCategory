import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import ApiKeys from './pages/ApiKeys'
import Categories from './pages/Categories'
import TrainingData from './pages/TrainingData'
import RequestLogs from './pages/RequestLogs'
import SystemControl from './pages/SystemControl'
import Configuration from './pages/Configuration'
import Settings from './pages/Settings'
import PostTester from './pages/PostTester'

// Layout
import Layout from './components/Layout'

// Protected Route Component
function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  
  // Also check localStorage for token (handles zustand hydration delay)
  const hasToken = localStorage.getItem('auth_token')
  
  if (!isAuthenticated && !hasToken) {
    return <Navigate to="/login" replace />
  }
  
  return <Layout>{children}</Layout>
}

function App() {
  return (
    <Router basename="/admin">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <Users />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/api-keys"
          element={
            <ProtectedRoute>
              <ApiKeys />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/categories"
          element={
            <ProtectedRoute>
              <Categories />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/training-data"
          element={
            <ProtectedRoute>
              <TrainingData />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/logs"
          element={
            <ProtectedRoute>
              <RequestLogs />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/system"
          element={
            <ProtectedRoute>
              <SystemControl />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/config"
          element={
            <ProtectedRoute>
              <Configuration />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/post-tester"
          element={
            <ProtectedRoute>
              <PostTester />
            </ProtectedRoute>
          }
        />
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
