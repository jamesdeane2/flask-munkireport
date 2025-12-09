# Quick Reference

## Local Development

```bash
# Setup
cp .env.example .env
# Edit .env with your settings
pip install -r requirements.txt

# Run dev server
python run.py

# Test API
python tests/test_api.py http://localhost:5000 your-api-key
```

## Production Deployment

```bash
# On server
cd /opt/flask-munkireport
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

# With systemd
sudo systemctl start munkireport-api
sudo systemctl status munkireport-api
sudo journalctl -u munkireport-api -f
```

## Common API Calls

```bash
# Set your API key
export API_KEY="your-api-key-here"
export BASE_URL="http://your-server:5000"

# Health check (no auth)
curl $BASE_URL/api/v1/health

# Database stats
curl -H "X-API-Key: $API_KEY" \
  $BASE_URL/api/v1/tools/get_database_stats

# Query machines without MDM
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filters": {"mdm_enrolled": "No"}, "limit": 10}' \
  $BASE_URL/api/v1/tools/query_machines

# Get machine details
curl -H "X-API-Key: $API_KEY" \
  $BASE_URL/api/v1/tools/get_machine_details/SERIAL123

# Recent critical events
curl -H "X-API-Key: $API_KEY" \
  "$BASE_URL/api/v1/tools/get_recent_critical_events?hours=24&limit=20"

# Query events
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filters": {"type": ["error", "danger"]}, "limit": 10}' \
  $BASE_URL/api/v1/tools/get_events
```

## Python Client Example

```python
import requests

class MunkiReportClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def query_machines(self, filters=None, limit=100):
        resp = requests.post(
            f"{self.base_url}/api/v1/tools/query_machines",
            json={"filters": filters, "limit": limit},
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()["data"]
    
    def get_machine_details(self, serial):
        resp = requests.get(
            f"{self.base_url}/api/v1/tools/get_machine_details/{serial}",
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()["data"]

# Usage
client = MunkiReportClient("http://localhost:5000", "your-api-key")
machines = client.query_machines(filters={"mdm_enrolled": "No"})
print(f"Found {len(machines)} machines")
```

## Troubleshooting

```bash
# Check if service is running
sudo systemctl status munkireport-api

# View logs
sudo journalctl -u munkireport-api -n 100

# Test database access
python3 << EOF
from src.flask_munkireport.database import MunkiReportDB
db = MunkiReportDB("/path/to/db.sqlite")
print(f"Tables: {len(db.list_tables())}")
EOF

# Test manually
cd /opt/flask-munkireport
source venv/bin/activate
python run.py

# Check port
lsof -i :5000
```

## File Locations

```
Application:    /opt/flask-munkireport/
Config:         /opt/flask-munkireport/.env
Service:        /etc/systemd/system/munkireport-api.service
Logs:           /var/log/munkireport-api/
Database:       /Volumes/Macintosh HD-1/Users/Shared/munkireport-php/app/db/claude.db.sqlite
```

## Key Files

```
config.py           - Configuration management
wsgi.py             - Production entry point
run.py              - Development server
.env                - Environment variables (create from .env.example)
requirements.txt    - Python dependencies
```

## Environment Variables

```
DATABASE_PATH       - Path to SQLite database
API_KEY            - API authentication key
FLASK_ENV          - development or production
FLASK_HOST         - Bind address (0.0.0.0 for all interfaces)
FLASK_PORT         - Port number (default: 5000)
SECRET_KEY         - Flask secret key
LOG_LEVEL          - Logging level (INFO, DEBUG, ERROR)
```
