# Flask MunkiReport API

Read-only HTTP API for querying MunkiReport SQLite databases.

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run development server:**
```bash
python run.py
```

4. **Run production server:**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

## API Endpoints

All endpoints except `/health` and `/status` require authentication via `X-API-Key` header.

### Public Endpoints

**GET /api/v1/health**
- Health check endpoint
- Returns: `{"success": true, "status": "healthy"}`

**GET /api/v1/status**
- Detailed status including database connectivity
- Returns: Status object with database info

### Machine Endpoints

**POST /api/v1/tools/query_machines**
- Query machines with flexible filters
- Body:
  ```json
  {
    "filters": {
      "mdm_enrolled": "No",
      "manifest": "Pablo"
    },
    "include": ["reportdata", "mdm_status"],
    "order_by": "hostname",
    "limit": 100
  }
  ```

**GET /api/v1/tools/get_machine_details/{serial_number}**
- Get complete details for specific machine
- Returns: Machine object with all related data

**GET /api/v1/tools/get_mdm_enrollment_summary**
- Get MDM enrollment statistics
- Returns: Summary object with enrollment breakdown

### Event Endpoints

**POST /api/v1/tools/get_events**
- Query events with filters
- Body:
  ```json
  {
    "filters": {
      "type": ["error", "danger"],
      "timestamp_after": 1234567890
    },
    "include_machine": true,
    "limit": 50
  }
  ```

**GET /api/v1/tools/get_error_summary**
- Get error/warning summary by machine
- Returns: Summary with counts per machine

**GET /api/v1/tools/get_recent_critical_events?hours=24&limit=50**
- Get recent critical events
- Query params: `hours` (default: 24), `limit` (default: 50)

### Database Endpoints

**GET /api/v1/tools/get_database_stats**
- Get database statistics
- Returns: Database info including size and table counts

**POST /api/v1/tools/get_table_summary**
- Get aggregated statistics for any table
- Body:
  ```json
  {
    "table_name": "machine",
    "group_by": "machine_model",
    "filters": {}
  }
  ```

## Authentication

All authenticated endpoints require the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:5000/api/v1/tools/get_database_stats
```

## Example Requests

**Query machines without MDM:**
```bash
curl -X POST \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"filters": {"mdm_enrolled": "No"}, "limit": 10}' \
  http://localhost:5000/api/v1/tools/query_machines
```

**Get machine details:**
```bash
curl -H "X-API-Key: your-key" \
  http://localhost:5000/api/v1/tools/get_machine_details/C02ABC123DEF
```

**Get recent errors:**
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:5000/api/v1/tools/get_recent_critical_events?hours=24&limit=20"
```

## Production Deployment

### Using Gunicorn (Recommended)

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

# Run with logging
gunicorn -w 4 -b 0.0.0.0:5000 \
  --access-logfile - \
  --error-logfile - \
  wsgi:app
```

### Using systemd

Create `/etc/systemd/system/munkireport-api.service`:

```ini
[Unit]
Description=Flask MunkiReport API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/flask-munkireport
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable munkireport-api
sudo systemctl start munkireport-api
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.munkireport.local;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Security Notes

1. **API Key Storage**: Store API keys in environment variables, never commit to git
2. **HTTPS**: Use HTTPS in production (nginx + Let's Encrypt)
3. **Firewall**: Restrict access to trusted IPs if possible
4. **Read-Only**: Database is opened in read-only mode (`PRAGMA query_only`)
5. **SQL Injection**: All queries use parameterized statements

## Response Format

All endpoints return JSON with consistent structure:

**Success:**
```json
{
  "success": true,
  "data": {...},
  "count": 10  // For list endpoints
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error type",
  "message": "Detailed error message"
}
```

## Development

```bash
# Run in development mode
FLASK_ENV=development python run.py

# Test endpoints
python tests/test_api.py
```
