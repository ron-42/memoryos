from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
import sqlite3
from typing import Any

from app.core.config import get_settings


SCHEMA_STATEMENTS = [
    """
    create table if not exists profiles (
        id text primary key,
        email text,
        total_xp integer not null default 0,
        current_streak integer not null default 0,
        longest_streak integer not null default 0,
        last_capture_date text,
        created_at text not null,
        updated_at text not null
    )
    """,
    """
    create table if not exists memories (
        id text primary key,
        user_id text not null,
        source_type text not null,
        source_url text,
        source_title text,
        raw_content text not null,
        title text,
        summary text,
        key_concepts_json text not null,
        topic_tags_json text not null,
        content_type text,
        importance_score real,
        estimated_read_time integer,
        embedding_json text not null,
        xp_awarded integer not null default 0,
        created_at text not null
    )
    """,
    """
    create table if not exists chunks (
        id text primary key,
        memory_id text not null,
        user_id text not null,
        chunk_index integer not null,
        chunk_text text not null,
        embedding_json text not null,
        created_at text not null
    )
    """,
    """
    create table if not exists topics (
        id text primary key,
        user_id text not null,
        name text not null,
        memory_count integer not null default 0,
        total_xp integer not null default 0,
        level integer not null default 1,
        color text,
        created_at text not null,
        updated_at text not null,
        unique(user_id, name)
    )
    """,
    """
    create table if not exists connections (
        id text primary key,
        user_id text not null,
        memory_a text not null,
        memory_b text not null,
        similarity_score real not null,
        connection_label text,
        discovered_at text not null,
        unique(user_id, memory_a, memory_b)
    )
    """,
    """
    create table if not exists xp_events (
        id text primary key,
        user_id text not null,
        event_type text not null,
        xp_amount integer not null,
        metadata_json text not null,
        created_at text not null
    )
    """,
    "create index if not exists idx_memories_user_created_at on memories(user_id, created_at desc)",
    "create index if not exists idx_chunks_user_memory on chunks(user_id, memory_id, chunk_index)",
    "create index if not exists idx_chunks_user_text on chunks(user_id, chunk_text)",
    "create index if not exists idx_topics_user_total_xp on topics(user_id, total_xp desc)",
    "create index if not exists idx_connections_user_discovered_at on connections(user_id, discovered_at desc)",
    "create index if not exists idx_xp_events_user_created_at on xp_events(user_id, created_at desc)",
]


def _db_path() -> Path:
    settings = get_settings()
    path = Path(settings.database_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("pragma journal_mode = wal")
    connection.execute("pragma foreign_keys = on")
    return connection


async def initialize_database() -> None:
    await asyncio.to_thread(_initialize_database_sync)


def _initialize_database_sync() -> None:
    with _connect() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


async def fetch_all(query: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    return await asyncio.to_thread(_fetch_all_sync, query, tuple(params))


def _fetch_all_sync(query: str, params: tuple[Any, ...]) -> list[sqlite3.Row]:
    with _connect() as connection:
        cursor = connection.execute(query, params)
        return cursor.fetchall()


async def fetch_one(query: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
    return await asyncio.to_thread(_fetch_one_sync, query, tuple(params))


def _fetch_one_sync(query: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
    with _connect() as connection:
        cursor = connection.execute(query, params)
        return cursor.fetchone()


async def execute(query: str, params: Sequence[Any] = ()) -> None:
    await asyncio.to_thread(_execute_sync, query, tuple(params))


def _execute_sync(query: str, params: tuple[Any, ...]) -> None:
    with _connect() as connection:
        connection.execute(query, params)
        connection.commit()


async def executemany(query: str, rows: Sequence[Sequence[Any]]) -> None:
    await asyncio.to_thread(_executemany_sync, query, [tuple(row) for row in rows])


def _executemany_sync(query: str, rows: list[tuple[Any, ...]]) -> None:
    with _connect() as connection:
        connection.executemany(query, rows)
        connection.commit()


async def run_in_transaction(callback: Any) -> Any:
    return await asyncio.to_thread(_run_in_transaction_sync, callback)


def _run_in_transaction_sync(callback: Any) -> Any:
    with _connect() as connection:
        result = callback(connection)
        connection.commit()
        return result
