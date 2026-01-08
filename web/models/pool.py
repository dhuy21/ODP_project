import mysql.connector
import os
import time

class PoolDatabase:
    def __init__(self):
        # MySQL connection config
        self.db_config = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASSWORD'),
            'database': os.environ.get('MYSQL_DB', 'odp_platform')
        }

    def _get_connection(self):
        return mysql.connector.connect(**self.db_config)

    def get_pool_status(self):
        # Get pool status summary
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "SELECT status, COUNT(*) as count FROM pool_nodes GROUP BY status"
            cursor.execute(sql)
            rows = cursor.fetchall()
            stats = {'total': 0, 'free': 0, 'allocated': 0, 'maintenance': 0}
            for row in rows:
                stats[row['status']] = row['count']
                stats['total'] += row['count']
            return stats
        finally:
            cursor.close()
            conn.close()

    def find_free_nodes(self, count):
        # Find n free nodes
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "SELECT * FROM pool_nodes WHERE status = 'free' ORDER BY port ASC LIMIT %s"
            cursor.execute(sql, (count,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def allocate_node(self, node_name, username, expiry_timestamp):
        # Mark node as allocated
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            sql = """
                UPDATE pool_nodes 
                SET status = 'allocated', owner = %s, expiry = %s 
                WHERE name = %s AND status = 'free'
            """
            cursor.execute(sql, (username, expiry_timestamp, node_name))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def release_node(self, node_name):
        # Set node status to free
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            sql = """
                UPDATE pool_nodes 
                SET status = 'free', owner = NULL, expiry = 0 
                WHERE name = %s
            """
            cursor.execute(sql, (node_name,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def get_nodes_by_owner(self, username):
        # Get nodes owned by user
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "SELECT * FROM pool_nodes WHERE owner = %s"
            cursor.execute(sql, (username,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def upsert_node(self, name, ip, port, status='free'):
        # Insert or update node info
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            sql = """
                INSERT INTO pool_nodes (name, ip, port, status, owner, expiry)
                VALUES (%s, %s, %s, %s, NULL, 0)
                ON DUPLICATE KEY UPDATE 
                    ip=VALUES(ip), 
                    port=VALUES(port), 
                    status=VALUES(status),
                    owner=NULL,
                    expiry=0
            """
            cursor.execute(sql, (name, ip, port, status))
            conn.commit()
        except Exception as e:
            print(f"Error upserting node {name}: {e}")
        finally:
            cursor.close()
            conn.close()