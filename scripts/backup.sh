#!/bin/bash

# Backup script for Broking Terminal V2
set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="trading_terminal_db_${TIMESTAMP}.sql"
CONFIG_BACKUP_FILE="config_${TIMESTAMP}.tar.gz"

echo "🔄 Starting backup process..."

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Backup PostgreSQL database
echo "💾 Backing up database..."
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres trading_terminal > "${BACKUP_DIR}/${DB_BACKUP_FILE}"

# Backup configuration files
echo "📋 Backing up configuration..."
tar -czf "${BACKUP_DIR}/${CONFIG_BACKUP_FILE}" \
    .env.production \
    nginx.prod.conf \
    docker-compose.prod.yml \
    ssl/ \
    logs/ \
    --exclude='logs/*.log' 2>/dev/null || true

# Backup Redis data
echo "🔴 Backing up Redis data..."
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli BGSAVE
docker cp $(docker-compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb" 2>/dev/null || true

# Clean old backups (keep last 7 days)
echo "🧹 Cleaning old backups..."
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete 2>/dev/null || true
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete 2>/dev/null || true

# Create backup summary
echo "📊 Creating backup summary..."
cat > "${BACKUP_DIR}/backup_${TIMESTAMP}.txt" << EOF
Backup Summary - $(date)
=============================
Database: ${DB_BACKUP_FILE}
Config: ${CONFIG_BACKUP_FILE}
Redis: redis_${TIMESTAMP}.rdb

Files created:
- $(ls -lh "${BACKUP_DIR}/${DB_BACKUP_FILE}" 2>/dev/null || echo "Database backup failed")
- $(ls -lh "${BACKUP_DIR}/${CONFIG_BACKUP_FILE}" 2>/dev/null || echo "Config backup failed")
- $(ls -lh "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb" 2>/dev/null || echo "Redis backup failed")

Total backup size: $(du -sh ${BACKUP_DIR} | cut -f1)
EOF

echo "✅ Backup completed successfully!"
echo "📁 Backup location: ${BACKUP_DIR}"
echo "📋 Summary file: backup_${TIMESTAMP}.txt"
echo ""
echo "To restore:"
echo "1. Database: docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres trading_terminal < ${BACKUP_DIR}/${DB_BACKUP_FILE}"
echo "2. Config: tar -xzf ${BACKUP_DIR}/${CONFIG_BACKUP_FILE}"
echo "3. Redis: docker cp ${BACKUP_DIR}/redis_${TIMESTAMP}.rdb \$(docker-compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb"
