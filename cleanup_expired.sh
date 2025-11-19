#!/usr/bin/env bash
# Run this script every minute with cron to auto-release expired containers

while true; do
    ./pool_manager.sh check-expired
    sleep 60
done