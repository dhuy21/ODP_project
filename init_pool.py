import sys
import os

# Add web/services to import path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'web'))

from services.docker_service import DockerService
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

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