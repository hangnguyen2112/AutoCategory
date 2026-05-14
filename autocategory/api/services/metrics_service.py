"""
Prometheus Metrics Exporter for AutoCategory API

Exposes metrics in Prometheus format:
- Request count, duration, status codes
- Classification metrics (confidence, accuracy)
- Business metrics (categories used, feedback rate)
- System metrics (database connections, cache hit rate)
"""

from typing import Dict

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import Response


# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Classification metrics
classification_requests_total = Counter(
    'classification_requests_total',
    'Total classification requests',
    ['model_version']
)

classification_confidence = Histogram(
    'classification_confidence',
    'Classification confidence scores',
    ['category'],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99)
)

classification_categories = Counter(
    'classification_categories_total',
    'Classifications by category',
    ['category_id', 'category_name']
)

user_feedback_total = Counter(
    'user_feedback_total',
    'User feedback submissions',
    ['feedback_type']
)

# Database metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Cache misses',
    ['cache_type']
)

# Training pipeline metrics
training_job_status = Gauge(
    'training_job_status',
    'Training job status',
    ['job_id', 'status']
)

model_accuracy = Gauge(
    'model_accuracy',
    'Model accuracy score',
    ['model_id']
)

model_version_active = Gauge(
    'model_version_active',
    'Active model version',
    ['model_id', 'model_type']
)

# Business metrics
training_samples_total = Gauge(
    'training_samples_total',
    'Total training samples'
)

training_samples_validated = Gauge(
    'training_samples_validated',
    'Validated training samples'
)

api_keys_active = Gauge(
    'api_keys_active',
    'Number of active API keys'
)

categories_total = Gauge(
    'categories_total',
    'Total categories'
)


def metrics_endpoint():
    """FastAPI endpoint to expose Prometheus metrics"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsMiddleware:
    """Middleware to automatically track request metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        import time
        start_time = time.time()
        
        # Track request
        method = scope["method"]
        path = scope["path"]
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status = message["status"]
                duration = time.time() - start_time
                
                # Record metrics
                http_requests_total.labels(
                    method=method,
                    endpoint=path,
                    status=status
                ).inc()
                
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=path
                ).observe(duration)
            
            await send(message)
        
        return await self.app(scope, receive, send_wrapper)


def update_business_metrics(db_stats: Dict):
    """Update business metrics from database stats"""
    training_samples_total.set(db_stats.get("total_training_samples", 0))
    training_samples_validated.set(db_stats.get("validated_samples", 0))
    api_keys_active.set(db_stats.get("active_api_keys", 0))
    categories_total.set(db_stats.get("total_categories", 0))


def record_classification(category_id: int, category_name: str, confidence: float, model_version: str):
    """Record a classification event"""
    classification_requests_total.labels(model_version=model_version).inc()
    classification_confidence.labels(category=str(category_id)).observe(confidence)
    classification_categories.labels(
        category_id=str(category_id),
        category_name=category_name
    ).inc()


def record_cache_hit(cache_type: str):
    """Record a cache hit"""
    cache_hits_total.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str):
    """Record a cache miss"""
    cache_misses_total.labels(cache_type=cache_type).inc()


def record_db_connection(count: int):
    """Update active database connections"""
    db_connections_active.set(count)


def record_db_query(query_type: str, duration: float):
    """Record database query duration"""
    db_query_duration_seconds.labels(query_type=query_type).observe(duration)


def record_feedback(feedback_type: str):
    """Record user feedback"""
    user_feedback_total.labels(feedback_type=feedback_type).inc()


def record_training_job(job_id: str, status: str):
    """Record training job status"""
    # Reset all status values for this job
    for s in ["queued", "running", "completed", "failed"]:
        training_job_status.labels(job_id=job_id, status=s).set(0)
    # Set current status
    training_job_status.labels(job_id=job_id, status=status).set(1)


def record_model_accuracy(model_id: str, accuracy: float):
    """Record model accuracy"""
    model_accuracy.labels(model_id=model_id).set(accuracy)


def set_active_model(model_id: str, model_type: str):
    """Set the active model version"""
    model_version_active.labels(model_id=model_id, model_type=model_type).set(1)
