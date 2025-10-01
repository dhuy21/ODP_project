#!/usr/bin/env bash
# entrypoint.sh
# If an ID is passed as environment variable NODE_ID, write it and set hostname

if [ -n "$NODE_ID" ]; then
  echo "$NODE_ID" > /etc/node_id
  hostnamectl set-hostname "node-$NODE_ID" 2>/dev/null || true
fi

# Start sshd in foreground
/usr/sbin/sshd -D