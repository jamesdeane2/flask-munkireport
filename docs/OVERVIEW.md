# Flask MunkiReport - Project Overview

## What Was Built

A production-ready Flask HTTP API that exposes your MunkiReport SQLite database for remote querying. This solves your VPN/mount/copy workflow by allowing direct queries over HTTP.

## Project Structure

```
flask-munkireport/
├── src/flask_munkireport/
│   ├── __init__.py
│   ├── app.py                    # Flask application factory
│   ├── auth.py                   # API key authentication
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py         # Database connection (read-only)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py             # Health/status endpoints
│   │   └── tools.py              # Main query endpoints
│   └── utils/
│       ├── __init__.py
│       ├── filters.py            # SQL query builders
│       ├── machines.py           # Machine query logic
│       ├── events.py             # Event query logic
│       └── queries.py            # General query logic
├── tests/
│   └── test_api.py               # API test suite
├── docs/
│   └── DEPLOYMENT.md             # Deployment guide
├── .env.example                  # Example environment config
├── config.py                     # Configuration management
├── requirements.txt              # Dependencies
├── run.py                        # Development server
├── wsgi.py                       # Production entry point
└── README.md                     # API documentation
```

## Key Features

### Security
- ✅ API key authentication (`X-API-Key` header)
- ✅ Database opened in read-only mode (`PRAGMA query_only`)
- ✅ Parameterized SQL queries (injection protection)
- ✅ Environment-based configuration
- ✅ No secrets in code

### Database Access
- ✅ Read-only SQLite connection
- ✅ Connection pooling via Flask's `g` object
- ✅ Automatic connection cleanup
- ✅ Timeout handling (30s default)
- ✅ Thread-safe mode disabled for performance

### API Design
- ✅ RESTful endpoints with consistent JSON responses
- ✅ Success/error response structure
- ✅ Health check endpoint (no auth required)
- ✅ Status endpoint with DB connectivity check
- ✅ Versioned API (`/api/v1/`)

### Query Features
- ✅ All MCP server tools exposed as HTTP endpoints
- ✅ Machine queries with filters and joins
- ✅ Event queries with machine details
- ✅ MDM enrollment summaries
- ✅ Database statistics
- ✅ Table aggregations

## API Endpoints Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/health` | GET | No | Health check |
| `/api/v1/status` | GET | No | Detailed status |
| `/api/v1/tools/query_machines` | POST | Yes | Query machines |
| `/api/v1/tools/get_machine_details/{serial}` | GET | Yes | Get machine details |
| `/api/v1/tools/get_mdm_enrollment_summary` | GET | Yes | MDM summary |
| `/api/v1/tools/get_events` | POST | Yes | Query events |
| `/api/v1/tools/get_error_summary` | GET | Yes | Error summary |
| `/api/v1/tools/get_recent_critical_events` | GET | Yes | Recent critical events |
| `/api/v1/tools/get_database_stats` | GET | Yes | Database stats |
| `/api/v1/tools/get_table_summary` | POST | Yes | Table aggregations |

## Quick Start

### Local Testing (On Your Mac)

1. **Install dependencies:**
   ```bash
   cd /Users/admin/Documents/GitHub_James/flask-munkireport
   pip install -r requirements.txt
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit DATABASE_PATH and API_KEY
   ```

3. **Run development server:**
   ```bash
   python run.py
   ```

4. **Test endpoints:**
   ```bash
   # Health check (no auth)
   curl http://localhost:5000/api/v1/health
   
   # Database stats (requires auth)
   curl -H "X-API-Key: your-key" \
     http://localhost:5000/api/v1/tools/get_database_stats
   ```

### Production Deployment (On Server)

See `docs/DEPLOYMENT.md` for complete instructions.

**TL;DR:**
1. Copy code to server: `/opt/flask-munkireport`
2. Create virtualenv and install deps
3. Configure `.env` with production settings
4. Set up systemd service
5. Start service: `sudo systemctl start munkireport-api`

## Architecture Decisions

### Why Flask?
- Lightweight and simple for read-only API
- Easy to deploy with gunicorn
- You've built Flask apps before (familiar)
- No need for Django's ORM/admin (read-only database)

