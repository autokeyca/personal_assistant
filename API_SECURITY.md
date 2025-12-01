# Jarvis API Security Protocol

Comprehensive security measures to ensure only authorized AI agents and workflows can access Jarvis.

## Security Layers

### Layer 1: Network Isolation ✅

**Localhost Binding**
- API server binds to `127.0.0.1` (localhost only)
- Not accessible from external networks
- Only processes on the same machine can connect

**Configuration:**
```yaml
api:
  host: "127.0.0.1"  # Never change to 0.0.0.0 unless behind reverse proxy
  port: 8000
```

### Layer 2: API Key Authentication ✅

**How It Works:**
- All endpoints (except /health and /) require valid API key
- Keys are SHA-256 hashed before storage
- Keys shown only once during creation
- Usage tracking (last_used, usage_count)

**Key Management:**
```bash
# Create key with all permissions
python scripts/manage_api_keys.py create "agent-name"

# Create key with limited permissions
python scripts/manage_api_keys.py create "monitoring-bot" \
  --permissions "message:send,task:create"

# Deactivate compromised key
python scripts/manage_api_keys.py deactivate <id>

# List all keys with usage stats
python scripts/manage_api_keys.py list
```

**Best Practices:**
- ✅ Create separate keys for each agent/workflow
- ✅ Use descriptive names
- ✅ Set minimum required permissions
- ✅ Rotate keys periodically (every 90 days recommended)
- ✅ Deactivate unused keys immediately
- ❌ Never share keys between agents
- ❌ Never commit keys to git
- ❌ Never log keys in plaintext

### Layer 3: IP Whitelisting ✅

**Purpose:** Restrict API access to specific IP addresses

**Configuration:**
```yaml
api:
  allowed_ips:
    - "192.168.1.100"  # n8n server
    - "10.0.0.50"      # Make.com runner
    - "172.17.0.1"     # Docker container
```

**How to Find IPs:**

**Local machine agents:**
```bash
# Your machine's local IP
ip addr show | grep "inet " | grep -v 127.0.0.1
```

**Docker containers:**
```bash
# Get container IP
docker inspect <container_name> | grep IPAddress
```

**n8n/Make.com:**
- If self-hosted: Use server's internal IP
- If cloud: Contact support for webhook IP ranges

**When to Use:**
- ✅ Running agents on specific machines
- ✅ Docker-based automation
- ✅ Self-hosted n8n/Make.com
- ❌ Cloud services (IPs change frequently)

### Layer 4: Rate Limiting ✅

**Configuration:**
```yaml
api:
  rate_limit_per_minute: 60  # Adjust based on needs
```

**Limits:**
- 60 requests per minute per client (default)
- Separate counters for each IP + API key combination
- 429 status code when exceeded
- Headers included: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

**Adjust for Your Use Case:**
- Low-frequency monitoring: 10-30/min
- Medium automation: 60/min (default)
- High-volume tasks: 120-300/min

### Layer 5: Security Headers ✅

**Automatically Applied:**
- `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Strict-Transport-Security` - Force HTTPS (when applicable)
- `Content-Security-Policy` - Restrict resource loading

### Layer 6: Permission System ✅

**Available Permissions:**
- `*` - All permissions (use cautiously)
- `message:send` - Send messages to users
- `task:create` - Create tasks
- `task:read` - List and view tasks
- `reminder:create` - Create reminders
- `status:read` - View Jarvis status

**Example Use Cases:**

**Monitoring Agent (read-only + alerts):**
```bash
python scripts/manage_api_keys.py create "monitoring" \
  --permissions "message:send,status:read"
```

**Task Automation (create only):**
```bash
python scripts/manage_api_keys.py create "task-creator" \
  --permissions "task:create"
```

**Full Access Agent:**
```bash
python scripts/manage_api_keys.py create "main-agent" \
  --permissions "*"
```

## Firewall Rules (Optional)

**If API needs to be accessible from other machines on your network:**

### UFW (Ubuntu Firewall)

```bash
# Allow specific IP to access API
sudo ufw allow from 192.168.1.100 to any port 8000

# Deny all other access to port 8000
sudo ufw deny 8000

# Check rules
sudo ufw status
```

### iptables

```bash
# Allow specific IP
sudo iptables -A INPUT -p tcp -s 192.168.1.100 --dport 8000 -j ACCEPT

# Drop all other connections to port 8000
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

## SSH Tunneling for Remote Access

**If you need to access the API from a remote machine securely:**

```bash
# From remote machine, create SSH tunnel
ssh -L 8000:localhost:8000 ja@your-server-ip

