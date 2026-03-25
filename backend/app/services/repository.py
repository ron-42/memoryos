from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import logging
import sqlite3
from typing import Any
from uuid import UUID, uuid4

from app.core.security import UserContext
from app.db.pinecone import get_pinecone_client
from app.db.sqlite import fetch_all, fetch_one, run_in_transaction
from app.models.capture import CapturedContent, EnrichmentPayload, PersistedCapture
from app.models.memory import MemoryChunk, MemoryConnection, MemoryDetail, MemorySummary
from app.models.topic import TopicAggregate, TopicProgress
from app.services.gamification import xp_for_source
from app.services.topics import color_for_topic, level_for_xp

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RepositoryCapturePayload:
    content: CapturedContent
    enrichment: EnrichmentPayload
    chunks: list[str]
    chunk_embeddings: list[list[float]]
    document_embedding: list[float]


@dataclass(slots=True)
class ProfileState:
    total_xp: int
    current_streak: int
    longest_streak: int
    last_capture_date: date | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _json_dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def _json_load_list(value: str | None) -> list[Any]:
    if not value:
        return []
    loaded = json.loads(value)
    return loaded if isinstance(loaded, list) else []


def _memory_summary_from_row(row: sqlite3.Row) -> MemorySummary:
    return MemorySummary.model_validate(
        {
            "id": row["id"],
            "title": row["title"],
            "source_type": row["source_type"],
            "source_url": row["source_url"],
            "topic_tags": _json_load_list(row["topic_tags_json"]),
            "content_type": row["content_type"],
            "importance_score": row["importance_score"],
            "created_at": row["created_at"],
        }
    )


def _profile_state_from_row(row: sqlite3.Row | None) -> ProfileState:
    if row is None:
        return ProfileState(total_xp=0, current_streak=0, longest_streak=0, last_capture_date=None)
    last_capture = row["last_capture_date"]
    return ProfileState(
        total_xp=int(row["total_xp"] or 0),
        current_streak=int(row["current_streak"] or 0),
        longest_streak=int(row["longest_streak"] or 0),
        last_capture_date=date.fromisoformat(last_capture) if last_capture else None,
    )


