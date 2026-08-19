@echo off
echo Wiping database volume and recreating...
docker-compose down -v
docker-compose up -d
echo Database reset successfully.
