Client: dinhhuydeptrai
Network: internet-dinhhuydeptrai (172.28.59.0/24)

Accès SSH (depuis cette machine) :
- dinhhuydeptrai-node1 -> ssh vagrant@127.0.0.1 -p 2790
- dinhhuydeptrai-node2 -> ssh vagrant@127.0.0.1 -p 2791
-  -> ssh vagrant@127.0.0.1 -p 2791 

Clé privée Vagrant :
/home/byn227/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini dinhhuydeptrai -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
