# Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-server sudo curl ca-certificates && \
    useradd -m -s /bin/bash vagrant && echo 'vagrant:vagrant' | chpasswd && \
    mkdir -p /home/vagrant/.ssh /var/run/sshd && \
    curl -fsSL https://raw.githubusercontent.com/hashicorp/vagrant/master/keys/vagrant.pub \
      -o /home/vagrant/.ssh/authorized_keys && \
    chmod 700 /home/vagrant/.ssh && chmod 600 /home/vagrant/.ssh/authorized_keys && \
    chown -R vagrant:vagrant /home/vagrant/.ssh && \
    echo 'vagrant ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/99-vagrant && \
    chmod 0440 /etc/sudoers.d/99-vagrant

# Small script to write the ID and set hostname at container start
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 22
CMD ["/usr/local/bin/entrypoint.sh"]