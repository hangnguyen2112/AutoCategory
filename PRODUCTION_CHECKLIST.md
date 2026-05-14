# Production Deployment Checklist

Complete this checklist before deploying to production.

---

## Pre-Deployment

### Code Quality
- [ ] All tests passing (run `./scripts/run_tests.sh`)
- [ ] Test coverage >80%
- [ ] No console.log or debug statements in production code
- [ ] Code reviewed and approved by team
- [ ] All linting errors resolved
- [ ] Documentation updated

### Configuration
- [ ] `.env` file configured with production values
- [ ] `SECRET_KEY` changed from default
- [ ] `DATABASE_URL` pointing to production database
- [ ] `REDIS_PASSWORD` set to strong password
- [ ] `CORS_ORIGINS` set to production domains only
- [ ] `DEBUG=false` in production
- [ ] Email/alert configuration tested

### Security
- [ ] All default passwords changed
- [ ] Admin user password changed from `admin123`
- [ ] API rate limits configured appropriately
- [ ] JWT secret key rotated
- [ ] SSL/TLS certificates obtained
- [ ] Firewall rules configured
- [ ] Security audit passed
- [ ] SQL injection tests passed
- [ ] XSS protection verified

### Database
- [ ] Database backup strategy implemented
- [ ] Migration scripts tested
- [ ] Database indexes created
- [ ] Connection pooling configured
- [ ] Backup restoration tested

### Infrastructure
- [ ] Server provisioned and configured
- [ ] Docker installed and configured
- [ ] Docker Compose installed
- [ ] Sufficient disk space (minimum 50GB free)
- [ ] Domain name configured
- [ ] DNS records updated
- [ ] Load balancer configured (if applicable)

---

## Deployment Steps

### 1. Server Setup
- [ ] SSH access configured
- [ ] Non-root user created
- [ ] Firewall enabled (UFW or iptables)
- [ ] Fail2Ban installed and configured
- [ ] Docker daemon running

### 2. Application Deployment
- [ ] Code cloned to server
- [ ] Environment variables set
- [ ] Docker images built
- [ ] Docker Compose started
- [ ] All services healthy

### 3. Database Initialization
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Admin user created (`python scripts/init_admin.py`)
- [ ] Categories imported (`python scripts/import_categories.py`)
- [ ] Sample data imported (if needed)

### 4. SSL/TLS Configuration
- [ ] SSL certificates obtained (Let's Encrypt or manual)
- [ ] Nginx configured with SSL
- [ ] HTTP to HTTPS redirect enabled
- [ ] SSL certificate auto-renewal configured

### 5. Monitoring Setup
- [ ] Prometheus deployed and running
- [ ] Grafana deployed and configured
- [ ] Alertmanager configured
- [ ] Alert notifications tested (Slack/email)
- [ ] Dashboards imported

### 6. Backup Configuration
- [ ] Automated backup script configured
- [ ] Backup schedule set (cron job)
- [ ] Backup restoration tested
- [ ] Offsite backup configured

---

## Post-Deployment Validation

### Health Checks
- [ ] API health endpoint responding (`/health`)
- [ ] All services showing as healthy in dashboard
- [ ] Database connection working
- [ ] Redis cache working
- [ ] Qdrant vector search working
- [ ] LLM service responding

### Functional Tests
- [ ] User login working
- [ ] Classification API working
- [ ] API key creation and usage working
- [ ] Category management working
- [ ] Training data management working
- [ ] Admin dashboard accessible

### Performance Tests
- [ ] Response times acceptable (<1s for 95th percentile)
- [ ] Can handle expected load (run load tests)
- [ ] No memory leaks detected
- [ ] CPU usage reasonable
- [ ] Database query performance acceptable

### Monitoring Verification
- [ ] Metrics being collected
- [ ] Grafana dashboards showing data
- [ ] Alerts configured and working
- [ ] Logs being collected
- [ ] Error tracking working

### Security Verification
- [ ] HTTPS enforced (no HTTP access)
- [ ] Firewall rules working
- [ ] Rate limiting working
- [ ] API keys properly secured
- [ ] No sensitive data exposed in logs
- [ ] Password hashing working

---

## Launch Checklist

### Pre-Launch
- [ ] Announcement prepared
- [ ] Documentation published
- [ ] Support team trained
- [ ] Incident response plan ready
- [ ] Rollback plan documented
- [ ] Status page configured

### Launch
- [ ] DNS cutover executed
- [ ] Service started
- [ ] Initial smoke tests passed
- [ ] Monitoring active
- [ ] Team on standby

### Post-Launch (First 24 Hours)
- [ ] Monitor error rates
- [ ] Monitor response times
- [ ] Check resource usage
- [ ] Verify user feedback
- [ ] Address any critical issues
- [ ] Document lessons learned

---

## Rollback Plan

If issues are encountered:

1. **Stop new traffic**
   ```bash
   # Redirect traffic back to old system
   # Or put up maintenance page
   ```

2. **Assess the issue**
   - Check logs
   - Check metrics
   - Identify root cause

3. **Execute rollback**
   ```bash
   cd /opt/autocategory
   git checkout <previous-version>
   docker-compose -f docker-compose.prod.yml down
   # Restore database backup
   gunzip < /backups/db_YYYYMMDD.sql.gz | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U autocategory_user autocategory
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify rollback**
   - Test functionality
   - Check metrics
   - Verify data integrity

5. **Post-incident**
   - Document what happened
   - Update runbook
   - Plan fixes

---

## Monitoring Checklist

### Metrics to Watch
- [ ] Request rate (requests/second)
- [ ] Error rate (%)
- [ ] Response time (p95, p99)
- [ ] Classification confidence
- [ ] Database connections
- [ ] Cache hit rate
- [ ] Memory usage
- [ ] CPU usage
- [ ] Disk usage

### Alerts to Configure
- [ ] Service down
- [ ] High error rate (>5%)
- [ ] Slow response time (>3s)
- [ ] Low classification confidence (<0.5)
- [ ] High memory usage (>90%)
- [ ] High disk usage (>90%)
- [ ] Database connection pool exhausted
- [ ] Redis memory high
- [ ] SSL certificate expiring soon

---

## Support Checklist

### Documentation
- [ ] API documentation published
- [ ] Integration guide available
- [ ] Admin manual accessible
- [ ] Troubleshooting guide ready
- [ ] FAQ created

### Team Preparedness
- [ ] On-call schedule defined
- [ ] Escalation path documented
- [ ] Team trained on system
- [ ] Access credentials distributed
- [ ] Communication channels set up

---

## Sign-Off

**Technical Lead:** _________________ Date: _________

**DevOps Lead:** _________________ Date: _________

**QA Lead:** _________________ Date: _________

**Product Owner:** _________________ Date: _________

---

## Production URL

- **Admin Dashboard:** https://admin.yourcompany.com
- **API Base URL:** https://api.yourcompany.com
- **Monitoring:** https://monitoring.yourcompany.com
- **Status Page:** https://status.yourcompany.com

---

## Emergency Contacts

- **On-Call Engineer:** +84 xxx xxx xxxx
- **DevOps Team:** devops@yourcompany.com
- **Support Team:** support@yourcompany.com
- **Incident Manager:** incidents@yourcompany.com
