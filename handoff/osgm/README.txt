Client: osgm
Network: internet-osgm (172.28.20.0/24)

Accès SSH (depuis cette machine) :
- osgm-node1 -> ssh vagrant@127.0.0.1 -p 2200
- osgm-node2 -> ssh vagrant@127.0.0.1 -p 2201
- osgm-node3 -> ssh vagrant@127.0.0.1 -p 2202
-  -> ssh vagrant@127.0.0.1 -p 2202 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini osgm -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