### Why Vendor MCP Code?
- MCP server and Flask server on different machines
- Can't use relative imports across repos
- Vendored code = single deployable unit
- Easier to maintain versions independently

### Why API Keys Instead of OAuth?
- Simple use case (you're the only client)
- No user accounts needed
- Easy to rotate keys
- Lower complexity = fewer bugs

### Why systemd Instead of Docker?
- macOS server (your deployment target)
- systemd is built-in and reliable
- No Docker overhead
- Easier log management with journalctl

## How It Solves Your Problem

**Before (Current Workflow):**
```
Your Mac → VPN → SSH to server → Offline server → 
Copy DB → Mount share → Update MCP config → Query
```

**After (With Flask API):**
```
Your Mac → HTTP request → Server → Response
```

**Benefits:**
1. No VPN required (or works through VPN automatically)
2. No server downtime for DB copies
3. No mounting shares
4. Query live data
5. Can query from anywhere (curl, Python, Claude MCP)

## Next Steps

### Immediate
1. Deploy to server following `docs/DEPLOYMENT.md`
2. Test with `tests/test_api.py`
3. Add API endpoint to your workflow

### Future Enhancements
1. **Caching**: Add Redis for frequently-run queries
2. **Rate Limiting**: Prevent API abuse
3. **Query Queue**: For expensive queries, return job ID and poll for results
4. **Metrics**: Add Prometheus endpoint for monitoring
5. **MCP HTTP Wrapper**: Create MCP client that calls HTTP API instead of direct DB access

## Comparing Approaches

### SSH Tunnel (Recommended Earlier)
- **Pros**: Zero code, uses existing SSH
- **Cons**: MCP server still runs locally, SSH can disconnect
- **Best for**: Quick solution, no other clients

### Flask API (What We Built)
- **Pros**: Multiple clients, stable, HTTP standard
- **Cons**: More infrastructure, need to maintain server
- **Best for**: Multiple clients, stable long-term solution

### Your Use Case
Since you've built Flask APIs before and want a proper solution, the Flask API is the right choice. The SSH approach would work but wouldn't scale if you want:
- Other team members to query
- Web dashboard later
- Scheduled queries/reports
- Integration with other tools

## Testing

```bash
# Run test suite
python tests/test_api.py http://localhost:5000 your-api-key
```

Tests include:
1. Health check (no auth)
2. Status check (no auth)
3. Auth enforcement
4. Machine queries
5. Database stats
6. Event queries

## Performance Characteristics

**Expected Performance:**
- Simple queries: ~50-200ms
- Complex JOINs: ~200-1000ms
- Large result sets: ~1-5s
- Database stats: ~2-3s

**Bottlenecks:**
1. SQLite file I/O (single writer lock)
2. Network latency (if over VPN)
3. Large result set serialization

**Mitigations:**
- Read-only mode avoids write locks
- Pagination via `limit` parameter
- Gunicorn workers for parallelism
- Future: Add caching layer

## Security Considerations

1. **API Key Rotation**: Change keys regularly
2. **HTTPS**: Use nginx reverse proxy with SSL
3. **Firewall**: Restrict to known IPs
4. **Logs**: Monitor for suspicious queries
5. **Rate Limiting**: Add if needed (future)

## Maintenance

**Regular Tasks:**
- Monitor logs: `sudo journalctl -u munkireport-api -f`
- Check disk space (log rotation enabled)
- Update dependencies monthly
- Rotate API keys quarterly

**Updates:**
```bash
sudo systemctl stop munkireport-api
cd /opt/flask-munkireport && git pull
source venv/bin/activate && pip install -r requirements.txt
sudo systemctl start munkireport-api
```

## Support

For issues:
1. Check logs: `sudo journalctl -u munkireport-api -n 100`
2. Test manually: `python run.py`
3. Verify database access: Check permissions
4. Test API: `python tests/test_api.py`

---

**Ready to deploy?** Follow `docs/DEPLOYMENT.md`

**Questions about the API?** See `README.md`

**Want to extend it?** The code is modular - add new routes in `src/flask_munkireport/routes/`
