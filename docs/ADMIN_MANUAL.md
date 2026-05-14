# Admin Manual - AutoCategory System

**Version:** 1.0.0  
**Last Updated:** 2026-05-06  
**Target Audience:** System administrators

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [User Management](#user-management)
4. [API Key Management](#api-key-management)
5. [System Control](#system-control)
6. [Configuration](#configuration)
7. [Category Management](#category-management)
8. [Training Pipeline](#training-pipeline)
9. [Monitoring](#monitoring)
10. [Data Management](#data-management)
11. [Troubleshooting](#troubleshooting)
12. [Security](#security)

---

## 1. Getting Started

### 1.1 First Login

**URL:** `http://localhost:3001/admin`

**Default Credentials:**
```
Username: admin
Password: [provided by deployment team]
```

⚠️ **IMPORTANT:** Change password immediately after first login!

### 1.2 Change Password

```
1. Click profile icon (top right)
2. Select "Change Password"
3. Enter current password
4. Enter new password (min 12 chars, mixed case, numbers, symbols)
5. Confirm new password
6. Click "Update"
```

### 1.3 Dashboard Navigation

```
├── Overview          - System metrics & quick stats
├── System Control    - Start/stop services
├── Configuration     - System settings
├── Users             - User & API key management
├── Categories        - Category CRUD & sync
├── Training          - Model training & evaluation
└── Monitoring        - Logs, metrics, alerts
```

---

## 2. Dashboard Overview

### 2.1 Overview Page

**What you see:**

```
┌─────────────────────────────────────────────────┐
│  AutoCategory Admin Dashboard                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Request Statistics (24h)                    │
│  ┌─────────┬──────────┬──────────┬──────────┐  │
│  │ Total   │ Success  │ Errors   │ Avg Time │  │
│  │ 1,234   │ 1,198    │ 36       │ 342ms    │  │
│  └─────────┴──────────┴──────────┴──────────┘  │
│                                                 │
│  🤖 Model Performance                           │
│  ┌────────────────┬─────────┬─────────────┐    │
│  │ Decision Type  │ Count   │ Percentage  │    │
│  ├────────────────┼─────────┼─────────────┤    │
│  │ Auto Assign    │ 890     │ 72%         │    │
│  │ Preselect      │ 234     │ 19%         │    │
│  │ Suggest Top 3  │ 89      │ 7%          │    │
│  │ Manual Select  │ 21      │ 2%          │    │
│  └────────────────┴─────────┴─────────────┘    │
│                                                 │
│  💻 System Health                               │
│  ┌─────────────┬────────┬────────┬─────────┐   │
│  │ Component   │ Status │ CPU    │ Memory  │   │
│  ├─────────────┼────────┼────────┼─────────┤   │
│  │ API         │ 🟢 UP  │ 12%    │ 512MB   │   │
│  │ LLM Server  │ 🟢 UP  │ 45%    │ 6GB     │   │
│  │ Qdrant      │ 🟢 UP  │ 8%     │ 1.2GB   │   │
│  │ PostgreSQL  │ 🟢 UP  │ 5%     │ 256MB   │   │
│  └─────────────┴────────┴────────┴─────────┘   │
│                                                 │
│  ⚠️ Recent Alerts                               │
│  • High error rate in last hour (3.2%)         │
│  • Training data needs rebalancing             │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Actions:**
- Click metrics for detailed view
- Click components for logs
- Click alerts for details

---

## 3. User Management

### 3.1 View Users

```
Navigate: Users → All Users

You'll see:
┌────┬──────────┬───────────────────────┬────────┬────────────┐
│ ID │ Username │ Email                 │ Role   │ Status     │
├────┼──────────┼───────────────────────┼────────┼────────────┤
│ 1  │ admin    │ admin@example.com     │ Admin  │ 🟢 Active  │
│ 2  │ john     │ john@example.com      │ Editor │ 🟢 Active  │
│ 3  │ jane     │ jane@example.com      │ Viewer │ 🔴 Blocked │
└────┴──────────┴───────────────────────┴────────┴────────────┘
```

### 3.2 Create New User

```
1. Click "Add User" button
2. Fill form:
   - Username: john_dev
   - Email: john@example.com
   - Password: [auto-generated or custom]
   - Role: [select from dropdown]
   - Send welcome email: ☑
3. Click "Create"
```

**Available Roles:**

| Role | Permissions |
|------|-------------|
| **Admin** | Full access (users, config, training, deploy) |
| **Editor** | Manage categories, training data, view monitoring |
| **Operator** | Start/stop services, view logs, basic config |
| **Viewer** | Read-only access to dashboard |

### 3.3 Edit User

```
1. Click user row
2. Modify fields
3. Click "Save"
```

**Can change:**
- Email
- Role
- Status (Active/Blocked)
- Password reset (force on next login)

### 3.4 Block/Unblock User

```
1. Select user
2. Click "Block User" or "Unblock User"
3. Confirm action
```

**Effect:**
- Blocked users cannot login
- Existing sessions terminated
- API keys remain valid (block separately)

### 3.5 Delete User

⚠️ **WARNING:** Cannot be undone!

```
1. Select user
2. Click "Delete User"
3. Type username to confirm
4. Click "Confirm Delete"
```

**What happens:**
- User account deleted
- API keys revoked
- Activity logs preserved
- Created data (categories, training) NOT deleted

---

## 4. API Key Management

### 4.1 View API Keys

```
Navigate: Users → API Keys

┌──────────────────────┬──────────┬─────────┬────────────┬─────────┐
│ Key (masked)         │ Name     │ Owner   │ Created    │ Status  │
├──────────────────────┼──────────┼─────────┼────────────┼─────────┤
│ sk_live_abc...xyz123 │ Prod API │ john    │ 2026-01-15 │ 🟢 Active│
│ sk_test_def...uvw456 │ Test API │ jane    │ 2026-02-20 │ 🟢 Active│
│ sk_live_ghi...rst789 │ Mobile   │ john    │ 2025-12-10 │ 🔴 Revoked│
└──────────────────────┴──────────┴─────────┴────────────┴─────────┘
```

### 4.2 Create API Key

```
1. Click "Create API Key"
2. Fill form:
   - Name: Production Frontend API
   - Environment: Production / Test
   - Rate Limit: [select tier]
   - Expires: [date or "Never"]
   - Scopes: ☑ classify ☑ generate ☐ admin
3. Click "Generate"
```

**⚠️ IMPORTANT:** Key shown only once! Copy immediately!

```
┌───────────────────────────────────────────────┐
│ API Key Created Successfully!                 │
├───────────────────────────────────────────────┤
│                                               │
│  sk_live_**
│                                               │
│  📋 Copy to clipboard                         │
│                                               │
│  ⚠️ This key will not be shown again!        │
│     Store it securely.                        │
│                                               │
│  Rate Limit: 120 req/min                      │
│  Expires: Never                               │
│  Scopes: classify, generate                   │
│                                               │
└───────────────────────────────────────────────┘
```

### 4.3 Rate Limit Tiers

| Tier | Req/Min | Req/Day | Monthly Cost |
|------|---------|---------|--------------|
| Free | 10 | 100 | $0 |
| Developer | 60 | 1,000 | $29 |
| Production | 120 | 10,000 | $99 |
| Enterprise | Custom | Custom | Contact |

### 4.4 Revoke API Key

```
1. Select API key
2. Click "Revoke"
3. Confirm action
```

**Effect:**
- Key immediately invalid
- All requests return 401
- Cannot be un-revoked (create new key instead)

### 4.5 Monitor API Key Usage

```
1. Click API key row
2. View usage stats:
   - Requests (24h, 7d, 30d)
   - Success/error rate
   - Rate limit hits
   - Top endpoints used
   - Geographic distribution
```

---

## 5. System Control

### 5.1 View Service Status

```
Navigate: System Control

┌──────────────┬────────┬────────────────────┬─────────┐
│ Service      │ Status │ Uptime             │ Actions │
├──────────────┼────────┼────────────────────┼─────────┤
│ API          │ 🟢 UP  │ 5d 3h 22m          │ [Restart]│
│ LLM Server   │ 🟢 UP  │ 5d 3h 20m          │ [Restart]│
│ Ollama       │ 🟢 UP  │ 5d 3h 19m          │ [Restart]│
│ Qdrant       │ 🟢 UP  │ 5d 3h 21m          │ [Restart]│
│ PostgreSQL   │ 🟢 UP  │ 15d 8h 45m         │ [Restart]│
│ Redis        │ 🟢 UP  │ 15d 8h 45m         │ [Restart]│
└──────────────┴────────┴────────────────────┴─────────┘

[⏸️ Stop All Services]  [🔄 Restart All Services]
```

### 5.2 Restart Individual Service

```
1. Click [Restart] button for service
2. Confirm: "Restart [Service Name]?"
3. Wait for status update (30-60 seconds)
```

**What happens:**
- Service gracefully shut down
- Pending requests completed (if possible)
- Service restarted with current config
- Health check performed

**Safe to restart anytime:**
- API (rolling restart if multiple instances)
- Redis (cached data regenerated)

**⚠️ Restart with caution:**
- LLM Server (ongoing requests fail)
- Qdrant (ongoing searches fail)

**❌ Rarely need to restart:**
- PostgreSQL (only for config changes)

### 5.3 Restart All Services

⚠️ **WARNING:** System will be unavailable for 1-2 minutes!

```
1. Click "Restart All Services"
2. Type "restart" to confirm
3. Click "Confirm"
```

**Order:**
1. API stops (reject new requests)
2. LLM/Ollama stop
3. Qdrant stops
4. Services restart in reverse order
5. Health checks performed
6. API starts accepting requests

### 5.4 View Service Logs

```
1. Click service name
2. View real-time logs
3. Filter by level: INFO, WARNING, ERROR
4. Search logs
5. Download logs (last 24h)
```

---

## 6. Configuration

### 6.1 View Current Config

```
Navigate: Configuration

┌─────────────────────────────────────────────────────┐
│ LLM Configuration                                   │
├─────────────────────────────────────────────────────┤
│ Model Name:          gemma4-e4b                     │
│ Base URL:            http://llm-server:8080/v1      │
│ Temperature:         0.1                            │
│ Max Tokens:          512                            │
│                                      [Edit] [Test]  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Embedding Configuration                             │
├─────────────────────────────────────────────────────┤
│ Model:               nomic-embed-text               │
│ Service:             Ollama                         │
│ Base URL:            http://ollama:11434            │
│                                      [Edit] [Test]  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Classification Thresholds                           │
├─────────────────────────────────────────────────────┤
│ Auto Assign:         ≥ 0.90                         │
│ Preselect:          0.75 - 0.89                     │
│ Suggest Top 3:      0.55 - 0.74                     │
│ Manual Select:       < 0.55                         │
│                                            [Edit]   │
└─────────────────────────────────────────────────────┘
```

### 6.2 Edit Configuration

```
1. Click [Edit] button
2. Modify values
3. Click "Test Configuration" (validates changes)
4. If test passes, click "Save"
5. Click "Apply Changes" to activate
```

**⚠️ Changes require service restart!**

### 6.3 ProtonX API Key (for future integration)

```
Navigate: Configuration → External Services

┌─────────────────────────────────────────────────────┐
│ ProtonX API Configuration                           │
├─────────────────────────────────────────────────────┤
│ API Key:             [●●●●●●●●●●●●●●●●●●●●]  [Show]  │
│ Endpoint:            https://api.protonx.ai/v1      │
│ Status:              🟢 Connected                   │
│ Last Test:           2026-05-06 10:30:00            │
│                               [Test] [Update]       │
└─────────────────────────────────────────────────────┘
```

### 6.4 Test Configuration

```
1. Click [Test] button
2. System runs validation:
   ✓ LLM server connectivity
   ✓ Sample inference
   ✓ Response time check
   ✓ Model compatibility
3. View test results
4. Save if all tests pass
```

---

## 7. Category Management

### 7.1 View Categories

```
Navigate: Categories

Tree view:
📂 Điện tử (1)
  📂 Điện thoại (120)
    📄 iPhone (123)
    📄 Samsung (124)
    📄 Xiaomi (125)
  📂 Laptop (200)
    📄 MacBook (210)
    📄 Dell (220)
📂 Thời trang (2)
  📄 Áo nam (210)
  📄 Quần nữ (220)
```

### 7.2 Add Category

```
1. Click "Add Category"
2. Fill form:
   - ID: [auto or manual]
   - Name: iPhone
   - Parent: Điện thoại
   - Description: Các sản phẩm iPhone của Apple
   - Keywords: iphone, apple, ios
   - Active: ☑
3. Click "Create"
4. Click "Rebuild Vectors" to index new category
```

### 7.3 Edit Category

```
1. Click category name
2. Edit fields
3. Click "Save"
4. If description changed, click "Rebuild Vectors"
```

### 7.4 Sync Categories from Main System

**Scenario:** Main e-commerce system has updated categories

```
1. Navigate: Categories → Sync
2. Enter main system URL: https://main.example.com/api/categories
3. Click "Fetch Categories"
4. Review changes:
   - ✅ 5 new categories
   - ⚠️ 2 modified categories
   - ❌ 1 deleted category
5. Click "Preview Import"
6. Verify no errors
7. Click "Apply Sync"
8. Wait for completion
9. Click "Rebuild Vectors"
```

**Auto-sync (planned):**
- Webhook from main system → auto-sync
- Or scheduled sync every 6 hours

### 7.5 Rebuild Vector Index

⚠️ **Required after category changes!**

```
1. Navigate: Categories → Actions
2. Click "Rebuild Vector Index"
3. Confirm action
4. Monitor progress:
   - Generating embeddings: 50/100
   - Indexing in Qdrant: 75/100
5. Wait for completion (1-5 minutes)
6. Verify: Run test classification
```

**When to rebuild:**
- Added/modified categories
- Changed category descriptions
- After bulk import
- Switched embedding model

---

## 8. Training Pipeline

### 8.1 View Training Data

```
Navigate: Training → Data

┌─────┬─────────────────────────┬──────────────┬─────────────┬────────┐
│ ID  │ Title                   │ Category     │ Source      │ Status │
├─────┼─────────────────────────┼──────────────┼─────────────┼────────┤
│ 123 │ iPhone 15 Pro Max...    │ iPhone       │ Feedback    │ ✅ Valid│
│ 124 │ Laptop Dell i5...       │ Dell         │ Manual      │ ✅ Valid│
│ 125 │ dt ip 15...             │ iPhone       │ Feedback    │ ⚠️ Review│
└─────┴─────────────────────────┴──────────────┴─────────────┴────────┘

Total: 1,234 samples | Valid: 1,190 | Need Review: 44
```

### 8.2 Import Training Data

```
1. Navigate: Training → Import
2. Click "Choose File"
3. Select JSONL file (see DATA_STANDARDS.md)
4. Click "Validate"
5. Review validation report:
   ✓ Format: OK
   ✓ All category IDs exist
   ⚠️ 5 warnings (empty descriptions)
6. Click "Import"
7. Wait for completion
```

### 8.3 Review Training Data

```
1. Navigate: Training → Review Queue
2. See items needing review:
   - Empty/short descriptions
   - Unusual titles
   - Conflicting categories
3. For each item:
   - Keep ✅
   - Edit ✏️
   - Delete 🗑️
4. Click "Save Changes"
```

### 8.4 Start Training

```
1. Navigate: Training → Train Model
2. Review stats:
   - Total samples: 1,234
   - Categories: 45
   - Balance score: 0.82 (Good)
3. Configure training:
   - Training set: 80%
   - Validation set: 20%
   - Epochs: [auto or manual]
   - Model version: v1.2.0
4. Click "Start Training"
5. Monitor progress:
   - Epoch 1/5: Loss 0.45
   - Epoch 2/5: Loss 0.32
   - ...
6. Wait for completion (30-60 minutes)
7. Review results:
   - Accuracy: 92.5%
   - F1 Score: 0.91
   - Confusion matrix
8. Click "Deploy New Model" or "Keep Current Model"
```

### 8.5 A/B Test Models

```
1. Navigate: Training → A/B Testing
2. Select models:
   - Model A: v1.1.0 (current)
   - Model B: v1.2.0 (new)
3. Configure split: 80% A / 20% B
4. Click "Start A/B Test"
5. Monitor metrics (24-48 hours):
   - Model A: 91% accuracy, 345ms avg
   - Model B: 93% accuracy, 350ms avg
6. Click "Promote Model B" if better
```

---

## 9. Monitoring

### 9.1 View Metrics Dashboard

```
Navigate: Monitoring → Metrics

Grafana dashboard embedded showing:
- Request rate (req/sec)
- Error rate (%)
- Response time (p50, p95, p99)
- Model metrics (accuracy, confidence distribution)
- System metrics (CPU, memory, disk)
```

### 9.2 View Logs

```
Navigate: Monitoring → Logs

Real-time log stream:
[2026-05-06 10:30:15] INFO: Classify request received
[2026-05-06 10:30:15] INFO: LLM understanding: confidence=0.92
[2026-05-06 10:30:16] INFO: Vector search: top_score=0.87
[2026-05-06 10:30:16] INFO: Decision: auto_assign
[2026-05-06 10:30:16] ERROR: Rate limit exceeded for key sk_live_...

Filters:
- Level: [All] [INFO] [WARNING] [ERROR]
- Service: [All] [API] [LLM] [Qdrant]
- Date Range: [Last 1h] [Last 24h] [Custom]
- Search: [Enter text]
```

### 9.3 View Alerts

```
Navigate: Monitoring → Alerts

┌──────────────────────────────────────────────────────────────┐
│ Active Alerts                                                │
├──────────────────────────────────────────────────────────────┤
│ 🔴 CRITICAL: High error rate (5.2% in last 5m)              │
│    Triggered: 2 minutes ago                                  │
│    [View Details] [Acknowledge] [Silence]                    │
│                                                              │
│ ⚠️ WARNING: Training data imbalance detected                 │
│    Triggered: 1 hour ago                                     │
│    [View Details] [Acknowledge]                              │
└──────────────────────────────────────────────────────────────┘
```

### 9.4 Configure Alerts

```
Navigate: Monitoring → Alert Rules

┌────────────────────────────────┬──────────┬──────────┐
│ Alert                          │ Threshold│ Status   │
├────────────────────────────────┼──────────┼──────────┤
│ High Error Rate                │ > 3%     │ 🟢 Enabled│
│ Slow Response Time             │ > 1s     │ 🟢 Enabled│
│ Low Disk Space                 │ < 10GB   │ 🟢 Enabled│
│ Service Down                   │ N/A      │ 🟢 Enabled│
│ Rate Limit Exceeded (frequent) │ > 10/min │ 🔴 Disabled│
└────────────────────────────────┴──────────┴──────────┘

[Add New Alert]
```

---

## 10. Data Management

### 10.1 Backup Categories

```
Navigate: Data → Export

1. Select data type: Categories
2. Select format: JSON
3. Click "Export"
4. File downloaded: categories_2026-05-06.json
```

### 10.2 Backup Training Data

```
1. Select data type: Training Data
2. Filter: [All] [Validated Only] [Since Date]
3. Select format: JSONL (recommended) or CSV
4. Click "Export"
5. File downloaded: training_data_2026-05-06.jsonl
```

### 10.3 Restore from Backup

⚠️ **WARNING:** This will overwrite current data!

```
1. Navigate: Data → Import
2. Select data type
3. Choose backup file
4. Click "Validate"
5. Review changes preview
6. Type "restore" to confirm
7. Click "Restore"
8. Wait for completion
9. Verify data integrity
```

### 10.4 Database Maintenance

```
Navigate: Data → Maintenance

┌──────────────────────────────────────────────────────┐
│ Database Statistics                                  │
├──────────────────────────────────────────────────────┤
│ Size: 2.3 GB                                         │
│ Categories: 450                                      │
│ Training Data: 12,345 rows                           │
│ Request Logs: 1.2M rows                              │
│ Last Vacuum: 2 days ago                              │
│                                                      │
│ Actions:                                             │
│ [Vacuum Database] - Reclaim space                    │
│ [Analyze Tables] - Update statistics                 │
│ [Archive Old Logs] - Move logs >90 days to archive  │
└──────────────────────────────────────────────────────┘
```

---

## 11. Troubleshooting

### 11.1 Common Issues

#### Issue: High Error Rate

**Symptoms:** Dashboard shows >3% errors

**Diagnosis:**
1. Check Monitoring → Logs for error patterns
2. Common causes:
   - LLM server overloaded
   - Qdrant connection issues
   - Invalid API requests

**Solutions:**
```
If LLM overload:
  → Increase timeout
  → Scale horizontally
  → Optimize prompts

If Qdrant issues:
  → Check Qdrant logs
  → Restart Qdrant service
  → Verify vector index intact

If invalid requests:
  → Check API client code
  → Validate request format
```

#### Issue: Slow Response Time

**Symptoms:** Average response time >1s

**Diagnosis:**
1. Check Monitoring → Metrics
2. Identify bottleneck:
   - LLM inference time
   - Embedding generation
   - Vector search time
   - Database queries

**Solutions:**
```
If LLM slow:
  → Use fast mode (skip understand)
  → Reduce max_tokens
  → Consider faster model

If embedding slow:
  → Batch requests
  → Cache common products
  → Use faster embedding model

If vector search slow:
  → Optimize Qdrant parameters
  → Reduce search results
  → Scale Qdrant
```

#### Issue: Classification Accuracy Drop

**Symptoms:** More manual_select decisions, user complaints

**Diagnosis:**
1. Check Training → Metrics
2. Review recent categories changes
3. Check for data drift

**Solutions:**
```
1. Review training data quality
2. Add more diverse samples
3. Retrain model with recent feedback
4. Adjust classification thresholds
5. Update category descriptions
```

### 11.2 Emergency Procedures

#### Procedure: System Down

```
1. Check System Control → Service Status
2. Identify failed services
3. Check logs for errors
4. Restart failed services
5. If persistent:
   → Check infrastructure (Docker, host OS)
   → Check disk space
   → Check memory availability
   → Restart all services
6. Monitor recovery
7. Post-incident review
```

#### Procedure: Data Corruption

```
1. Stop services immediately
2. Assess corruption extent:
   → Categories corrupted?
   → Training data corrupted?
   → Vector index corrupted?
3. Restore from last backup:
   → Data → Import → Restore
4. Rebuild vector index if needed
5. Verify data integrity
6. Resume services
7. Investigate root cause
```

#### Procedure: Security Breach

```
1. Revoke all API keys immediately
2. Change all admin passwords
3. Review access logs for suspicious activity
4. Export logs for forensic analysis
5. Patch security vulnerabilities
6. Generate new API keys
7. Notify affected users
8. Implement additional security measures
```

---

## 12. Security

### 12.1 Security Best Practices

✅ **DO:**
- Change default passwords immediately
- Use strong passwords (12+ chars, mixed)
- Enable 2FA (when available)
- Rotate API keys regularly (every 90 days)
- Review user access regularly
- Monitor suspicious activity
- Keep backups encrypted
- Use HTTPS only
- Update system regularly

❌ **DON'T:**
- Share admin credentials
- Expose API keys publicly
- Disable security features
- Ignore security alerts
- Use weak passwords
- Leave inactive users active

### 12.2 Access Control

**Principle of Least Privilege:**
- Give users minimum required permissions
- Use Viewer role for read-only access
- Reserve Admin role for trusted personnel
- Review and adjust roles quarterly

### 12.3 Audit Logs

```
Navigate: Monitoring → Audit Logs

View who did what:
[2026-05-06 10:30] admin created user "john_dev"
[2026-05-06 11:45] john_dev generated API key "Prod API"
[2026-05-06 14:20] admin modified configuration
[2026-05-06 15:30] admin started training job
```

**Audit log retention:** 1 year

### 12.4 Compliance

**Data Privacy:**
- Request logs contain user data → comply with GDPR/local laws
- Implement data retention policies
- Provide data export/deletion tools
- Document data processing activities

**Security Standards:**
- Regular security audits
- Penetration testing (annual)
- Vulnerability scanning (monthly)
- Incident response plan

---

## 📞 Support

### Getting Help

**Documentation:**
- This manual (you're reading it!)
- [Integration Guide](./INTEGRATION_GUIDE.md) - For developers
- [Data Standards](./DATA_STANDARDS.md) - For data management

**Technical Support:**
- Email: admin@localhost
- Discord: https://discord.gg/autocategory
- GitHub Issues: https://github.com/autocategory/issues

**Emergency Contact:**
- On-call engineer: +84 xxx xxx xxx
- Email: admin@localhost

---

## 📝 Checklist

### Daily Tasks
- [ ] Check dashboard overview
- [ ] Review alerts
- [ ] Monitor error rate
- [ ] Check API key usage

### Weekly Tasks
- [ ] Review new training data
- [ ] Check system performance trends
- [ ] Review user activity logs
- [ ] Backup categories & training data

### Monthly Tasks
- [ ] Rotate API keys (if policy)
- [ ] Review user access levels
- [ ] Database maintenance (vacuum, analyze)
- [ ] Review and adjust alert thresholds
- [ ] Update documentation if needed

### Quarterly Tasks
- [ ] Full system audit
- [ ] Retrain models with accumulated feedback
- [ ] Review security posture
- [ ] Plan capacity upgrades
- [ ] Review and update disaster recovery plan

---

**Version History:**
- v1.0.0 (2026-05-06) - Initial release
