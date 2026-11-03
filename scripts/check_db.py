import os
from pathlib import Path
from neo4j import GraphDatabase
import json

def load_env(env_path: Path):
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

def main():
    root = Path(__file__).resolve().parent.parent
    load_env(root / ".env")

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    print(f"Connecting to Neo4j at {uri} (user: {user}, db: {database})...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session(database=database) as session:
        result = session.run("MATCH (n) RETURN count(n) AS node_count").single()
        node_count = result["node_count"]
        
        rel_result = session.run("MATCH ()-[r]->() RETURN count(r) AS rel_count").single()
        rel_count = rel_result["rel_count"]

        snapshots = session.run("MATCH (n:KGNode) RETURN DISTINCT n.snapshot_id AS snapshot").values()
        snapshot_list = [s[0] for s in snapshots if s[0]]

        print(f"Current database status: {node_count} nodes, {rel_count} relationships.")
        if snapshot_list:
            print(f"Existing snapshots in DB: {snapshot_list}")
        else:
            print("No snapshots found in database.")

    driver.close()

if __name__ == "__main__":
    main()
