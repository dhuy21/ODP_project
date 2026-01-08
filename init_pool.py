import sys
import os
from pathlib import Path

# Add web/services to import path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'web'))

from services.docker_service import DockerService
from dotenv import load_dotenv

# Load environment variables from .env if available
# Try to load from web/.env first, then from project root
web_env_path = Path(current_dir) / 'web' / '.env'
root_env_path = Path(current_dir) / '.env'

if web_env_path.exists():
    load_dotenv(web_env_path)
    print(f"[CONFIG] Loaded environment variables from {web_env_path}")
elif root_env_path.exists():
    load_dotenv(root_env_path)
    print(f"[CONFIG] Loaded environment variables from {root_env_path}")
else:
    load_dotenv()  # Try default locations
    print("[CONFIG] Using environment variables or defaults")

def main():
    print("Starting ODP Pool Initialization...")
    service = DockerService()
    if not service.client:
        print("Error: Cannot connect to Docker. Is it running?")
        sys.exit(1)
    print("This process will build the Docker image and create 30 containers.")
    result = service.init_pool(pool_size=30)
    if result['success']:
        print("Pool initialized successfully.")
        print("Docker containers created.")
        print("MySQL database populated with 'free' nodes.")
    else:
        print(f"Initialization failed: {result.get('error')}")

if __name__ == "__main__":
    main()