class MemoryRepository:
    async def list_user_ids(self, limit: int = 100) -> list[UUID]:
        rows = await fetch_all("select id from profiles order by created_at asc limit ?", (limit,))
        return [UUID(row["id"]) for row in rows]

    async def list_memories(
        self,
        user_id: UUID,
        limit: int = 20,
        cursor: str | None = None,
        topic: str | None = None,
        content_type: str | None = None,
        query: str | None = None,
    ) -> tuple[list[MemorySummary], str | None]:
        clauses = ["user_id = ?"]
        params: list[Any] = [str(user_id)]

        if cursor:
            clauses.append("created_at < ?")
            params.append(cursor)
        if topic:
            clauses.append("topic_tags_json like ?")
            params.append(f'%"{topic}"%')
        if content_type:
            clauses.append("content_type = ?")
            params.append(content_type)
        if query:
            clauses.append("coalesce(title, '') like ?")
            params.append(f"%{query}%")

        rows = await fetch_all(
            f"""
            select id, title, source_type, source_url, topic_tags_json, content_type, importance_score, created_at
            from memories
            where {" and ".join(clauses)}
            order by created_at desc
            limit ?
            """,
            (*params, limit + 1),
        )
        next_cursor = rows[limit]["created_at"] if len(rows) > limit else None
        return [_memory_summary_from_row(row) for row in rows[:limit]], next_cursor

    async def list_memories_for_topic_rebuild(self, user_id: UUID, limit: int = 1000) -> list[dict[str, Any]]:
        rows = await fetch_all(
            """
            select topic_tags_json, xp_awarded
            from memories
            where user_id = ?
            order by created_at desc
            limit ?
            """,
            (str(user_id), limit),
        )
        return [
            {
                "topic_tags": _json_load_list(row["topic_tags_json"]),
                "xp_awarded": int(row["xp_awarded"] or 0),
            }
            for row in rows
        ]

    async def list_memory_ids_without_connections(self, user_id: UUID, limit: int = 25) -> list[UUID]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        rows = await fetch_all(
            """
            select id
            from memories
            where user_id = ?
              and created_at <= ?
              and id not in (
                select memory_a from connections where user_id = ?
                union
                select memory_b from connections where user_id = ?
              )
            order by created_at desc
            limit ?
            """,
            (str(user_id), cutoff, str(user_id), str(user_id), limit),
        )
        return [UUID(row["id"]) for row in rows]

    async def get_memory_detail(self, user_id: UUID, memory_id: UUID) -> MemoryDetail | None:
        row = await fetch_one(
            """
            select *
            from memories
            where user_id = ? and id = ?
            limit 1
            """,
            (str(user_id), str(memory_id)),
        )
        if row is None:
            return None

        chunk_rows = await fetch_all(
            """
            select id, chunk_index, chunk_text
            from chunks
            where user_id = ? and memory_id = ?
            order by chunk_index asc
            limit 8
            """,
            (str(user_id), str(memory_id)),
        )
        connection_rows = await fetch_all(
            """
            select id, memory_a, memory_b, similarity_score, connection_label
            from connections
            where user_id = ?
              and (memory_a = ? or memory_b = ?)
            order by discovered_at desc
            limit 10
            """,
            (str(user_id), str(memory_id), str(memory_id)),
        )
        related_ids = {
            row["memory_b"] if row["memory_a"] == str(memory_id) else row["memory_a"]
            for row in connection_rows
        }
        related_map = await self.get_memories_by_ids(user_id=user_id, memory_ids=[UUID(item) for item in related_ids]) if related_ids else {}

        return MemoryDetail(
            id=UUID(row["id"]),
            title=row["title"],
            source_type=row["source_type"],
            source_url=row["source_url"],
            source_title=row["source_title"],
            summary=row["summary"],
            raw_content=row["raw_content"],
            key_concepts=_json_load_list(row["key_concepts_json"]),
            topic_tags=_json_load_list(row["topic_tags_json"]),
            content_type=row["content_type"],
            importance_score=row["importance_score"],
            estimated_read_time=row["estimated_read_time"],
            xp_awarded=int(row["xp_awarded"] or 0),
            created_at=row["created_at"],
            connections=[
                MemoryConnection(
                    id=UUID(item["id"]),
                    memory_id=UUID(item["memory_b"] if item["memory_a"] == str(memory_id) else item["memory_a"]),
                    title=related_map.get(item["memory_b"] if item["memory_a"] == str(memory_id) else item["memory_a"], {}).get("title"),
                    similarity_score=float(item["similarity_score"]),
                    connection_label=item["connection_label"],
                )
                for item in connection_rows
            ],
            chunks=[MemoryChunk.model_validate(dict(chunk)) for chunk in chunk_rows],
        )

    async def get_memories_by_ids(self, user_id: UUID, memory_ids: list[UUID]) -> dict[str, dict[str, Any]]:
        if not memory_ids:
            return {}
        placeholders = ",".join("?" for _ in memory_ids)
        rows = await fetch_all(
            f"""
            select id, title, source_url, summary, topic_tags_json, embedding_json, source_type
            from memories
            where user_id = ?
              and id in ({placeholders})
            """,
            (str(user_id), *[str(memory_id) for memory_id in memory_ids]),
        )
        return {
            row["id"]: {
                "id": row["id"],
                "title": row["title"],
                "source_url": row["source_url"],
                "summary": row["summary"],
                "topic_tags": _json_load_list(row["topic_tags_json"]),
                "embedding": _json_load_list(row["embedding_json"]),
                "source_type": row["source_type"],
            }
            for row in rows
        }

    async def get_chunk_keyword_matches(self, user_id: UUID, query: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = await fetch_all(
            """
            select id, memory_id, chunk_text
            from chunks
            where user_id = ?
              and chunk_text like ?
            limit ?
            """,
            (str(user_id), f"%{query}%", limit),
        )
        return [dict(row) for row in rows]

    async def get_chunks_for_memory_ids(self, user_id: UUID, memory_ids: list[UUID], limit: int = 20) -> list[dict[str, Any]]:
        if not memory_ids:
            return []
        placeholders = ",".join("?" for _ in memory_ids)
        rows = await fetch_all(
            f"""
            select id, memory_id, chunk_text, chunk_index
            from chunks
            where user_id = ?
              and memory_id in ({placeholders})
            order by chunk_index asc
            limit ?
            """,
            (str(user_id), *[str(memory_id) for memory_id in memory_ids], limit),
        )
        return [dict(row) for row in rows]

    async def get_profile_stats(self, user_id: UUID) -> dict[str, Any]:
        row = await fetch_one(
            """
            select total_xp, current_streak, longest_streak, last_capture_date
            from profiles
            where id = ?
            limit 1
            """,
            (str(user_id),),
        )
        if row is None:
            return {"total_xp": 0, "current_streak": 0, "longest_streak": 0, "last_capture_date": None}
        return dict(row)

    async def get_topics_progress(self, user_id: UUID, limit: int = 10) -> list[TopicProgress]:
        rows = await fetch_all(
            """
            select id, name, memory_count, total_xp, level, color
            from topics
            where user_id = ?
            order by total_xp desc, name asc
            limit ?
            """,
            (str(user_id), limit),
        )
        return [TopicProgress.model_validate(dict(row)) for row in rows]

    async def sync_topics_for_user(self, user_id: UUID, aggregates: list[TopicAggregate]) -> None:
        aggregate_names = {item.name for item in aggregates}

        def _sync(connection: sqlite3.Connection) -> None:
            now = _now_iso()
            existing_rows = connection.execute("select name from topics where user_id = ?", (str(user_id),)).fetchall()
            existing_names = {row["name"] for row in existing_rows}

            for aggregate in aggregates:
                connection.execute(
                    """
                    insert into topics (id, user_id, name, memory_count, total_xp, level, color, created_at, updated_at)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(user_id, name) do update set
                        memory_count = excluded.memory_count,
                        total_xp = excluded.total_xp,
                        level = excluded.level,
                        color = excluded.color,
                        updated_at = excluded.updated_at
                    """,
                    (
                        str(uuid4()),
                        str(user_id),
                        aggregate.name,
                        aggregate.memory_count,
                        aggregate.total_xp,
                        aggregate.level,
                        aggregate.color,
                        now,
                        now,
                    ),
                )

            for stale_name in existing_names - aggregate_names:
                connection.execute(
                    """
                    update topics
                    set memory_count = 0, total_xp = 0, level = 1, color = ?, updated_at = ?
                    where user_id = ? and name = ?
                    """,
                    (color_for_topic(stale_name), now, str(user_id), stale_name),
                )

        await run_in_transaction(_sync)

    async def get_xp_events_since(self, user_id: UUID, iso_timestamp: str) -> list[dict[str, Any]]:
        rows = await fetch_all(
            """
            select xp_amount, created_at
            from xp_events
            where user_id = ?
              and created_at >= ?
            """,
            (str(user_id), iso_timestamp),
        )
        return [dict(row) for row in rows]

    async def get_recent_connections(self, user_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
        rows = await fetch_all(
            """
            select id, memory_a, memory_b, similarity_score, connection_label, discovered_at
            from connections
            where user_id = ?
            order by discovered_at desc
            limit ?
            """,
            (str(user_id), limit),
        )
        return [dict(row) for row in rows]

    async def get_all_connections(self, user_id: UUID, limit: int = 200) -> list[dict[str, Any]]:
        rows = await fetch_all(
            """
            select id, memory_a, memory_b, similarity_score, connection_label, discovered_at
            from connections
            where user_id = ?
            order by discovered_at desc
            limit ?
            """,
            (str(user_id), limit),
        )
        return [dict(row) for row in rows]

    async def get_memory_similarity_payload(self, user_id: UUID, memory_id: UUID) -> dict[str, Any] | None:
        row = await fetch_one(
            """
            select id, title, summary, source_url, topic_tags_json, embedding_json, source_type
            from memories
            where user_id = ? and id = ?
            limit 1
            """,
            (str(user_id), str(memory_id)),
        )
        if row is None:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "summary": row["summary"],
            "source_url": row["source_url"],
            "topic_tags": _json_load_list(row["topic_tags_json"]),
            "embedding": _json_load_list(row["embedding_json"]),
            "source_type": row["source_type"],
            "user_id": str(user_id),
        }

    async def get_connection_candidates(self, user_id: UUID, exclude_memory_id: UUID, limit: int = 50) -> list[dict[str, Any]]:
        rows = await fetch_all(
            """
            select id, title, summary, source_url, topic_tags_json, embedding_json, source_type
            from memories
            where user_id = ?
              and id != ?
            order by created_at desc
            limit ?
            """,
            (str(user_id), str(exclude_memory_id), limit),
        )
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "source_url": row["source_url"],
                "topic_tags": _json_load_list(row["topic_tags_json"]),
                "embedding": _json_load_list(row["embedding_json"]),
                "source_type": row["source_type"],
                "user_id": str(user_id),
            }
            for row in rows
        ]

    async def get_connected_memory_ids(self, user_id: UUID, memory_id: UUID) -> set[str]:
        rows = await fetch_all(
            """
            select memory_a, memory_b
            from connections
            where user_id = ?
              and (memory_a = ? or memory_b = ?)
            """,
            (str(user_id), str(memory_id), str(memory_id)),
        )
        related: set[str] = set()
        for row in rows:
            related.add(row["memory_b"] if row["memory_a"] == str(memory_id) else row["memory_a"])
        return related

    async def create_connection(
        self,
        user_id: UUID,
        memory_a: UUID,
        memory_b: UUID,
        similarity_score: float,
        connection_label: str | None,
    ) -> dict[str, Any] | None:
        first, second = canonical_memory_pair(memory_a, memory_b)
        connection_id = str(uuid4())
        discovered_at = _now_iso()

        def _create(connection: sqlite3.Connection) -> dict[str, Any] | None:
            existing = connection.execute(
                """
                select id, memory_a, memory_b, similarity_score, connection_label, discovered_at
                from connections
                where user_id = ? and memory_a = ? and memory_b = ?
                limit 1
                """,
                (str(user_id), str(first), str(second)),
            ).fetchone()
            if existing is not None:
                return dict(existing)

            connection.execute(
                """
                insert or ignore into connections (
                    id, user_id, memory_a, memory_b, similarity_score, connection_label, discovered_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (connection_id, str(user_id), str(first), str(second), similarity_score, connection_label, discovered_at),
            )
            inserted = connection.execute(
                """
                select id, memory_a, memory_b, similarity_score, connection_label, discovered_at
                from connections
                where user_id = ? and memory_a = ? and memory_b = ?
                limit 1
                """,
                (str(user_id), str(first), str(second)),
            ).fetchone()
            return dict(inserted) if inserted is not None else None

        return await run_in_transaction(_create)

    async def store_capture(self, user: UserContext, payload: RepositoryCapturePayload) -> PersistedCapture:
        memory_id = uuid4()
        xp_awarded = xp_for_source(payload.content.source_type)
        today = _today_utc()
        now = _now_iso()

        def _store(connection: sqlite3.Connection) -> None:
            logger.info("store capture ensure profile user_id=%s", user.user_id)
            profile = self._ensure_profile(connection=connection, user=user, now=now)
            profile = self._advance_streak(profile, today=today)

            logger.info("store capture insert memory user_id=%s memory_id=%s source_type=%s", user.user_id, memory_id, payload.content.source_type)
            connection.execute(
                """
                insert into memories (
                    id, user_id, source_type, source_url, source_title, raw_content, title, summary,
                    key_concepts_json, topic_tags_json, content_type, importance_score, estimated_read_time,
                    embedding_json, xp_awarded, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(memory_id),
                    str(user.user_id),
                    payload.content.source_type,
                    payload.content.source_url,
                    payload.content.source_title,
                    payload.content.raw_content,
                    payload.enrichment.title,
                    payload.enrichment.summary,
                    _json_dump(payload.enrichment.key_concepts),
                    _json_dump(payload.enrichment.topic_tags),
                    payload.enrichment.content_type,
                    payload.enrichment.importance_score,
                    payload.enrichment.estimated_read_time,
                    _json_dump(payload.document_embedding),
                    xp_awarded,
                    now,
                ),
            )

            chunk_rows: list[dict[str, Any]] = []
            for index, chunk_text in enumerate(payload.chunks):
                chunk_id = str(uuid4())
                embedding = payload.chunk_embeddings[index]
                chunk_rows.append(
                    {
                        "id": chunk_id,
                        "memory_id": str(memory_id),
                        "user_id": str(user.user_id),
                        "chunk_index": index,
                        "chunk_text": chunk_text,
                        "embedding": embedding,
                    }
                )
                connection.execute(
                    """
                    insert into chunks (id, memory_id, user_id, chunk_index, chunk_text, embedding_json, created_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (chunk_id, str(memory_id), str(user.user_id), index, chunk_text, _json_dump(embedding), now),
                )

            logger.info("store capture update profile user_id=%s memory_id=%s xp=%s", user.user_id, memory_id, xp_awarded)
            self._update_profile(connection=connection, user_id=user.user_id, profile=profile, xp_awarded=xp_awarded, today=today, now=now)
            logger.info("store capture update topics user_id=%s memory_id=%s topics=%s", user.user_id, memory_id, len(payload.enrichment.topic_tags))
            self._upsert_topics(connection=connection, user_id=user.user_id, topic_tags=payload.enrichment.topic_tags, xp_awarded=xp_awarded, now=now)
            logger.info("store capture write xp event user_id=%s memory_id=%s", user.user_id, memory_id)
            self._log_xp_event(connection=connection, user_id=user.user_id, source_type=payload.content.source_type, memory_id=memory_id, xp_awarded=xp_awarded, now=now)

        try:
            await run_in_transaction(_store)
        except Exception:
            logger.exception("store capture failed user_id=%s memory_id=%s", user.user_id, memory_id)
            raise

        chunk_rows_for_vectors = [
            {
                "id": str(uuid4()),
                "user_id": str(user.user_id),
                "chunk_text": chunk_text,
                "embedding": payload.chunk_embeddings[index],
            }
            for index, chunk_text in enumerate(payload.chunks)
        ]
        stored_chunks = await fetch_all(
            """
            select id, chunk_text, embedding_json
            from chunks
            where memory_id = ?
            order by chunk_index asc
            """,
            (str(memory_id),),
        )
        if stored_chunks:
            chunk_rows_for_vectors = [
                {
                    "id": row["id"],
                    "user_id": str(user.user_id),
                    "chunk_text": row["chunk_text"],
                    "embedding": _json_load_list(row["embedding_json"]),
                }
                for row in stored_chunks
            ]
        await self._upsert_chunk_vectors(
            user_id=user.user_id,
            memory_id=memory_id,
            source_type=payload.content.source_type,
            source_url=payload.content.source_url,
            title=payload.enrichment.title,
            chunk_rows=chunk_rows_for_vectors,
        )
        await self._upsert_memory_vector(
            user_id=user.user_id,
            memory_id=memory_id,
            source_type=payload.content.source_type,
            source_url=payload.content.source_url,
            title=payload.enrichment.title,
            summary=payload.enrichment.summary,
            topic_tags=payload.enrichment.topic_tags,
            embedding=payload.document_embedding,
        )

        return PersistedCapture(
            memory_id=memory_id,
            xp_awarded=xp_awarded,
            topics_updated=payload.enrichment.topic_tags,
            connections_found=0,
        )

    def _ensure_profile(self, connection: sqlite3.Connection, user: UserContext, now: str) -> ProfileState:
        connection.execute(
            """
            insert into profiles (id, email, created_at, updated_at)
            values (?, ?, ?, ?)
            on conflict(id) do update set
                email = excluded.email,
                updated_at = excluded.updated_at
            """,
            (str(user.user_id), user.email, now, now),
        )
        row = connection.execute(
            """
            select total_xp, current_streak, longest_streak, last_capture_date
            from profiles
            where id = ?
            limit 1
            """,
            (str(user.user_id),),
        ).fetchone()
        return _profile_state_from_row(row)

    def _advance_streak(self, profile: ProfileState, today: date) -> ProfileState:
        if profile.last_capture_date == today:
            return profile
        if profile.last_capture_date is None:
            current_streak = 1
        else:
            delta_days = (today - profile.last_capture_date).days
            current_streak = profile.current_streak + 1 if delta_days == 1 else 1
        return ProfileState(
            total_xp=profile.total_xp,
            current_streak=current_streak,
            longest_streak=max(profile.longest_streak, current_streak),
            last_capture_date=today,
        )

    def _update_profile(
        self,
        connection: sqlite3.Connection,
        user_id: UUID,
        profile: ProfileState,
        xp_awarded: int,
        today: date,
        now: str,
    ) -> None:
        connection.execute(
            """
            update profiles
            set total_xp = ?,
                current_streak = ?,
                longest_streak = ?,
                last_capture_date = ?,
                updated_at = ?
            where id = ?
            """,
            (
                profile.total_xp + xp_awarded,
                profile.current_streak,
                profile.longest_streak,
                today.isoformat(),
                now,
                str(user_id),
            ),
        )

    def _upsert_topics(
        self,
        connection: sqlite3.Connection,
        user_id: UUID,
        topic_tags: list[str],
        xp_awarded: int,
        now: str,
    ) -> None:
        if not topic_tags:
            return
        topic_xp = max(1, xp_awarded // len(topic_tags))
        for topic_name in topic_tags:
            row = connection.execute(
                """
                select memory_count, total_xp
                from topics
                where user_id = ? and name = ?
                limit 1
                """,
                (str(user_id), topic_name),
            ).fetchone()
            memory_count = (int(row["memory_count"] or 0) + 1) if row else 1
            total_xp = (int(row["total_xp"] or 0) + topic_xp) if row else topic_xp
            connection.execute(
                """
                insert into topics (id, user_id, name, memory_count, total_xp, level, color, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(user_id, name) do update set
                    memory_count = excluded.memory_count,
                    total_xp = excluded.total_xp,
                    level = excluded.level,
                    color = excluded.color,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    str(user_id),
                    topic_name,
                    memory_count,
                    total_xp,
                    level_for_xp(total_xp),
                    color_for_topic(topic_name),
                    now,
                    now,
                ),
            )

    def _log_xp_event(
        self,
        connection: sqlite3.Connection,
        user_id: UUID,
        source_type: str,
        memory_id: UUID,
        xp_awarded: int,
        now: str,
    ) -> None:
        connection.execute(
            """
            insert into xp_events (id, user_id, event_type, xp_amount, metadata_json, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                str(user_id),
                f"capture_{source_type}",
                xp_awarded,
                _json_dump({"memory_id": str(memory_id)}),
                now,
            ),
        )

    async def _upsert_chunk_vectors(
        self,
        user_id: UUID,
        memory_id: UUID,
        source_type: str,
        source_url: str | None,
        title: str | None,
        chunk_rows: list[dict[str, Any]],
    ) -> None:
        pinecone = await get_pinecone_client()
        if pinecone is None:
            return
        try:
            vectors = [
                {
                    "id": f"chunk:{row['id']}",
                    "values": row["embedding"],
                    "metadata": {
                        "record_type": "chunk",
                        "user_id": row.get("user_id") or str(user_id),
                        "memory_id": str(memory_id),
                        "chunk_id": row["id"],
                        "source_type": source_type,
                        "source_url": source_url or "",
                        "title": title or "",
                        "chunk_text": row["chunk_text"][:1500],
                    },
                }
                for row in chunk_rows
                if row.get("embedding")
            ]
            if vectors:
                await pinecone.upsert(vectors)
        except Exception:
            logger.exception("pinecone chunk upsert failed memory_id=%s", memory_id)
        finally:
            await pinecone.aclose()

    async def _upsert_memory_vector(
        self,
        user_id: UUID,
        memory_id: UUID,
        source_type: str,
        source_url: str | None,
        title: str | None,
        summary: str,
        topic_tags: list[str],
        embedding: list[float],
    ) -> None:
        pinecone = await get_pinecone_client()
        if pinecone is None or not embedding:
            return
        try:
            await pinecone.upsert(
                [
                    {
                        "id": f"memory:{memory_id}",
                        "values": embedding,
                        "metadata": {
                            "record_type": "memory",
                            "user_id": str(user_id),
                            "memory_id": str(memory_id),
                            "source_type": source_type,
                            "source_url": source_url or "",
                            "title": title or "",
                            "summary": summary[:1500],
                            "topic_tags": topic_tags,
                        },
                    }
                ]
            )
        except Exception:
            logger.exception("pinecone memory upsert failed memory_id=%s", memory_id)
        finally:
            await pinecone.aclose()


def canonical_memory_pair(memory_a: UUID, memory_b: UUID) -> tuple[UUID, UUID]:
    return (memory_a, memory_b) if str(memory_a) < str(memory_b) else (memory_b, memory_a)
