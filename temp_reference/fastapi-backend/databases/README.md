# Database Directory
# This directory contains all database files for the Trading Terminal application

## Database Files

### SQLite Database
- `trading_terminal.db` - Main application database
  - Tables: dhan_credentials, credential_logs
  - Size: ~32 KB (current)
  - Purpose: User authentication, credential logging

## Database Structure

### Tables

#### dhan_credentials
Stores DhanHQ authentication credentials and user authentication data.

#### credential_logs
Logs all credential-related activities for auditing and debugging.

## Configuration

### Database URL
```
sqlite+aiosqlite:///./databases/trading_terminal.db
```

### Environment Variables
- `DATABASE_URL` - Database connection string
- Configured in: `.env`, `docker-compose.yml`

## Backup & Maintenance

### Backup Commands
```bash
# Full database backup
sqlite3 databases/trading_terminal.db ".backup databases/backup_$(date +%Y%m%d_%H%M%S).db"

# Schema backup
sqlite3 databases/trading_terminal.db ".schema > databases/schema.sql"

# Data export
sqlite3 databases/trading_terminal.db ".dump > databases/export.sql"
```

### Maintenance
- Database is automatically created on first run
- Tables are created using SQLAlchemy migrations
- No manual intervention required

## Security Notes

- Database contains sensitive authentication data
- Ensure proper file permissions
- Regular backups recommended
- Do not commit database files to version control

## Last Updated
2026-01-31T06:05:00Z - Database reorganized into dedicated directory
