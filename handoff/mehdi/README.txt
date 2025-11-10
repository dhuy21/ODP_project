Client: mehdi
Network: internet-mehdi (172.28.80.0/24)

Accès SSH (depuis cette machine) :
- mehdi-node1 -> ssh vagrant@127.0.0.1 -p 3000
- mehdi-node2 -> ssh vagrant@127.0.0.1 -p 3001
- mehdi-node3 -> ssh vagrant@127.0.0.1 -p 3002
-  -> ssh vagrant@127.0.0.1 -p 3002 

Clé privée Vagrant :
~/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini mehdi -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
