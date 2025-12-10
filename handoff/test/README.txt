Client: test
Network: internet-test (172.28.224.0/24)

Accès SSH (depuis cette machine) :
- test-node1 -> ssh vagrant@127.0.0.1 -p 4440
-  -> ssh vagrant@127.0.0.1 -p 4440 

Clé privée Vagrant :
/Users/mehdiouseggua/.vagrant.d/insecure_private_key

Provisionnement :
  ansible -i Ansible/inventory.ini test -m ping
  ansible-playbook -i Ansible/inventory.ini Ansible/playbook.yml
