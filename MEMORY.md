# Agent Memory Configuration & Schema

## 1. Architecture
- **Vector Engine:** ChromaDB (Local, persisted in `./data/chroma`)
- **Metadata Store:** SQLite (Local, `./data/memory.db`)
- **Embedding Model:** `text-embedding-3-small` (or local via `sentence-transformers`)

## 2. Memory Tiers
1.  **Working:** Current conversation buffer (managed by chat context).
2.  **Episodic:** Past interactions (Vector DB + SQLite logs).
3.  **Semantic:** User preferences, project standards (Structured SQLite).

## 3. Data Schema (SQLite)
| Table | Fields | Purpose |
| :--- | :--- | :--- |
| `user_prefs` | `key`, `value`, `updated_at` | Global persistent state |
| `project_ctx` | `id`, `filename`, `summary`, `tags` | Codebase/Repo conventions |
| `history` | `id`, `timestamp`, `vector_id`, `summary` | Interaction audit trail |

## 4. Operational Policies
- **Retention:** Interactions > 90 days are archived or purged.
- **Privacy:** Sensitive credentials (keys/tokens) MUST NOT be stored in memory.
