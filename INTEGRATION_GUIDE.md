# Integration Guide - AutoCategory

## Overview

This guide helps you integrate AutoCategory's classification API into your e-commerce platform.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication Setup](#authentication-setup)
3. [Basic Integration](#basic-integration)
4. [Advanced Features](#advanced-features)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)
7. [Code Examples](#code-examples)

---

## Quick Start

### Step 1: Get API Key

1. Log into AutoCategory Admin Dashboard: `http://localhost:3001/admin`
2. Navigate to "API Keys" section
3. Click "Create New API Key"
4. Save the key securely (shown only once!)

### Step 2: Test API

```bash
curl -X POST http://localhost:3001/api/classify \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 14 Pro Max 256GB",
    "description": "Brand new sealed",
    "price": 25000000
  }'
```

### Step 3: Integrate into Your Platform

See [Code Examples](#code-examples) below for your language/framework.

---

## Authentication Setup

### API Key Security

**DO:**
- ✅ Store API key in environment variables
- ✅ Use server-side requests only (never expose key in frontend)
- ✅ Rotate keys regularly (every 90 days)
- ✅ Use different keys for dev/staging/production

**DON'T:**
- ❌ Commit API keys to version control
- ❌ Send API keys in URLs (use headers)
- ❌ Share keys between applications
- ❌ Expose keys in browser JavaScript

### Environment Variables

```bash
# .env file
AUTOCATEGORY_API_KEY=ac_1234567890abcdef
AUTOCATEGORY_API_URL=http://localhost:3001
```

---

## Basic Integration

### Classify Product on Listing Creation

**Workflow:**
1. User creates new listing with title/description/price
2. Call AutoCategory API before saving
3. Show predicted category to user for confirmation
4. Save listing with selected category

```python
# Django example
from django.views import View
import requests
import os

class CreateListingView(View):
    def post(self, request):
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        
        # Call AutoCategory
        response = requests.post(
            f"{os.getenv('AUTOCATEGORY_API_URL')}/api/classify",
            headers={'X-API-Key': os.getenv('AUTOCATEGORY_API_KEY')},
            json={'title': title, 'description': description, 'price': float(price)}
        )
        
        if response.status_code == 200:
            result = response.json()
            suggested_category = result['category_id']
            confidence = result['confidence']
            alternatives = result['alternatives']
            
            # Show to user for confirmation
            return render(request, 'confirm_listing.html', {
                'title': title,
                'suggested_category': suggested_category,
                'confidence': confidence,
                'alternatives': alternatives
            })
        else:
            # Handle error
            return render(request, 'error.html', {'error': 'Classification failed'})
```

### Auto-categorize Existing Listings

**Batch Processing:**

```python
import requests
import time
from typing import List, Dict

def batch_classify_listings(listings: List[Dict], api_key: str, batch_size: int = 10):
    """
    Classify multiple listings in batches
    
    Args:
        listings: List of dicts with 'id', 'title', 'description', 'price'
        api_key: AutoCategory API key
        batch_size: Number of concurrent requests (respect rate limits!)
    
    Returns:
        List of results with original id + predicted category
    """
    results = []
    
    for i in range(0, len(listings), batch_size):
        batch = listings[i:i+batch_size]
        
        for listing in batch:
            try:
                response = requests.post(
                    'http://localhost:3001/api/classify',
                    headers={'X-API-Key': api_key},
                    json={
                        'title': listing['title'],
                        'description': listing.get('description', ''),
                        'price': listing.get('price')
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results.append({
                        'id': listing['id'],
                        'category_id': result['category_id'],
                        'confidence': result['confidence']
                    })
                else:
                    results.append({
                        'id': listing['id'],
                        'error': f"HTTP {response.status_code}"
                    })
            
            except Exception as e:
                results.append({
                    'id': listing['id'],
                    'error': str(e)
                })
        
        # Respect rate limits: wait 1 second between batches
        if i + batch_size < len(listings):
            time.sleep(1)
    
    return results

# Usage
listings = [
    {'id': 1, 'title': 'iPhone 14', 'price': 20000000},
    {'id': 2, 'title': 'Samsung S23', 'price': 18000000},
    # ... more listings
]

results = batch_classify_listings(listings, api_key='your-key')
```

---

## Advanced Features

### Confidence Threshold

Only auto-accept categories above a confidence threshold:

```python
def auto_categorize_if_confident(title, description, price, threshold=0.85):
    result = classify_product(title, description, price)
    
    if result['confidence'] >= threshold:
        # High confidence - auto-assign
        return result['category_id'], True
    else:
        # Low confidence - ask user
        return result['alternatives'], False
```

### Alternative Categories

Show top 3 alternatives to users:

```javascript
async function showCategorySuggestions(title, description, price) {
  const response = await fetch('/api/classify', {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ title, description, price })
  });
  
  const result = await response.json();
  
  // Create UI with primary + alternatives
  const categories = [
    { id: result.category_id, name: result.category_name, confidence: result.confidence, isPrimary: true },
    ...result.alternatives.slice(0, 3).map(alt => ({ ...alt, isPrimary: false }))
  ];
  
  renderCategorySelector(categories);
}
```

### Feedback Loop

Send user corrections to improve model:

```python
def submit_correction(request_log_id, actual_category_id, note=None):
    """Send feedback when user corrects the prediction"""
    requests.post(
        'http://localhost:3001/api/classify/feedback',
        headers={'X-API-Key': API_KEY},
        json={
            'request_log_id': request_log_id,
            'actual_category_id': actual_category_id,
            'note': note
        }
    )
```

---

## Error Handling

### Retry Logic with Exponential Backoff

```python
import time
import requests
from requests.exceptions import RequestException

def classify_with_retry(title, description, price, max_retries=3):
    """Classify with exponential backoff retry"""
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                'http://localhost:3001/api/classify',
                headers={'X-API-Key': API_KEY},
                json={'title': title, 'description': description, 'price': price},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                # Rate limit exceeded - wait and retry
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
                continue
            
            elif response.status_code >= 500:
                # Server error - retry
                time.sleep(1)
                continue
            
            else:
                # Client error - don't retry
                raise Exception(f"API error: {response.status_code}")
        
        except RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                raise e
    
    raise Exception("Max retries exceeded")
```

### Graceful Degradation

```python
def classify_or_fallback(title, description, price, default_category_id):
    """Try to classify, fall back to default if fails"""
    
    try:
        result = classify_with_retry(title, description, price)
        return result['category_id'], result['confidence']
    
    except Exception as e:
        # Log error
        logger.error(f"Classification failed: {e}")
        
        # Use default category
        return default_category_id, 0.0
```

---

## Best Practices

### 1. Cache Results

Cache classification results to avoid redundant API calls:

```python
from django.core.cache import cache

def classify_with_cache(title, description, price):
    # Create cache key
    cache_key = f"category:{hash((title, description, price))}"
    
    # Check cache
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Call API
    result = classify_product(title, description, price)
    
    # Cache for 7 days
    cache.set(cache_key, result, 60 * 60 * 24 * 7)
    
    return result
```

### 2. Rate Limit Awareness

Track API usage to avoid hitting rate limits:

```python
import redis
from datetime import datetime, timedelta

def check_rate_limit(api_key, limit_per_hour=1000):
    r = redis.Redis()
    key = f"ratelimit:{api_key}:{datetime.now().hour}"
    
    count = r.incr(key)
    if count == 1:
        r.expire(key, 3600)  # Expire after 1 hour
    
    if count > limit_per_hour:
        raise Exception("Rate limit exceeded")
    
    return count
```

### 3. Monitor Performance

Track classification accuracy and latency:

```python
import statsd

statsd_client = statsd.StatsClient('localhost', 8125)

def classify_with_metrics(title, description, price):
    start_time = time.time()
    
    try:
        result = classify_product(title, description, price)
        
        # Track success
        statsd_client.incr('autocategory.classify.success')
        statsd_client.timing('autocategory.classify.duration', 
                            int((time.time() - start_time) * 1000))
        statsd_client.gauge('autocategory.classify.confidence', 
                           result['confidence'])
        
        return result
    
    except Exception as e:
        statsd_client.incr('autocategory.classify.error')
        raise e
```

---

## Code Examples

### Laravel (PHP)

```php
<?php
use Illuminate\Support\Facades\Http;

class CategoryService {
    protected $apiKey;
    protected $apiUrl;
    
    public function __construct() {
        $this->apiKey = env('AUTOCATEGORY_API_KEY');
        $this->apiUrl = env('AUTOCATEGORY_API_URL');
    }
    
    public function classify($title, $description = null, $price = null) {
        $response = Http::withHeaders([
            'X-API-Key' => $this->apiKey,
        ])->post("{$this->apiUrl}/api/classify", [
            'title' => $title,
            'description' => $description,
            'price' => $price,
        ]);
        
        if ($response->successful()) {
            return $response->json();
        }
        
        throw new Exception("Classification failed: " . $response->status());
    }
}

// Usage
$service = new CategoryService();
$result = $service->classify('iPhone 14 Pro Max', 'Brand new', 25000000);
echo "Category: " . $result['category_name'];
```

### Express.js (Node.js)

```javascript
const axios = require('axios');

class AutoCategoryClient {
  constructor(apiKey, apiUrl = 'http://localhost:3001') {
    this.apiKey = apiKey;
    this.apiUrl = apiUrl;
  }
  
  async classify(title, description = null, price = null) {
    try {
      const response = await axios.post(
        `${this.apiUrl}/api/classify`,
        { title, description, price },
        {
          headers: { 'X-API-Key': this.apiKey },
          timeout: 10000
        }
      );
      
      return response.data;
    } catch (error) {
      if (error.response) {
        throw new Error(`API error: ${error.response.status}`);
      } else {
        throw error;
      }
    }
  }
  
  async submitFeedback(requestLogId, actualCategoryId, note = null) {
    await axios.post(
      `${this.apiUrl}/api/classify/feedback`,
      {
        request_log_id: requestLogId,
        actual_category_id: actualCategoryId,
        note
      },
      {
        headers: { 'X-API-Key': this.apiKey }
      }
    );
  }
}

// Usage
const client = new AutoCategoryClient(process.env.AUTOCATEGORY_API_KEY);

app.post('/listings', async (req, res) => {
  const { title, description, price } = req.body;
  
  try {
    const result = await client.classify(title, description, price);
    
    res.json({
      suggestedCategory: result.category_id,
      categoryName: result.category_name,
      confidence: result.confidence,
      alternatives: result.alternatives
    });
  } catch (error) {
    res.status(500).json({ error: 'Classification failed' });
  }
});
```

### Ruby on Rails

```ruby
# app/services/auto_category_service.rb
require 'net/http'
require 'json'

class AutoCategoryService
  API_URL = ENV['AUTOCATEGORY_API_URL']
  API_KEY = ENV['AUTOCATEGORY_API_KEY']
  
  def self.classify(title, description = nil, price = nil)
    uri = URI("#{API_URL}/api/classify")
    
    request = Net::HTTP::Post.new(uri)
    request['X-API-Key'] = API_KEY
    request['Content-Type'] = 'application/json'
    request.body = {
      title: title,
      description: description,
      price: price
    }.to_json
    
    response = Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) do |http|
      http.request(request)
    end
    
    if response.code == '200'
      JSON.parse(response.body)
    else
      raise "Classification failed: #{response.code}"
    end
  end
end

# Usage in controller
class ListingsController < ApplicationController
  def create
    result = AutoCategoryService.classify(
      params[:title],
      params[:description],
      params[:price]
    )
    
    @listing = Listing.new(listing_params)
    @listing.category_id = result['category_id']
    @listing.save
    
    render json: { category: result['category_name'], confidence: result['confidence'] }
  end
end
```

---

## Webhook Integration

### Receive Category Updates

Register a webhook endpoint to receive category sync notifications:

```python
from flask import Flask, request
import hmac
import hashlib

app = Flask(__name__)

@app.route('/webhooks/category-sync', methods=['POST'])
def handle_category_sync():
    # Verify signature (optional but recommended)
    signature = request.headers.get('X-AutoCategory-Signature')
    if not verify_signature(request.data, signature):
        return 'Invalid signature', 401
    
    data = request.json
    
    if data['event'] == 'category.sync':
        # Update local category cache
        updated_categories = data['data']['categories']
        update_local_categories(updated_categories)
        
        return 'OK', 200
    
    return 'Unknown event', 400

def verify_signature(payload, signature):
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

---

## Support & Resources

- **API Documentation:** http://localhost:3001/docs
- **Support Email:** admin@localhost
- **Status Page:** http://localhost:3001/api/health
- **Community Forum:** http://localhost:3001
