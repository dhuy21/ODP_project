Client: osg
Network: internet-osg (172.28.138.0/24)

Accès SSH (depuis cette machine) :
- osg-node1 -> ssh vagrant@127.0.0.1 -p 3580
- osg-node2 -> ssh vagrant@127.0.0.1 -p 3581
- osg-node3 -> ssh vagrant@127.0.0.1 -p 3582
- osg-node4 -> ssh vagrant@127.0.0.1 -p 3583
- osg-node5 -> ssh vagrant@127.0.0.1 -p 3584
-  -> ssh vagrant@127.0.0.1 -p 3584 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini osg -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
