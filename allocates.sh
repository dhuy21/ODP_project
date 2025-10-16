#!/usr/bin/env bash
set -euo pipefail

REQ_FILE="${1:-requests/clientA.yaml}"

# --- Vérifs préalables ---
command -v docker >/dev/null || { echo "Docker requis"; exit 1; }
command -v ansible >/dev/null || { echo "Ansible requis"; exit 1; }
command -v python3 >/dev/null || { echo "python3 requis"; exit 1; }
python3 - <<'PY' 2>/dev/null || { echo "PyYAML manquant: pip3 install pyyaml"; exit 1; }
import yaml, sys
PY

# --- Parse YAML -> variables shell (sans readarray) ---
eval "$(
python3 - "$REQ_FILE" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
cid   = d.get('client_id','clientX')
cnt   = int(d.get('count',1))
sub   = d.get('subnet_cidr','172.28.50.0/24')
pkgs  = ",".join(d.get('packages',[]))
print(f'CLIENT_ID="{cid}"')
print(f'COUNT="{cnt}"')
print(f'SUBNET="{sub}"')
print(f'PKGS_CSV="{pkgs}"')
PY
)"

NET_NAME="internet-${CLIENT_ID}"
IMAGE_TAG="labnode:${CLIENT_ID}"

echo "==> Build image"
docker build -t "${IMAGE_TAG}" --platform=linux/arm64 -f ./Docker/ssh/Dockerfile ./Docker/ssh

echo "==> Create network ${NET_NAME} (${SUBNET}) if needed"
if ! docker network inspect "${NET_NAME}" >/dev/null 2>&1; then
  docker network create --subnet "${SUBNET}" "${NET_NAME}"
fi

echo "==> Clean up existing containers"
docker rm -f $(docker ps -a -q --filter "label=client=${CLIENT_ID}") 2>/dev/null || true

echo "==> Start ${COUNT} containers"
mkdir -p Ansible "handoff/${CLIENT_ID}"
INVENTORY="Ansible/inventory.ini"
echo "[${CLIENT_ID}]" > "${INVENTORY}"

# base IP from subnet (e.g. 172.28.10.0/24 -> 172.28.10)
BASE_PREFIX="$(echo "${SUBNET}" | cut -d'/' -f1 | awk -F. '{print $1"."$2"."$3}')"
HOST_START=10   # .11, .12, ... pour les nœuds
for i in $(seq 1 "${COUNT}"); do
  NAME="${CLIENT_ID}-node${i}"
  IP="${BASE_PREFIX}.$((HOST_START+i))"
  HOST_PORT=$((2199+i))  # 2200, 2201, ...

  echo "   - ${NAME} -> ${IP} (ssh: localhost:${HOST_PORT})"

  docker run -d --restart unless-stopped \
    --name "${NAME}" \
    --network "${NET_NAME}" --ip "${IP}" \
    -p "127.0.0.1:${HOST_PORT}:22" \
    -l "client=${CLIENT_ID}" \
    "${IMAGE_TAG}" >/dev/null

  echo "${NAME} ansible_host=127.0.0.1 ansible_port=${HOST_PORT} ansible_user=vagrant ansible_ssh_private_key_file=${HOME}/.vagrant.d/insecure_private_key" >> "${INVENTORY}"
done

{
  echo ""
  echo "[${CLIENT_ID}:vars]"
  echo "packages=${PKGS_CSV}"
} >> "${INVENTORY}"

HANDOFF="handoff/${CLIENT_ID}/README.txt"
mkdir -p "$(dirname "${HANDOFF}")"
cat > "${HANDOFF}" <<EOF
Client: ${CLIENT_ID}
Network: ${NET_NAME} (${SUBNET})

Accès SSH (depuis cette machine) :
$(awk "/^\[${CLIENT_ID}\]/{f=1;next} /^\[/{f=0} f" ${INVENTORY} \
 | awk '{for(i=1;i<=NF;i++) if($i~/ansible_port=/){split($i,a,"=");p=a[2]} } {printf "- %s -> ssh vagrant@127.0.0.1 -p %s\n",$1,p}') 

Clé privée Vagrant :
${HOME}/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini ${CLIENT_ID} -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
EOF

echo "==> Done."
echo "   Inventaire: ${INVENTORY}"
echo "   Handoff:    ${HANDOFF}"
echo
echo "Pour tester :"
echo "  ansible -i ${INVENTORY} ${CLIENT_ID} -m ping"
echo "  ansible-playbook -i ${INVENTORY} Ansible/playbook.yml"