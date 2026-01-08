-- Remove database if exists
DROP DATABASE IF EXISTS odp_platform;

CREATE DATABASE IF NOT EXISTS odp_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE odp_platform;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(32) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reservations (
    id VARCHAR(36) PRIMARY KEY,
    user_id INT NOT NULL,
    vm_count INT NOT NULL DEFAULT 1,
    duration_minutes INT NOT NULL,
    status ENUM('active', 'released', 'expired', 'error', 'deleted') NOT NULL,
    created_at DOUBLE NOT NULL, -- real number timestamp permet d'éviter de trop modifier le code Python.
    expires_at DOUBLE NOT NULL,
    nodes JSON,         -- [{"name": "pool-node-1", "ip": "..."}]
    final_stats JSON,   -- CPU/RAM
    packages JSON, 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pool_nodes (
    name VARCHAR(50) PRIMARY KEY,     
    ip VARCHAR(15) NOT NULL,          
    port INT NOT NULL,                
    status ENUM('free', 'allocated', 'maintenance', 'error') DEFAULT 'free',
    owner VARCHAR(32),                
    expiry DOUBLE DEFAULT 0,          
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_reservation_user ON reservations(user_id);
CREATE INDEX idx_reservation_status ON reservations(status);
CREATE INDEX idx_reservation_expires_at ON reservations(expires_at);
CREATE INDEX idx_reservation_status_expires ON reservations(status, expires_at);
