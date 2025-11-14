Client: mehditest
Network: internet-mehditest (172.28.103.0/24)

Accès SSH (depuis cette machine) :
- mehditest-node1 -> ssh vagrant@127.0.0.1 -p 3230
- mehditest-node2 -> ssh vagrant@127.0.0.1 -p 3231
- mehditest-node3 -> ssh vagrant@127.0.0.1 -p 3232
- mehditest-node4 -> ssh vagrant@127.0.0.1 -p 3233
-  -> ssh vagrant@127.0.0.1 -p 3233 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini mehditest -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
