# ODP - Orchestration & Deployment Platform

A comprehensive platform for provisioning and orchestrating containerized resources (workers) that allows clients to reserve and deploy resources, monitor their status, and automatically replace missing resources to maintain a defined service level.

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Usage Guide](#usage-guide)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Project Overview

**ODP (Orchestration & Deployment Platform)** is an automated "Pentest" platform that provides:

- **Resource Pool Management**: Maintains a pool of containerized workers (VMs)
- **Reservation System**: Allows users to reserve and deploy virtual machines
- **Automatic Monitoring**: Tracks resource status and health
- **Auto-Recovery**: Automatically replaces missing or failed resources
- **Web-Based Interface**: User-friendly dashboard for managing reservations

## Features

- **User Authentication**: Secure login/registration system with role-based access (Admin/User)
- **VM Provisioning**: Reserve and deploy multiple virtual machines on-demand
- **Real-time Monitoring**: Live statistics and health checks for reserved resources
- **Automatic Expiry**: Reservations automatically expire and release resources
- **Auto-Recovery**: Automatic detection and replacement of failed containers
- **Web Terminal**: Built-in SSH terminal for direct VM access
- **Admin Dashboard**: Comprehensive admin panel for user and resource management
- **WebSocket Support**: Real-time updates via Socket.IO

## Architecture

This project uses a modern **MVC (Model-View-Controller)** architecture:

- **Backend**: Python 3.8+ with Flask framework
- **Database**: MySQL (replaces JSON file storage)
- **Container Management**: Docker SDK for container orchestration
- **Frontend**: HTML/CSS/JavaScript with Jinja2 templating
- **Real-time**: Flask-SocketIO for WebSocket communication
- **SSH**: Paramiko for secure shell connections


## Prerequisites

Before installing, ensure you have the following installed:

- **Python 3.8+** (Python 3.12 recommended)
- **MySQL Server 5.7+** or **MariaDB 10.3+**
- **Docker** and **Docker Compose**
- **Git** (for cloning the repository)

### System Requirements

- **RAM**: Minimum 4GB (8GB+ recommended for running multiple containers)
- **Disk Space**: At least 10GB free space
- **OS**: Linux, macOS, or Windows (with WSL2)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ODP_project/src
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Required packages:**
- Flask 2.3.3
- Flask-SocketIO 5.3.6
- mysql-connector-python 8.3.0
- python-dotenv 1.0.1
- docker 7.1.2
- paramiko 3.3.1
- pyyaml 6.0.1

### Step 4: Install and Start MySQL

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

**On macOS (using Homebrew):**
```bash
brew install mysql
brew services start mysql
```

**On Windows:**
Download and install MySQL from [mysql.com](https://dev.mysql.com/downloads/mysql/)

### Step 5: Verify Docker Installation

```bash
docker --version
docker-compose --version
```

Ensure Docker daemon is running:
```bash
docker ps
```

## Database Setup

### Step 1: Create Database and Tables

```bash
# Import the database schema
mysql -u root -p < database/db_schema.sql
```

Or manually:

```bash
# Login to MySQL
mysql -u root -p

# Run the schema file
source database/db_schema.sql;
```

### Step 2: Verify Database Creation

```bash
mysql -u root -p -e "USE odp_platform; SHOW TABLES;"
```

You should see:
- `users`
- `reservations`
- `pool_nodes`

### Step 3: (Optional) Migrate Existing Data

If you have existing data in `web/data/users.json`:

```bash
# Update database credentials in migrate_data.py if needed
python3 database/migrate_data.py
```

## Configuration

### Step 1: Create Environment File

```bash
cd web
cp exemple.env .env
```

### Step 2: Configure Environment Variables

Edit `web/.env` file:

```env
# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=odp_platform

# Flask Application Configuration
# Generate a secret key: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_secret_key_here

# Flask debug mode (True/False)
# Set to False in production
FLASK_DEBUG=True
```

**Important Security Notes:**
- Change `MYSQL_PASSWORD` to your actual MySQL root password
- Generate a strong `SECRET_KEY` for production
- Set `FLASK_DEBUG=False` in production environments
- Never commit `.env` file to version control

### Step 3: Verify Configuration

The application will automatically load the `.env` file. Check the console output when starting the app:

```
[CONFIG] Loaded environment variables from /path/to/web/.env
```

## Running the Application

### Step 1: Initialize the Container Pool

Before starting the web application, initialize the Docker container pool:

```bash
# From project root (src/)
python3 init_pool.py
```

This will:
- Create a Docker network (`pool-network`)
- Create 30 container workers (pool-node-1 to pool-node-30)
- Initialize the pool in the database

**Expected output:**
```
Creating Docker network...
Creating containers...
Pool initialized successfully!
```

### Step 2: Start the Web Application

```bash
cd web
python3 app.py
```

**Expected output:**
```
============================================================
Starting ODP Platform (MVC Architecture)
============================================================
Architecture:
   - Models: User, VM, Reservation, SSH Session
   - Views: Templates in templates/
   - Controllers: Auth, Dashboard, VM, SSH
   - Services: Docker, SSH, Ansible
============================================================
Server starting on http://0.0.0.0:5001
============================================================
```

### Step 3: Access the Application

Open your web browser and navigate to:

```
http://localhost:5001
```

### Default Credentials

- **Username**: `admin`
- **Password**: `admin`

**Important**: Change the admin password immediately after first login!

## Usage Guide

### For Regular Users

1. **Register/Login**
   - Click "Register" to create a new account
   - Or login with existing credentials

2. **Create a Reservation**
   - Navigate to Dashboard
   - Enter number of VMs needed
   - Set duration (in minutes)
   - Optionally specify packages to install
   - Click "Provision"

3. **Manage Reservations**
   - View active reservations on Dashboard
   - Check reservation details and statistics
   - Access VMs via Web Terminal
   - Release resources when done

4. **View History**
   - Check "Reservation History" for past reservations
   - View final statistics for expired/released reservations

### For Administrators

1. **Admin Dashboard**
   - Access `/admin/overview` for system overview
   - View total users, active reservations, pool status

2. **User Management**
   - Access `/admin/users` to manage users
   - Create, delete, or modify user roles
   - View user statistics

3. **Reservation Management**
   - Access `/admin/reservations` to view all reservations
   - Force release or delete reservations
   - Monitor system-wide resource usage

4. **Pool Management**
   - Access `/admin/pool` to view pool status
   - Recover failed containers
   - Monitor pool health

### Web Terminal

- Access terminal from reservation detail page
- Connect to VMs via built-in SSH terminal
- Execute commands directly in containers

## Project Structure

```
src/
├── database/
│   ├── db_schema.sql          # Database schema
│   └── migrate_data.py        # Data migration script
├── web/
│   ├── app.py                 # Flask application entry point
│   ├── config/
│   │   ├── config.py          # Application configuration
│   │   └── exemple.env       # Environment variables template
│   ├── models/                # Data models
│   │   ├── user.py           # User database model
│   │   ├── vm.py             # VM/Reservation models
│   │   └── pool.py           # Pool database model
│   ├── controllers/           # Business logic
│   │   ├── auth_controller.py
│   │   ├── vm_controller.py
│   │   └── dashboard_controller.py
│   ├── routes/                # URL routes
│   │   ├── auth_routes.py
│   │   ├── main_routes.py
│   │   └── provision_routes.py
│   ├── services/              # External services
│   │   ├── docker_service.py
│   │   ├── ssh_service.py
│   │   └── ansible_service.py
│   ├── templates/             # HTML templates
│   ├── static/                # CSS, JS, images
│   └── data/                  # Legacy JSON data (for migration)
├── init_pool.py               # Pool initialization script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Troubleshooting

### Database Connection Issues

**Error**: `Can't connect to MySQL server`

**Solutions:**
1. Verify MySQL is running:
   ```bash
   sudo systemctl status mysql  # Linux
   brew services list           # macOS
   ```

2. Check credentials in `.env` file
3. Verify database exists:
   ```bash
   mysql -u root -p -e "SHOW DATABASES LIKE 'odp_platform';"
   ```

### Docker Issues

**Error**: `Cannot connect to Docker daemon`

**Solutions:**
1. Start Docker service:
   ```bash
   sudo systemctl start docker  # Linux
   ```

2. Add user to docker group:
   ```bash
   sudo usermod -aG docker $USER
   ```

3. Verify Docker is running:
   ```bash
   docker ps
   ```

### Port Already in Use

**Error**: `Address already in use`

**Solutions:**
1. Find process using port 5001:
   ```bash
   lsof -i :5001  # macOS/Linux
   netstat -ano | findstr :5001  # Windows
   ```

2. Kill the process or change port in `app.py`

### Container Pool Issues

**Error**: Containers not initializing

**Solutions:**
1. Check Docker network:
   ```bash
   docker network ls | grep pool-network
   ```

2. Reinitialize pool:
   ```bash
   python3 init_pool.py
   ```

3. Check container status:
   ```bash
   docker ps -a | grep pool-node
   ```

### Environment Variables Not Loading

**Error**: Configuration not found

**Solutions:**
1. Verify `.env` file exists in `web/` directory
2. Check file permissions
3. Verify `python-dotenv` is installed:
   ```bash
   pip list | grep python-dotenv
   ```

## Development

### Running in Development Mode

```bash
# Set debug mode in .env
FLASK_DEBUG=True

# Run with auto-reload
python3 app.py
```

### Database Migrations

When schema changes are made:

1. Update `database/db_schema.sql`
2. Run migration:
   ```bash
   mysql -u root -p odp_platform < database/db_schema.sql
   ```

### Testing Database Queries

```bash
mysql -u root -p odp_platform

# Example queries
SELECT * FROM users;
SELECT * FROM reservations WHERE status = 'active';
SELECT * FROM pool_nodes WHERE status = 'free';
```

### Logging

Application logs are printed to console. For production, consider:
- Using Python's `logging` module
- Configuring log rotation
- Setting up log aggregation

## Security Considerations

1. **Change Default Passwords**: Always change default admin password
2. **Environment Variables**: Never commit `.env` files
3. **Secret Key**: Use strong, randomly generated secret keys
4. **Database Access**: Use dedicated database user (not root) in production
5. **HTTPS**: Use HTTPS in production (configure reverse proxy)
6. **Firewall**: Restrict access to MySQL port (3306)
7. **Docker Security**: Keep Docker and containers updated

## Additional Resources

- **Database Schema**: See `database/db_schema.sql`
- **API Documentation**: Check route files in `web/routes/`
- **Architecture Details**: See MVC structure in `web/` directory

## Team Members

- Mehdi Ouseggua
- Vinh Tri NGUYEN
- Dinh Huy NGUYEN
- Khalid
- Thanh Tu VO
- Gia Khanh NGUYEN

## License

[Add your license information here]

---

**Need Help?** Check the troubleshooting section or review the project documentation.
