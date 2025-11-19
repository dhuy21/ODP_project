Client: osgg
Network: internet-osgg (172.28.114.0/24)

Accès SSH (depuis cette machine) :
- osgg-node1 -> ssh vagrant@127.0.0.1 -p 3340
- osgg-node2 -> ssh vagrant@127.0.0.1 -p 3341
- osgg-node3 -> ssh vagrant@127.0.0.1 -p 3342
-  -> ssh vagrant@127.0.0.1 -p 3342 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini osgg -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
