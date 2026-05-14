# Admin Manual - AutoCategory

## Overview

This manual provides step-by-step instructions for administrators using the AutoCategory Admin Dashboard.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [User Management](#user-management)
4. [API Key Management](#api-key-management)
5. [Category Management](#category-management)
6. [Training Data Management](#training-data-management)
7. [Request Logs](#request-logs)
8. [System Control](#system-control)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Login

1. Open browser and navigate to: `http://localhost:3001/admin`
2. Default credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. **⚠️ Important:** Change password immediately after first login!

### Changing Your Password

1. Click on your username in top right
2. Select "Change Password"
3. Enter current password and new password
4. Click "Save"

### User Roles

- **Admin:** Full access to all features
- **Developer:** Can manage API keys and view logs
- **Viewer:** Read-only access

---

## Dashboard Overview

The main dashboard shows:

### Key Metrics (Top Cards)
- **Total Requests:** Number of classification API calls (today/total)
- **Training Samples:** Number of validated training samples
- **Categories:** Total categories in system
- **Avg Response Time:** Average API response time

### Service Status
Real-time status of all services:
- API (FastAPI backend)
- LLM (llama-server)
- Qdrant (vector database)
- PostgreSQL (main database)
- Redis (cache)

**Status Colors:**
- 🟢 Green: Running normally
- 🟡 Yellow: Degraded performance
- 🔴 Red: Service down

### Quick Actions
- Sync Categories
- Rebuild Index
- View Logs
- Clear Cache

### Recent Activity
Shows last 10 system events

---

## User Management

### Viewing Users

1. Click "Users" in left sidebar
2. View list of all users with:
   - Username, email, full name
   - Role (Admin/Developer/Viewer)
   - Status (Active/Inactive)
   - Last login time

### Creating a New User

1. Click "Create User" button
2. Fill in form:
   - **Username:** Unique, 3-20 characters, alphanumeric only
   - **Email:** Valid email address
   - **Password:** Minimum 8 characters
   - **Full Name:** User's display name
   - **Role:** Select Admin/Developer/Viewer
3. Click "Create"
4. Share credentials securely with new user

### Editing a User

1. Find user in list
2. Click "Edit" button
3. Modify fields (cannot change username)
4. Click "Save"

**Note:** You cannot edit your own role to prevent lockout.

### Deleting a User

1. Find user in list
2. Click "Delete" button
3. Confirm deletion in popup
4. User will be permanently deleted

**⚠️ Warning:** Cannot delete yourself or the last admin user.

### Searching Users

Use search box to filter by:
- Username
- Email
- Full name

Use role dropdown to filter by role.

---

## API Key Management

### Viewing API Keys

1. Click "API Keys" in sidebar
2. View list showing:
   - Key (partially masked: `ac_1234****`)
   - Name/description
   - Owner
   - Rate limit
   - Usage count
   - Status (Active/Expired/Expires Soon)
   - Expiry date

### Creating an API Key

1. Click "Create API Key" button
2. Fill in form:
   - **Name:** Descriptive name (e.g., "Production API")
   - **Rate Limit:** Requests per hour (default: 1000)
   - **Expires In:** Days until expiry (default: 365)
3. Click "Create"
4. **⚠️ CRITICAL:** Copy the full API key immediately!
   ```
   ac_1234567890abcdef1234567890abcdef
   ```
5. Save it securely (e.g., password manager)
6. The key will never be shown again!

### Viewing API Key Usage

1. Find key in list
2. Click on key name to view details:
   - Total requests
   - Requests this hour
   - Last used timestamp
   - Rate limit status
3. See example cURL command for testing

### Deactivating an API Key

1. Find key in list
2. Click "Deactivate" button
3. Confirm action
4. Key will immediately stop working

### Deleting an API Key

1. Find key in list
2. Click "Delete" button
3. Confirm deletion
4. Key will be permanently removed

**⚠️ Warning:** Deleting a key will break any applications using it!

---

## Category Management

### Viewing Categories

1. Click "Categories" in sidebar
2. View category tree with:
   - ID, name, level
   - Active/Inactive status
   - Number of child categories
   - Last sync time

### Expanding/Collapsing Tree

- Click ▶️ to expand category
- Click ▼ to collapse category
- Click "Expand All" to see full tree
- Click "Collapse All" to see only root categories

### Syncing Categories from Main System

1. Click "Sync Categories" button
2. Choose sync source:
   - **From Main DB:** Sync from production database
   - **From API:** Sync via API endpoint
3. Click "Start Sync"
4. Wait for sync to complete (usually 1-2 minutes)
5. View sync results:
   - Categories added
   - Categories updated
   - Categories deactivated
   - Total categories

### Viewing Sync History

1. Click "Sync History" button
2. View list of past syncs:
   - Timestamp
   - Source
   - Changes made
   - Status (Success/Failed)
3. Click on sync to view details

### Importing Categories from JSON

1. Click "Import JSON" button
2. Select JSON file from computer
3. File format:
   ```json
   [
     {
       "id": 123,
       "name": "Category Name",
       "parent_id": 122,
       "is_active": true
     }
   ]
   ```
4. Click "Upload"
5. System validates file format
6. Review changes before confirming
7. Click "Confirm Import"

### Exporting Categories

1. Click "Export JSON" button
2. Download `categories_YYYYMMDD_HHMMSS.json`
3. File can be used for backup or import elsewhere

### Rebuilding Qdrant Index

**When to rebuild:**
- After bulk category import
- If search results seem incorrect
- After Qdrant server restart

**How to rebuild:**
1. Click "Rebuild Index" button
2. **⚠️ Warning:** This is a dangerous operation!
3. Read warning message carefully
4. Type "REBUILD" to confirm
5. Click "Start Rebuild"
6. Wait for completion (5-15 minutes depending on size)
7. System will be unavailable during rebuild

---

## Training Data Management

### Viewing Training Samples

1. Click "Training Data" in sidebar
2. View table with:
   - ID, title, description preview
   - Category
   - Confidence score
   - Validation status (✅ Validated, ⏳ Pending)
   - Source (Feedback/Manual/Import)

### Filtering Samples

**By Search:**
- Enter text in search box
- Searches title and description

**By Source:**
- Select from dropdown: All/Feedback/Manual/Import

**By Validation Status:**
- Select: All/Validated/Pending

### Viewing Sample Details

1. Click "View" button on any sample
2. Modal shows:
   - Full title and description
   - Price
   - Actual category (correct)
   - Predicted category (what model said)
   - Confidence score
   - Source
   - Validation status
   - Created/validated timestamps

### Validating a Sample

**From details modal:**
1. Click "View" on sample
2. Review information carefully
3. Click "Validate" if correct
4. Sample marked as validated ✅

**Bulk validation:**
1. Click "Bulk Validate" button
2. System selects up to 50 unvalidated samples
3. Reviews them automatically
4. Marks valid ones as validated
5. Shows summary of results

### Adding Training Sample Manually

1. Click "Add Sample" button
2. Fill in form:
   - **Title:** Product title (required)
   - **Description:** Product description (optional)
   - **Price:** Price in VND (optional)
   - **Category:** Select correct category (required)
   - **Source:** Auto-set to "manual"
3. Click "Create"
4. Sample added to training data

**When to add manually:**
- Important edge cases
- Underrepresented categories
- Complex products

### Deleting a Sample

1. Click "View" on sample
2. Click "Delete" button
3. Confirm deletion
4. Sample permanently removed

### Exporting Training Data

1. Click "Export Data" button
2. Downloads `training_data_YYYYMMDD_HHMMSS.json`
3. Contains all samples in JSON format

---

## Request Logs

### Viewing Logs

1. Click "Request Logs" in sidebar
2. View table with:
   - Timestamp
   - Endpoint (classify/generate/auth/admin)
   - HTTP status code
   - Response time (color-coded: 🟢<1s, 🟡<2s, 🔴>2s)
   - Title (for classification requests)
   - Category predicted
   - Confidence

### Filtering Logs

**By Date Range:**
- Select start and end dates
- Click "Apply"

**By Endpoint:**
- Select from dropdown: All/Classify/Generate/Auth/Admin

**By Status Code:**
- Select: All/2xx (Success)/4xx (Client Error)/5xx (Server Error)

**By Search:**
- Enter text to search endpoint or title

### Viewing Log Details

1. Click "View Details" on any log
2. Modal shows:
   - Full request details (URL, method, headers)
   - Request body
   - Response status and time
   - Response body
   - Classification details (if classify request)
   - IP address and user agent
   - Timestamp

### Exporting Logs to CSV

1. Apply filters if desired
2. Click "Export CSV" button
3. Downloads `request_logs_YYYYMMDD_HHMMSS.csv`
4. Can open in Excel or Google Sheets

### Cleaning Up Old Logs

**Manual cleanup:**
1. Click "Cleanup Old Logs" button
2. Confirm deletion of logs older than 30 days
3. System deletes old logs to free space

**Automatic cleanup:**
- Runs daily at midnight
- Keeps last 30 days of logs
- Can be configured in system settings

---

## System Control

### Service Management

**Viewing Service Status:**
- Dashboard shows 5 services
- Each service card displays:
  - Status (Running/Stopped)
  - CPU usage %
  - Memory usage MB
  - Uptime

**Starting a Service:**
1. Find service card
2. Click "Start" button
3. Wait for service to start (usually <30s)
4. Status changes to "Running"

**Stopping a Service:**
1. Click "Stop" button
2. Confirm action
3. Service stops gracefully
4. Status changes to "Stopped"

**Restarting a Service:**
1. Click "Restart" button
2. Service stops then starts again
3. Useful for applying config changes

**⚠️ Warning:** Stopping API or Qdrant will make system unavailable!

### System Metrics

**CPU Usage:**
- Overall system CPU percentage
- Color-coded: Green <70%, Yellow <90%, Red >90%

**Memory Usage:**
- RAM usage in MB and percentage
- Color-coded thresholds

**Disk Usage:**
- Available/total disk space
- Color-coded by percentage

**System Load:**
- 1-minute, 5-minute, 15-minute averages
- Indicates system stress level

### Database Statistics

- Total connections (active/idle)
- Active queries running now
- Database size in MB
- Total tables

### Cache Management

**Clear Redis Cache:**
1. Click "Clear Redis Cache" button
2. Confirm action
3. All cached data removed (API keys, rate limits, sessions)

**Clear Vector Cache:**
1. Click "Clear Vector Cache" button
2. Confirm action
3. Qdrant embeddings cache cleared

**Clear All Caches:**
1. Click "Clear All" button
2. Confirm action (dangerous!)
3. All caches cleared

**⚠️ When to clear cache:**
- After updating categories
- After model deployment
- If seeing stale data

### Viewing System Logs

1. Scroll to "Recent Logs" section
2. View last 50 lines of API logs
3. Auto-scrolls to bottom
4. Shows errors in red, warnings in yellow

### Auto-Refresh

- Toggle "Auto Refresh" switch
- When ON: Page refreshes every 30 seconds
- When OFF: Manual refresh only

---

## Configuration

### Viewing Configurations

1. Click "Configuration" in sidebar
2. View table with:
   - Key (config name)
   - Value (hidden if secret)
   - Type (string/int/float/bool/json)
   - Category (general/llm/qdrant/api/auth)
   - Description

### Filtering Configurations

**By Search:**
- Search key or description

**By Category:**
- Select from dropdown: General/LLM/Qdrant/API/Auth

### Creating a Configuration

1. Click "Create Config" button
2. Fill in form:
   - **Key:** Unique identifier (e.g., `llm.max_tokens`)
   - **Value:** Configuration value
   - **Type:** Select string/int/float/bool/json
   - **Category:** Select category for grouping
   - **Description:** What this config does
   - **Is Secret:** Check if sensitive (e.g., API key)
3. Click "Create"

### Editing a Configuration

1. Find config in list
2. Click "Edit" button
3. Modify value (cannot change key)
4. Click "Save"
5. Some configs require service restart to take effect

### Viewing/Hiding Secret Values

1. Find secret config (shows ••••••••)
2. Click 👁️ icon to reveal
3. Click again to hide

### Bulk Updating Configurations

1. Select multiple configs using checkboxes
2. Click "Bulk Update (N)" button
3. Enter new values for each selected config
4. Click "Save All"
5. All configs updated at once

### Deleting a Configuration

1. Find config in list
2. Click "Delete" button
3. Confirm deletion
4. Config permanently removed

**⚠️ Warning:** Deleting critical configs can break the system!

---

## Troubleshooting

### Login Issues

**Problem:** Cannot log in
**Solutions:**
1. Check username/password (case-sensitive)
2. Try password reset if available
3. Check if account is active (contact super admin)
4. Clear browser cookies and try again

### Slow Performance

**Problem:** Dashboard is slow
**Solutions:**
1. Check system metrics for CPU/memory issues
2. Clear browser cache
3. Restart services if needed
4. Check if database is under load

### Classification Not Working

**Problem:** API returns errors
**Solutions:**
1. Check service status (API, LLM, Qdrant)
2. View request logs for error details
3. Verify categories are synced
4. Check if Qdrant index is built
5. Restart LLM service if needed

### Categories Not Showing

**Problem:** Category list is empty
**Solutions:**
1. Run "Sync Categories" from main system
2. Or import categories from JSON backup
3. Check sync history for errors
4. Verify database connection

### Training Data Not Saving

**Problem:** Cannot add training samples
**Solutions:**
1. Check if category ID exists and is active
2. Verify category is a leaf (not parent)
3. Check validation errors in form
4. View system logs for database errors

### Services Keep Stopping

**Problem:** Services crash frequently
**Solutions:**
1. Check system resources (CPU, memory, disk)
2. View service logs for error messages
3. Increase resource limits if needed
4. Check for memory leaks

### High Response Times

**Problem:** API is slow (>2s)
**Solutions:**
1. Check LLM service status and CPU usage
2. Clear Qdrant cache and rebuild index
3. Check database query performance
4. Enable Redis caching if not already
5. Scale up resources (CPU, RAM)

---

## Best Practices

### Daily Tasks

- [ ] Check dashboard for service health
- [ ] Review request logs for errors
- [ ] Monitor response times
- [ ] Check for failed classification requests

### Weekly Tasks

- [ ] Review training data quality
- [ ] Validate pending samples
- [ ] Check API key usage and expiry
- [ ] Review user activity logs
- [ ] Backup categories and training data

### Monthly Tasks

- [ ] Audit user accounts (remove inactive)
- [ ] Rotate API keys
- [ ] Review and update configurations
- [ ] Analyze classification accuracy trends
- [ ] Plan model retraining if needed

### Security

- ✅ Use strong passwords (12+ chars, mixed case, numbers, symbols)
- ✅ Change default admin password immediately
- ✅ Limit admin role to trusted users only
- ✅ Rotate API keys every 90 days
- ✅ Review user access regularly
- ✅ Monitor logs for suspicious activity
- ✅ Keep backup of categories and training data

---

## Support Contacts

- **Technical Support:** admin@localhost
- **Emergency Hotline:** +84 xxx xxx xxxx
- **Documentation:** http://localhost:3001/docs
- **Status Page:** http://localhost:3001/api/health
