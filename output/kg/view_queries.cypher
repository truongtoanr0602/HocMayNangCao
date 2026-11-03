// Run this parameter command first in Neo4j Browser.
:param snapshot => '1d10ded4d2cfbf1b63efa639a7d8e36499eb0f99cf053e8ceefd3b1077b471c1'

// 1. Show ALL 8 documents in the current snapshot; no Browser parameter required.
MATCH (d:LegalDocument {snapshot_id: '1d10ded4d2cfbf1b63efa639a7d8e36499eb0f99cf053e8ceefd3b1077b471c1'})
OPTIONAL MATCH (d)-[r:REFERS_TO|GUIDES|DETAILS]->(other:LegalDocument)
WHERE other.snapshot_id = d.snapshot_id
RETURN d, r, other;

// 2. Chapters and articles in the Labor Code.
MATCH p=(d:LegalDocument {snapshot_id: $snapshot, id: 'doc-01'})-[:CONTAINS*1..6]->(a:Article)
RETURN p LIMIT 80;

// 5. Article 62 in doc-01 only (detail view).
MATCH p=(a:Article {snapshot_id: $snapshot, document_id: 'doc-01', number: '62'})-[:CONTAINS|HAS_CHUNK*1..3]->(n)
RETURN p;

// 3. Article 35, its clauses, points, and source chunks.
MATCH p=(a:Article {snapshot_id: $snapshot, document_id: 'doc-01', number: '35'})-[:CONTAINS|HAS_CHUNK*1..3]->(n)
WHERE n.snapshot_id = $snapshot
RETURN p LIMIT 100;

// 4. Cross-document relationships between provisions.
MATCH p=(a)-[:GUIDES|DETAILS]->(b)
WHERE a.snapshot_id = $snapshot AND b.snapshot_id = $snapshot
  AND a.document_id <> b.document_id
  AND NOT a:LegalDocument AND NOT b:LegalDocument
RETURN p LIMIT 80;
