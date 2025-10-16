Client: clientA
Network: internet-clientA (172.28.10.0/24)

Accès SSH (depuis cette machine) :
- clientA-node1 -> ssh vagrant@127.0.0.1 -p 2200
- clientA-node2 -> ssh vagrant@127.0.0.1 -p 2201
- clientA-node3 -> ssh vagrant@127.0.0.1 -p 2202
-  -> ssh vagrant@127.0.0.1 -p 2202 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini clientA -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
