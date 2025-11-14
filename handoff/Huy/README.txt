Client: Huy
Network: internet-Huy (172.28.211.0/24)

Accès SSH (depuis cette machine) :
- Huy-node1 -> ssh vagrant@127.0.0.1 -p 4310
- Huy-node2 -> ssh vagrant@127.0.0.1 -p 4311
- Huy-node3 -> ssh vagrant@127.0.0.1 -p 4312
- Huy-node4 -> ssh vagrant@127.0.0.1 -p 4313
-  -> ssh vagrant@127.0.0.1 -p 4313 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini Huy -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
