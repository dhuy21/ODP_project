Client: tri
Network: internet-tri (172.28.104.0/24)

Accès SSH (depuis cette machine) :
- tri-node1 -> ssh vagrant@127.0.0.1 -p 3240
- tri-node2 -> ssh vagrant@127.0.0.1 -p 3241
- tri-node3 -> ssh vagrant@127.0.0.1 -p 3242
- tri-node4 -> ssh vagrant@127.0.0.1 -p 3243
-  -> ssh vagrant@127.0.0.1 -p 3243 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini tri -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
