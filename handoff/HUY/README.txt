Client: HUY
Network: internet-HUY (172.28.133.0/24)

Accès SSH (depuis cette machine) :
- HUY-node1 -> ssh vagrant@127.0.0.1 -p 3530
- HUY-node2 -> ssh vagrant@127.0.0.1 -p 3531
-  -> ssh vagrant@127.0.0.1 -p 3531 

Clé privée Vagrant :
/home/dhuy21/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini HUY -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
