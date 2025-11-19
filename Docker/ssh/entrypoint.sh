#!/bin/bash
set -e

# Setup SSH server
mkdir -p /var/run/sshd

# Generate SSH host keys if they don't exist
if [ ! -f "/etc/ssh/ssh_host_rsa_key" ]; then
  ssh-keygen -A
fi

# Ensure proper permissions for the SSH directory
if [ -d /home/vagrant/.ssh ]; then
  chown -R vagrant:vagrant /home/vagrant/.ssh
  chmod 700 /home/vagrant/.ssh
  [ -f /home/vagrant/.ssh/authorized_keys ] && chmod 600 /home/vagrant/.ssh/authorized_keys
fi

# Start SSH service in foreground mode
echo "Starting SSH server..."
exec /usr/sbin/sshd -D