# Now access API on remote machine via localhost:8000
curl -H "X-API-Key: your-key" http://localhost:8000/status
```

**Advantages:**
- ✅ Encrypted connection
- ✅ No need to expose API to network
- ✅ Uses existing SSH authentication

## Reverse Proxy Setup (Production)

**For production deployments, use nginx as reverse proxy:**

### 1. Install nginx with SSL

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

### 2. Configure nginx

`/etc/nginx/sites-available/jarvis-api`:
```nginx
server {
    listen 443 ssl;
    server_name jarvis-api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # IP whitelist
    allow 192.168.1.100;
    deny all;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 3. Enable and restart

```bash
sudo ln -s /etc/nginx/sites-available/jarvis-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Monitoring & Alerts

### Log API Access

API logs are in:
- Access: `/home/ja/projects/personal_assistant/logs/api.log`
- Errors: `/home/ja/projects/personal_assistant/logs/api_error.log`

### Monitor for Suspicious Activity

```bash
# Watch failed auth attempts
grep "401 UNAUTHORIZED" logs/api.log | tail -20

# Watch rate limit violations
grep "429 TOO_MANY_REQUESTS" logs/api.log | tail -20

# Watch blocked IPs
grep "Access denied for IP" logs/api.log | tail -20
```

### Set Up Alerts

Create monitoring script `scripts/monitor_api_security.sh`:
```bash
#!/bin/bash
LOG_FILE="logs/api.log"
THRESHOLD=5

# Count failed auth in last hour
failed_auth=$(grep "401 UNAUTHORIZED" $LOG_FILE | tail -100 | wc -l)

if [ $failed_auth -gt $THRESHOLD ]; then
    # Send alert via API
    curl -H "X-API-Key: your-monitoring-key" \
         -H "Content-Type: application/json" \
         http://127.0.0.1:8000/message \
         -d "{\"message\": \"⚠️ API Security Alert: $failed_auth failed auth attempts detected\"}"
fi
```

Run every hour:
```bash
crontab -e
# Add:
0 * * * * /home/ja/projects/personal_assistant/scripts/monitor_api_security.sh
```

## Security Checklist

### Initial Setup
- [x] API binds to localhost only
- [x] API keys created with minimal permissions
- [x] Rate limiting configured
- [x] Security headers enabled
- [ ] IP whitelist configured (if needed)
- [ ] Firewall rules set (if needed)
- [ ] Monitoring alerts configured

### Regular Maintenance
- [ ] Rotate API keys every 90 days
- [ ] Review API key usage monthly
- [ ] Check logs for suspicious activity weekly
- [ ] Update allowed IPs when infrastructure changes
- [ ] Deactivate keys for deprecated agents

### When Adding New Agent
1. Determine minimum required permissions
2. Create key with specific permissions
3. Add agent's IP to whitelist (if using)
4. Document agent name and purpose
5. Test with limited scope first
6. Monitor usage for first week

### If Key is Compromised
1. Immediately deactivate key: `python scripts/manage_api_keys.py deactivate <id>`
2. Check logs for unauthorized usage
3. Create new key with different credentials
4. Update agent with new key
5. Delete old key: `python scripts/manage_api_keys.py delete <id>`

## Security Scenarios

### Scenario 1: n8n Automation on Same Machine

**Setup:**
```yaml
api:
  host: "127.0.0.1"
  allowed_ips: []  # No whitelist needed
```

**Security:**
- n8n runs on same machine
- Uses localhost (already secure)
- API key authentication sufficient

**n8n HTTP Node:**
- URL: `http://127.0.0.1:8000/message`
- Header: `X-API-Key: your-key-here`

### Scenario 2: Docker Container Agent

**Setup:**
```yaml
api:
  host: "0.0.0.0"  # Accessible to Docker network
  allowed_ips:
    - "172.17.0.0/16"  # Docker network range
```

**Security:**
- IP whitelist to Docker network
- Container uses API key
- Rate limiting applies

### Scenario 3: Remote Cloud Service

**Setup:**
Use SSH tunnel (recommended) or reverse proxy with SSL

**SSH Tunnel:**
```bash
# On your machine
ssh -L 8000:localhost:8000 ja@server-ip

# Cloud service uses localhost:8000
```

**Security:**
- API stays on localhost
- SSH provides encryption
- No firewall changes needed

### Scenario 4: Multiple Local Agents

**Setup:**
Create separate key for each:
```bash
python scripts/manage_api_keys.py create "monitoring-agent"
python scripts/manage_api_keys.py create "task-automation"
python scripts/manage_api_keys.py create "notification-system"
```

**Security:**
- Each agent has unique key
- Can revoke one without affecting others
- Track usage per agent
- Set different permissions per agent

## Additional Security Measures

### 1. Environment Variables for Keys

Never hardcode keys. Use environment variables:

```bash
# .env file (never commit!)
JARVIS_API_KEY=your-key-here
```

```python
import os
api_key = os.getenv("JARVIS_API_KEY")
```

### 2. Secrets Management

For production, use proper secrets management:
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- 1Password CLI

### 3. HTTPS Only (Production)

If exposing API beyond localhost:
- Always use HTTPS
- Never use plain HTTP with sensitive data
- Use Let's Encrypt for free SSL certificates

### 4. Audit Trail

All API access is logged with:
- Timestamp
- API key (last 10 chars)
- IP address
- Endpoint accessed
- Success/failure

Review logs regularly:
```bash
tail -f logs/api.log
```

## Quick Reference

**Common Commands:**
```bash
# Start API service
sudo systemctl start jarvis-api

# Check API status
sudo systemctl status jarvis-api

# View API logs
sudo journalctl -u jarvis-api -f

# Create API key
python scripts/manage_api_keys.py create "agent-name"

# List all keys
python scripts/manage_api_keys.py list

# Test API
curl -H "X-API-Key: your-key" http://127.0.0.1:8000/health
```

**Security Levels:**
- **Level 1 (Minimal):** Localhost + API key
- **Level 2 (Standard):** Level 1 + Rate limiting + IP whitelist
- **Level 3 (High):** Level 2 + Firewall rules + Monitoring
- **Level 4 (Maximum):** Level 3 + HTTPS + SSH tunnel + Secrets manager
