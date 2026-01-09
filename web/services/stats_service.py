import subprocess

class StatsService:
    """Service for getting container statistics"""
    
    def __init__(self):
        pass
    
    def get_cpu_cores(self):
        """Get number of CPU cores on the system"""
        try:
            result = subprocess.run(
                ['nproc'],
                capture_output=True,
                text=True,
                timeout=2
            )
            return int(result.stdout.strip()) if result.returncode == 0 else 1
        except Exception as e:
            print(f"[STATS] Error getting CPU cores: {e}")
            return 1
    
    def get_container_stats(self, node_name):
        """Get stats for a specific container"""
        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 
                 '{{.Container}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}', node_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse output: container_name,cpu_perc,mem_usage,mem_perc
                parts = result.stdout.strip().split(',')
                if len(parts) >= 4:
                    return {
                        'container': parts[0].strip(),
                        'cpu_raw': parts[1].strip(),
                        'memory': parts[2].strip(),
                        'memory_percent': parts[3].strip()
                    }
            
            return None
        except Exception as e:
            print(f"[STATS] Error getting stats for {node_name}: {e}")
            return None
    
    def normalize_cpu_percent(self, cpu_perc_str, cpu_cores):
        """Normalize CPU percentage to 0-100% range"""
        try:
            cpu_perc_raw = float(cpu_perc_str.rstrip('%'))
            cpu_perc_normalized = cpu_perc_raw / cpu_cores
            return f"{cpu_perc_normalized:.2f}%"
        except Exception as e:
            print(f"[STATS] Error normalizing CPU: {e}")
            return cpu_perc_str
    
    def get_reservation_stats(self, nodes):
        """Get stats for all nodes in a reservation"""
        cpu_cores = self.get_cpu_cores()
        stats = {}
        
        for node in nodes:
            node_name = node.get('name')
            if not node_name:
                continue
            
            node_stats = self.get_container_stats(node_name)
            
            if node_stats:
                # Normalize CPU percentage
                cpu_display = self.normalize_cpu_percent(
                    node_stats['cpu_raw'],
                    cpu_cores
                )
                
                stats[node_name] = {
                    'cpu': cpu_display,
                    'memory': node_stats['memory'],
                    'memory_percent': node_stats['memory_percent']
                }
        
        return stats
