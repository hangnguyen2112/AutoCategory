"""
Category Version Control System

Tracks changes to categories over time:
- Version snapshots
- Diff between versions
- Rollback to previous versions
- Change history
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import asyncpg


class CategoryVersionControl:
    """Manages category versioning and change tracking"""
    
    def __init__(self, db_pool: asyncpg.Pool, data_dir: str = "./api/data"):
        self.db_pool = db_pool
        self.data_dir = Path(data_dir)
        self.versions_dir = self.data_dir / "categories_versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_snapshot(
        self,
        categories: List[Dict],
        source: str = "manual",
        description: Optional[str] = None
    ) -> Dict:
        """Create a new version snapshot of categories"""
        version_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        version_path = self.versions_dir / f"v{version_id}.json"
        
        # Prepare version metadata
        version_data = {
            "version_id": version_id,
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "description": description or f"Snapshot at {datetime.now()}",
            "total_categories": len(categories),
            "categories": categories
        }
        
        # Save version file
        with open(version_path, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)
        
        # Record in database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO category_versions (version_id, source, description, total_categories, file_path)
                VALUES ($1, $2, $3, $4, $5)
            """, version_id, source, description, len(categories), str(version_path))
        
        return {
            "success": True,
            "version_id": version_id,
            "path": str(version_path),
            "total_categories": len(categories),
            "timestamp": version_data["timestamp"]
        }
    
    async def load_version(self, version_id: str) -> Optional[Dict]:
        """Load a specific version by ID"""
        version_path = self.versions_dir / f"v{version_id}.json"
        
        if not version_path.exists():
            return None
        
        with open(version_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    async def list_versions(self, limit: int = 50) -> List[Dict]:
        """List all available versions"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT version_id, source, description, total_categories, created_at
                FROM category_versions
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
        
        return [
            {
                "version_id": row["version_id"],
                "source": row["source"],
                "description": row["description"],
                "total_categories": row["total_categories"],
                "created_at": row["created_at"].isoformat()
            }
            for row in rows
        ]
    
    async def compare_versions(
        self,
        version_a: str,
        version_b: str
    ) -> Dict:
        """Compare two versions and return differences"""
        data_a = await self.load_version(version_a)
        data_b = await self.load_version(version_b)
        
        if not data_a or not data_b:
            return {
                "success": False,
                "error": "One or both versions not found"
            }
        
        cats_a = {cat["id"]: cat for cat in data_a["categories"]}
        cats_b = {cat["id"]: cat for cat in data_b["categories"]}
        
        ids_a = set(cats_a.keys())
        ids_b = set(cats_b.keys())
        
        # Find differences
        added = ids_b - ids_a
        removed = ids_a - ids_b
        common = ids_a & ids_b
        
        modified = []
        for cat_id in common:
            if cats_a[cat_id] != cats_b[cat_id]:
                modified.append({
                    "id": cat_id,
                    "old": cats_a[cat_id],
                    "new": cats_b[cat_id]
                })
        
        return {
            "success": True,
            "version_a": version_a,
            "version_b": version_b,
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "modified": len(modified),
                "unchanged": len(common) - len(modified)
            },
            "details": {
                "added": [cats_b[cid] for cid in added],
                "removed": [cats_a[cid] for cid in removed],
                "modified": modified
            }
        }
    
    async def rollback_to_version(self, version_id: str) -> Dict:
        """Rollback categories to a specific version"""
        version_data = await self.load_version(version_id)
        
        if not version_data:
            return {
                "success": False,
                "error": f"Version not found: {version_id}"
            }
        
        # Create backup of current version first
        current_path = self.data_dir / "categories.json"
        if current_path.exists():
            with open(current_path, 'r', encoding='utf-8') as f:
                current_categories = json.load(f)
            
            await self.create_snapshot(
                current_categories,
                source="auto_backup",
                description=f"Auto backup before rollback to {version_id}"
            )
        
        # Write the old version as current
        categories = version_data["categories"]
        with open(current_path, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "version_id": version_id,
            "total_categories": len(categories),
            "message": f"Rolled back to version {version_id}"
        }
    
    async def get_change_history(
        self,
        category_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Get change history for a specific category"""
        versions = await self.list_versions(limit=50)
        
        history = []
        prev_data = None
        
        for version_info in versions:
            version_data = await self.load_version(version_info["version_id"])
            if not version_data:
                continue
            
            # Find category in this version
            category = next(
                (cat for cat in version_data["categories"] if cat["id"] == category_id),
                None
            )
            
            if category:
                change_type = "exists"
                if prev_data is None:
                    change_type = "first_seen"
                elif prev_data != category:
                    change_type = "modified"
                
                history.append({
                    "version_id": version_info["version_id"],
                    "timestamp": version_info["created_at"],
                    "change_type": change_type,
                    "data": category,
                    "previous_data": prev_data
                })
                
                prev_data = category
            else:
                if prev_data is not None:
                    history.append({
                        "version_id": version_info["version_id"],
                        "timestamp": version_info["created_at"],
                        "change_type": "deleted",
                        "data": None,
                        "previous_data": prev_data
                    })
                    prev_data = None
            
            if len(history) >= limit:
                break
        
        return history


# Add table for version control
CATEGORY_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS category_versions (
    id SERIAL PRIMARY KEY,
    version_id VARCHAR(50) UNIQUE NOT NULL,
    source VARCHAR(100),
    description TEXT,
    total_categories INTEGER,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_category_versions_created_at 
ON category_versions(created_at DESC);
"""


async def init_version_control(db_pool: asyncpg.Pool):
    """Initialize version control database table"""
    async with db_pool.acquire() as conn:
        await conn.execute(CATEGORY_VERSIONS_TABLE)
    print("✅ Category version control initialized")


# CLI interface
async def main():
    """CLI interface for category versioning"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python category_versioning.py snapshot [description]")
        print("  python category_versioning.py list")
        print("  python category_versioning.py compare <version_a> <version_b>")
        print("  python category_versioning.py rollback <version_id>")
        print("  python category_versioning.py history <category_id>")
        return
    
    # Connect to database
    db_url = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/autocategory")
    pool = await asyncpg.create_pool(db_url)
    
    vcs = CategoryVersionControl(pool)
    command = sys.argv[1]
    
    if command == "snapshot":
        # Load current categories
        with open("./api/data/categories.json", 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
        result = await vcs.create_snapshot(categories, source="manual", description=description)
        print(json.dumps(result, indent=2))
    
    elif command == "list":
        versions = await vcs.list_versions()
        print(json.dumps(versions, indent=2))
    
    elif command == "compare":
        if len(sys.argv) < 4:
            print("Error: Need two version IDs")
            return
        
        version_a = sys.argv[2]
        version_b = sys.argv[3]
        result = await vcs.compare_versions(version_a, version_b)
        print(json.dumps(result, indent=2))
    
    elif command == "rollback":
        if len(sys.argv) < 3:
            print("Error: version_id required")
            return
        
        version_id = sys.argv[2]
        result = await vcs.rollback_to_version(version_id)
        print(json.dumps(result, indent=2))
    
    elif command == "history":
        if len(sys.argv) < 3:
            print("Error: category_id required")
            return
        
        category_id = int(sys.argv[2])
        history = await vcs.get_change_history(category_id)
        print(json.dumps(history, indent=2))
    
    else:
        print(f"Unknown command: {command}")
    
    await pool.close()


if __name__ == "__main__":
    import os
    asyncio.run(main())
