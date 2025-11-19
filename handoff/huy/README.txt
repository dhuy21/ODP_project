Client: huy
Network: internet-huy (172.28.247.0/24)

Accès SSH (depuis cette machine) :
- huy-node1 -> ssh vagrant@127.0.0.1 -p 4670
- huy-node2 -> ssh vagrant@127.0.0.1 -p 4671
-  -> ssh vagrant@127.0.0.1 -p 4671 

Clé privée Vagrant :
/home/dhuy21/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini huy -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
