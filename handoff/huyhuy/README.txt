Client: huyhuy
Network: internet-huyhuy (172.28.105.0/24)

Accès SSH (depuis cette machine) :
- huyhuy-node1 -> ssh vagrant@127.0.0.1 -p 3250
- huyhuy-node2 -> ssh vagrant@127.0.0.1 -p 3251
- huyhuy-node3 -> ssh vagrant@127.0.0.1 -p 3252
-  -> ssh vagrant@127.0.0.1 -p 3252 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini huyhuy -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
