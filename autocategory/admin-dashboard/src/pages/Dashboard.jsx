import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { logsAPI, trainingAPI, categoriesAPI, systemAPI } from '../services/api'
import {
  Activity,
  TrendingUp,
  Users,
  Database,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'

// Stat Card Component
function StatCard({ title, value, subtitle, icon: Icon, trend, color = 'blue' }) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-200',
    green: 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-200',
    yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900 dark:text-yellow-200',
    red: 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-200',
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {subtitle}
            </p>
          )}
          {trend && (
            <div className="mt-2 flex items-center text-sm">
              <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
              <span className="text-green-600 dark:text-green-400">{trend}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-8 w-8" />
        </div>
      </div>
    </div>
  )
}

// Service Status Card
function ServiceStatusCard({ service, loading }) {
  const statusColors = {
    healthy: 'text-green-600 dark:text-green-400',
    degraded: 'text-yellow-600 dark:text-yellow-400',
    unhealthy: 'text-red-600 dark:text-red-400',
  }

  const StatusIcon = service.status === 'healthy' ? CheckCircle : service.status === 'degraded' ? Clock : XCircle

  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
      <div className="flex items-center gap-3">
        <StatusIcon className={`h-6 w-6 ${statusColors[service.status]}`} />
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{service.name}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            CPU: {service.cpu_percent?.toFixed(1)}% | Memory: {service.memory_mb?.toFixed(0)}MB
          </p>
        </div>
      </div>
      <span
        className={`px-3 py-1 rounded-full text-xs font-medium ${
          service.status === 'healthy'
            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
            : service.status === 'degraded'
            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
        }`}
      >
        {service.status}
      </span>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const fetchData = async () => {
    try {
      setLoading(true)
      
      // Fetch all data in parallel
      const [logsStatsRes, trainingStatsRes, categoriesListRes, systemHealthRes] = await Promise.all([
        logsAPI.stats().catch(() => ({ data: {} })),
        trainingAPI.stats().catch(() => ({ data: {} })),
        categoriesAPI.list().catch(() => ({ data: { categories: [] } })),
        systemAPI.health().catch(() => ({ data: {} })),
      ])

      // Calculate categories stats from list
      const flatCategories = categoriesListRes.data.categories || []
      const leafCount = flatCategories.filter(cat => 
        !flatCategories.some(c => c.parent_id === cat.category_id)
      ).length

      setStats({
        logs: logsStatsRes.data,
        training: trainingStatsRes.data,
        categories: {
          total: flatCategories.length,
          leaf: leafCount,
          active: flatCategories.length,
          indexed: leafCount
        },
      })
      
      setHealth(systemHealthRes.data)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      toast.error('Không thể tải dữ liệu dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Tổng quan hệ thống phân loại tự động
          </p>
        </div>
        <button onClick={fetchData} className="btn btn-primary flex items-center gap-2">
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Requests"
          value={stats?.logs?.total_requests?.toLocaleString() || '0'}
          subtitle={`Success: ${stats?.logs?.success_rate?.toFixed(1) || '0'}%`}
          icon={Activity}
          color="blue"
        />
        
        <StatCard
          title="Training Samples"
          value={stats?.training?.total_samples?.toLocaleString() || '0'}
          subtitle={`Validated: ${stats?.training?.validated_samples?.toLocaleString() || '0'}`}
          icon={Database}
          color="green"
        />
        
        <StatCard
          title="Categories"
          value={stats?.categories?.total?.toLocaleString() || '0'}
          subtitle={`Leaf: ${stats?.categories?.leaf?.toLocaleString() || '0'}`}
          icon={FileText}
          color="yellow"
        />
        
        <StatCard
          title="Avg Response Time"
          value={`${stats?.logs?.avg_response_time?.toFixed(0) || '0'}ms`}
          subtitle={`Errors: ${stats?.logs?.error_count || '0'}`}
          icon={Clock}
          color={stats?.logs?.avg_response_time > 2000 ? 'red' : 'green'}
        />
      </div>

      {/* System Health */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            System Health
          </h2>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              health?.overall_status === 'healthy'
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : health?.overall_status === 'degraded'
                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            }`}
          >
            {health?.overall_status || 'Unknown'}
          </span>
        </div>
        
        <div className="space-y-3">
          {health?.services?.map((service) => (
            <ServiceStatusCard key={service.name} service={service} loading={loading} />
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Quick Actions
          </h2>
          <div className="space-y-2">
            <button
              onClick={() => navigate('/categories')}
              className="w-full btn btn-secondary justify-start"
            >
              <FileText className="h-5 w-5 mr-2" />
              Manage Categories
            </button>
            <button
              onClick={() => navigate('/training-data')}
              className="w-full btn btn-secondary justify-start"
            >
              <Database className="h-5 w-5 mr-2" />
              View Training Data
            </button>
            <button
              onClick={() => navigate('/system')}
              className="w-full btn btn-secondary justify-start"
            >
              <Activity className="h-5 w-5 mr-2" />
              System Control
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Recent Activity
          </h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3 text-sm">
              <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  System running smoothly
                </p>
                <p className="text-gray-500 dark:text-gray-400">All services operational</p>
              </div>
            </div>
            
            <div className="flex items-start gap-3 text-sm">
              <Activity className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {stats?.logs?.total_requests || 0} requests processed
                </p>
                <p className="text-gray-500 dark:text-gray-400">Since last restart</p>
              </div>
            </div>
            
            <div className="flex items-start gap-3 text-sm">
              <Database className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {stats?.training?.total_samples || 0} training samples
                </p>
                <p className="text-gray-500 dark:text-gray-400">
                  {stats?.training?.validation_rate?.toFixed(1) || 0}% validated
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
