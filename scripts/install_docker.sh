#!/bin/bash
apt-get remove docker docker-engine docker.io containerd runc
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y python3-pip
apt-get install -y docker-ce docker-ce-cli containerd.io
apt-cache madison docker-ce

systemctl enable docker.service
systemctl enable containerd.service


#install docker-compose
mkdir -p ~/.docker/cli-plugins/
curl -SL https://github.com/docker/compose/releases/download/v2.2.3/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
echo "step 3"
chmod +x ~/.docker/cli-plugins/docker-compose
chown $USER /var/run/docker.sock


cp ~/.docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

docker-compose version


systemctl enable docker.service
systemctl enable containerd.service
