Client: te
Network: internet-te (172.28.143.0/24)

Accès SSH (depuis cette machine) :
- te-node1 -> ssh vagrant@127.0.0.1 -p 3630
- te-node2 -> ssh vagrant@127.0.0.1 -p 3631
- te-node3 -> ssh vagrant@127.0.0.1 -p 3632
- te-node4 -> ssh vagrant@127.0.0.1 -p 3633
- te-node5 -> ssh vagrant@127.0.0.1 -p 3634
-  -> ssh vagrant@127.0.0.1 -p 3634 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini te -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
