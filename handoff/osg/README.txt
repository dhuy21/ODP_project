Client: osg
Network: internet-osg (172.28.63.0/24)

Accès SSH (depuis cette machine) :
- osg-node1 -> ssh vagrant@127.0.0.1 -p 2830
- osg-node2 -> ssh vagrant@127.0.0.1 -p 2831
- osg-node3 -> ssh vagrant@127.0.0.1 -p 2832
-  -> ssh vagrant@127.0.0.1 -p 2832 

Clé privée Vagrant :
~/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini osg -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
