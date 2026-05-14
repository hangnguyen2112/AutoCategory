"""
Backup and Restore System for AutoCategory

Provides functionality to:
- Backup database (users, API keys, logs, training data, config)
- Backup categories and Qdrant vectors
- Restore from backups
- Schedule automatic backups
"""

import asyncio
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg
from qdrant_client import QdrantClient


class BackupManager:
    """Manages database and vector store backups"""
    
    def __init__(
        self,
        db_url: str,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        backup_dir: str = "./backups"
    ):
        self.db_url = db_url
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    async def backup_database(self, backup_name: Optional[str] = None) -> Dict:
        """Backup PostgreSQL database to SQL file"""
        if not backup_name:
            backup_name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / f"{backup_name}.sql"
        
        try:
            # Parse database URL
            # Format: postgresql://user:password@host:port/database
            parts = self.db_url.replace("postgresql://", "").split("@")
            user_pass = parts[0].split(":")
            host_db = parts[1].split("/")
            host_port = host_db[0].split(":")
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ""
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else "5432"
            database = host_db[1]
            
            # Use pg_dump
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            result = subprocess.run(
                [
                    "pg_dump",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-d", database,
                    "-f", str(backup_path),
                    "--clean",
                    "--if-exists"
                ],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            
            return {
                "success": True,
                "backup_name": backup_name,
                "backup_path": str(backup_path),
                "size_mb": round(size_mb, 2),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def restore_database(self, backup_name: str) -> Dict:
        """Restore PostgreSQL database from SQL file"""
        backup_path = self.backup_dir / f"{backup_name}.sql"
        
        if not backup_path.exists():
            return {
                "success": False,
                "error": f"Backup file not found: {backup_path}"
            }
        
        try:
            # Parse database URL
            parts = self.db_url.replace("postgresql://", "").split("@")
            user_pass = parts[0].split(":")
            host_db = parts[1].split("/")
            host_port = host_db[0].split(":")
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ""
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else "5432"
            database = host_db[1]
            
            # Use psql
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            result = subprocess.run(
                [
                    "psql",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-d", database,
                    "-f", str(backup_path)
                ],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"psql failed: {result.stderr}")
            
            return {
                "success": True,
                "backup_name": backup_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def backup_categories(self, backup_name: Optional[str] = None) -> Dict:
        """Backup categories JSON file"""
        if not backup_name:
            backup_name = f"categories_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        source_path = Path("./api/data/categories.json")
        backup_path = self.backup_dir / f"{backup_name}.json"
        
        try:
            if not source_path.exists():
                raise FileNotFoundError(f"Categories file not found: {source_path}")
            
            shutil.copy2(source_path, backup_path)
            
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            
            return {
                "success": True,
                "backup_name": backup_name,
                "backup_path": str(backup_path),
                "size_mb": round(size_mb, 2),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def backup_qdrant_collection(
        self,
        collection_name: str = "categories",
        backup_name: Optional[str] = None
    ) -> Dict:
        """Backup Qdrant vector collection"""
        if not backup_name:
            backup_name = f"qdrant_{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            
            # Create snapshot
            snapshot_info = client.create_snapshot(collection_name=collection_name)
            
            # Download snapshot (Qdrant API provides snapshot download)
            # For now, we'll just record the snapshot info
            backup_info = {
                "success": True,
                "backup_name": backup_name,
                "collection_name": collection_name,
                "snapshot_name": snapshot_info.name if hasattr(snapshot_info, 'name') else str(snapshot_info),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save backup info
            info_path = self.backup_dir / f"{backup_name}_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            return backup_info
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def full_backup(self) -> Dict:
        """Perform full system backup (DB + categories + Qdrant)"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"full_backup_{timestamp}"
        
        results = {
            "backup_name": backup_name,
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Backup database
        db_result = await self.backup_database(f"{backup_name}_db")
        results["components"]["database"] = db_result
        
        # Backup categories
        cat_result = await self.backup_categories(f"{backup_name}_categories")
        results["components"]["categories"] = cat_result
        
        # Backup Qdrant
        qdrant_result = await self.backup_qdrant_collection(backup_name=f"{backup_name}_qdrant")
        results["components"]["qdrant"] = qdrant_result
        
        # Overall success
        results["success"] = all(
            r.get("success", False) for r in results["components"].values()
        )
        
        # Save full backup manifest
        manifest_path = self.backup_dir / f"{backup_name}_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return results
    
    async def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        for manifest in self.backup_dir.glob("*_manifest.json"):
            try:
                with open(manifest, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
                    backups.append(backup_info)
            except Exception as e:
                print(f"Error reading manifest {manifest}: {e}")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return backups
    
    async def cleanup_old_backups(self, keep_last_n: int = 10) -> Dict:
        """Delete old backups, keeping only the last N"""
        backups = await self.list_backups()
        
        if len(backups) <= keep_last_n:
            return {
                "success": True,
                "deleted": 0,
                "message": f"Only {len(backups)} backups exist (keeping {keep_last_n})"
            }
        
        to_delete = backups[keep_last_n:]
        deleted_count = 0
        
        for backup in to_delete:
            backup_name = backup.get("backup_name")
            if not backup_name:
                continue
            
            # Delete all files related to this backup
            for file_path in self.backup_dir.glob(f"{backup_name}*"):
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        return {
            "success": True,
            "deleted": deleted_count,
            "message": f"Deleted {len(to_delete)} old backup(s)"
        }


# CLI interface
async def main():
    """CLI interface for backup/restore operations"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_restore.py backup [db|categories|qdrant|full]")
        print("  python backup_restore.py restore <backup_name>")
        print("  python backup_restore.py list")
        print("  python backup_restore.py cleanup [keep_last_n]")
        return
    
    # Load config
    db_url = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/autocategory")
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    backup_dir = os.getenv("BACKUP_DIR", "./backups")
    
    manager = BackupManager(
        db_url=db_url,
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port,
        backup_dir=backup_dir
    )
    
    command = sys.argv[1]
    
    if command == "backup":
        backup_type = sys.argv[2] if len(sys.argv) > 2 else "full"
        
        if backup_type == "db":
            result = await manager.backup_database()
        elif backup_type == "categories":
            result = await manager.backup_categories()
        elif backup_type == "qdrant":
            result = await manager.backup_qdrant_collection()
        elif backup_type == "full":
            result = await manager.full_backup()
        else:
            print(f"Unknown backup type: {backup_type}")
            return
        
        print(json.dumps(result, indent=2))
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Error: backup_name required")
            return
        
        backup_name = sys.argv[2]
        result = await manager.restore_database(backup_name)
        print(json.dumps(result, indent=2))
    
    elif command == "list":
        backups = await manager.list_backups()
        print(json.dumps(backups, indent=2))
    
    elif command == "cleanup":
        keep_last_n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = await manager.cleanup_old_backups(keep_last_n)
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
