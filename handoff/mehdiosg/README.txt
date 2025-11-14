Client: mehdiosg
Network: internet-mehdiosg (172.28.94.0/24)

Accès SSH (depuis cette machine) :
- mehdiosg-node1 -> ssh vagrant@127.0.0.1 -p 3140
- mehdiosg-node2 -> ssh vagrant@127.0.0.1 -p 3141
- mehdiosg-node3 -> ssh vagrant@127.0.0.1 -p 3142
- mehdiosg-node4 -> ssh vagrant@127.0.0.1 -p 3143
-  -> ssh vagrant@127.0.0.1 -p 3143 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini mehdiosg -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
