# Deployment Guide

## Server Setup

### 1. Prepare the Server

```bash
# SSH into your server
ssh admin@your-server.local

# Create application directory
sudo mkdir -p /opt/flask-munkireport
sudo chown $USER:$USER /opt/flask-munkireport

# Install Python 3.10+ if needed
# (Most macOS/Linux systems have this)
python3 --version
```

### 2. Transfer Application Code

**Option A: Git (Recommended)**
```bash
cd /opt/flask-munkireport
git clone https://github.com/yourusername/flask-munkireport.git .
```

**Option B: SCP**
```bash
# From your Mac
cd /Users/admin/Documents/GitHub_James/flask-munkireport
rsync -av --exclude '.git' --exclude '*.pyc' --exclude '__pycache__' \
  . admin@your-server.local:/opt/flask-munkireport/
```

### 3. Install Dependencies

```bash
cd /opt/flask-munkireport

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Generate secure API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit .env with your settings
nano .env
```

**Important settings:**
```env
DATABASE_PATH=/Volumes/Macintosh HD-1/Users/Shared/munkireport-php/app/db/claude.db.sqlite
API_KEY=your-generated-key-here
FLASK_ENV=production
SECRET_KEY=another-random-key
```

### 5. Test the Application

```bash
# Activate venv
source venv/bin/activate

# Test with development server
python run.py
```

In another terminal:
```bash
# Test health endpoint
curl http://localhost:5000/api/v1/health

# Test authenticated endpoint
curl -H "X-API-Key: your-key" http://localhost:5000/api/v1/tools/get_database_stats
```

### 6. Production Deployment (systemd)

Create systemd service file:

```bash
sudo nano /etc/systemd/system/munkireport-api.service
```

Content:
```ini
[Unit]
Description=Flask MunkiReport API
After=network.target

[Service]
User=admin
Group=admin
WorkingDirectory=/opt/flask-munkireport
Environment="PATH=/opt/flask-munkireport/venv/bin"
EnvironmentFile=/opt/flask-munkireport/.env
ExecStart=/opt/flask-munkireport/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 60 \
    --access-logfile /var/log/munkireport-api/access.log \
    --error-logfile /var/log/munkireport-api/error.log \
    wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create log directory:
```bash
sudo mkdir -p /var/log/munkireport-api
sudo chown admin:admin /var/log/munkireport-api
```

Enable and start service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable munkireport-api

# Start service
sudo systemctl start munkireport-api

# Check status
sudo systemctl status munkireport-api

# View logs
sudo journalctl -u munkireport-api -f
```

### 7. Firewall Configuration (Optional)

If you want to restrict access to specific IPs:

```bash
# Allow from specific IP
sudo iptables -A INPUT -p tcp -s 192.168.1.100 --dport 5000 -j ACCEPT

# Block all other IPs
sudo iptables -A INPUT -p tcp --dport 5000 -j DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

### 8. Using MCP Client from Your Mac

Update your Claude Desktop config or create a new MCP client:

**Claude Desktop Config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "munkireport-api": {
      "command": "python",
      "args": [
        "/path/to/your/mcp-http-client.py",
        "http://your-server.local:5000",
        "your-api-key"
      ]
    }
  }
}
```

You'll need to create a simple MCP wrapper that calls the HTTP API (or use the SSH approach for simplicity).

## Monitoring

### Check Service Status
```bash
sudo systemctl status munkireport-api
```

### View Logs
```bash
# Application logs
sudo journalctl -u munkireport-api -f

# Access logs
tail -f /var/log/munkireport-api/access.log

# Error logs
tail -f /var/log/munkireport-api/error.log
```

### Test Endpoints
```bash
# Health check
curl http://localhost:5000/api/v1/health

# Status (includes DB connectivity)
curl http://localhost:5000/api/v1/status

# Database stats (requires auth)
curl -H "X-API-Key: your-key" \
  http://localhost:5000/api/v1/tools/get_database_stats
```

## Maintenance

### Update Application
```bash
# Stop service
sudo systemctl stop munkireport-api

# Update code
cd /opt/flask-munkireport
git pull  # or rsync from your Mac

# Update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl start munkireport-api
```

### Restart Service
```bash
sudo systemctl restart munkireport-api
```

### View Service Logs
```bash
sudo journalctl -u munkireport-api -n 100
```

## Troubleshooting

### Database Permission Issues
```bash
# Check database file permissions
ls -la "/Volumes/Macintosh HD-1/Users/Shared/munkireport-php/app/db/claude.db.sqlite"

# Make readable by service user
sudo chmod 644 "/Volumes/Macintosh HD-1/Users/Shared/munkireport-php/app/db/claude.db.sqlite"
```

### Port Already in Use
```bash
# Check what's using port 5000
lsof -i :5000

# Kill process or change port in .env
```

### Service Won't Start
```bash
# Check systemd logs
sudo journalctl -u munkireport-api -n 50

# Test manually
cd /opt/flask-munkireport
source venv/bin/activate
python run.py
```

## Security Checklist

- [ ] Strong API key generated (32+ characters)
- [ ] `.env` file permissions set to 600 (`chmod 600 .env`)
- [ ] Firewall configured to restrict access
- [ ] HTTPS enabled (if exposed to internet)
- [ ] Regular log monitoring enabled
- [ ] Database is in read-only mode
- [ ] Service running as non-root user

## Performance Tuning

### Adjust Worker Count
Edit systemd service file and change `--workers` based on CPU cores:
```
--workers 4  # Typically 2-4 x CPU cores
```

### Increase Timeout for Slow Queries
```
--timeout 120  # Increase if queries take longer
```

### Enable Access Log Rotation
```bash
sudo nano /etc/logrotate.d/munkireport-api
```

Content:
```
/var/log/munkireport-api/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 admin admin
    sharedscripts
    postrotate
        systemctl reload munkireport-api > /dev/null 2>&1 || true
    endscript
}
```
