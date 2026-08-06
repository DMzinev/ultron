import os
from typing import Optional
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import RepositoryMetadata

class RepositoryAPI:
    @staticmethod
    def get_repositories(store: RepositoryStore) -> list[RepositoryMetadata]:
        cursor = store.conn.execute("SELECT * FROM rkm_metadata")
        return [
            RepositoryMetadata(
                id=row["id"],
                repository_uuid=row["repository_uuid"],
                name=row["name"],
                root_path=row["root_path"],
                language=row["language"],
                size=row["size"],
                rkm_version=row["rkm_version"],
                minimum_reader_version=row["minimum_reader_version"],
                maximum_writer_version=row["maximum_writer_version"],
                latest_analysis_run_id=row["latest_analysis_run_id"]
            )
            for row in cursor
        ]

    @staticmethod
    def get_repository(store: RepositoryStore, repo_id: int) -> Optional[RepositoryMetadata]:
        row = store.conn.execute("SELECT * FROM rkm_metadata WHERE id = ?", (repo_id,)).fetchone()
        if not row:
            return None
        return RepositoryMetadata(
            id=row["id"],
            repository_uuid=row["repository_uuid"],
            name=row["name"],
            root_path=row["root_path"],
            language=row["language"],
            size=row["size"],
            rkm_version=row["rkm_version"],
            minimum_reader_version=row["minimum_reader_version"],
            maximum_writer_version=row["maximum_writer_version"],
            latest_analysis_run_id=row["latest_analysis_run_id"]
        )

    @staticmethod
    def init_repository(store: RepositoryStore, name: str, root_path: str, repo_uuid: str) -> int:
        norm_path = os.path.normpath(root_path).replace("\\", "/")
        existing = store.conn.execute("SELECT id FROM rkm_metadata WHERE repository_uuid = ?", (repo_uuid,)).fetchone()
        if existing:
            return existing["id"]
        with store.transaction():
            meta = RepositoryMetadata(
                id=None,
                repository_uuid=repo_uuid,
                name=name,
                root_path=norm_path,
                language="Python",
                size=0,
                rkm_version="1.3.0",
                minimum_reader_version="1.3.0",
                maximum_writer_version="1.x",
                latest_analysis_run_id=None
            )
            return store.save_metadata(meta)
