"""
Contrôleur pour la gestion des VMs
"""
from flask import request, jsonify
import yaml
import os
import time

from models import db
from models.vm import VM
from services.docker_service import DockerService
from services.ansible_service import AnsibleService


class VMController:
    """Contrôleur pour les opérations sur les VMs"""
    
    @staticmethod
    def provision():
        """
        Provisionne les VMs pour un utilisateur
        
        Returns:
            JSON response avec le statut et l'URL de redirection
        """
        data = request.json
        
        try:
            # Créer la configuration VM
            config = VM(
                username=data['username'],
                count=data['vm_count'],
                packages=data['packages'],
                password=data['password']
            )
            
            # Déterminer les chemins de fichiers
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(os.path.dirname(current_dir))
            config_file = os.path.join(project_dir, 'requests', f"{config.client_id}.yaml")
            script_path = os.path.join(project_dir, 'allocates.sh')
            
            # Étape 1: Nettoyer les ressources existantes
            print(f"Cleaning up existing resources for {config.client_id}")
            DockerService.cleanup_resources(config.client_id, project_dir)
            
            # Étape 2: Sauvegarder la configuration
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                yaml.dump(config.to_dict(), f)
            
            # Étape 3: Créer les conteneurs Docker
            success, error_msg = DockerService.create_containers(
                script_path, config_file, project_dir
            )
            
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': error_msg
                })
            
            # Attendre que les conteneurs soient prêts
            print("Waiting for containers to be ready...")
            time.sleep(5)
            
            # Étape 4: Créer le fichier d'inventaire Ansible
            inventory_file = AnsibleService.create_inventory_file(config, project_dir)
            print(f"Created inventory file: {inventory_file}")
            
            # Étape 5: Exécuter le playbook Ansible
            ansible_success, stdout, stderr = AnsibleService.run_playbook(
                inventory_file, config, project_dir
            )
            
            if not ansible_success:
                print(f"Ansible execution had errors but continuing: {stderr}")
                # Ne pas échouer ici, juste logger l'erreur
            
            # Étape 6: Sauvegarder la VM dans la base de données
            try:
                # Supprimer les anciennes VMs de cet utilisateur
                VM.query.filter_by(username=config.username).delete()
                
                # Sauvegarder la nouvelle configuration
                db.session.add(config)
                db.session.commit()
                print(f"VM configuration saved to database for user {config.username}")
            except Exception as db_error:
                print(f"Warning: Could not save VM to database: {db_error}")
                # Ne pas échouer le provisioning pour une erreur de DB
            
            # Rediriger vers le dashboard
            return jsonify({
                'status': 'success',
                'redirect': "/admin-dashboard"
            })
            
        except KeyError as e:
            error_msg = f"Missing required field: {str(e)}"
            print(error_msg)
            return jsonify({
                'status': 'error',
                'message': error_msg
            })
        except Exception as e:
            error_msg = f"Error in provision: {str(e)}"
            print(error_msg)
            return jsonify({
                'status': 'error',
                'message': error_msg
            })
    