from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable
from uuid import uuid4

import psycopg

from .config import get_settings
from .models import CompanyProfileBase, CompanyProfileDB

settings = get_settings()


@contextmanager
def get_conn():
    conn = psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        autocommit=True,
    )
    try:
        yield conn
    finally:
        conn.close()


def ensure_tables() -> None:
    create_sql = """
    CREATE TABLE IF NOT EXISTS companies (
        id UUID PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        profile_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    );
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)


def map_row_to_profile(row: Iterable[Any]) -> CompanyProfileDB:
    (
        company_id,
        name,
        description,
        profile_json,
        created_at,
        updated_at,
    ) = row
    base_profile = CompanyProfileBase(**profile_json)
    return CompanyProfileDB(
        id=company_id,
        name=name,
        description=description,
        regions=base_profile.regions,
        min_contract_price=base_profile.min_contract_price,
        max_contract_price=base_profile.max_contract_price,
        industries=base_profile.industries,
        resources=base_profile.resources,
        risk_tolerance=base_profile.risk_tolerance,
        okpd2_codes=base_profile.okpd2_codes,
        created_at=created_at,
        updated_at=updated_at,
    )


def insert_company_profile(profile: CompanyProfileBase) -> CompanyProfileDB:
    now = datetime.utcnow()
    company_id = uuid4()
    profile_dict = json.loads(profile.model_dump_json())

    sql = """
    INSERT INTO companies (id, name, description, profile_json, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, name, description, profile_json, created_at, updated_at;
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    company_id,
                    profile.name,
                    profile.description,
                    json.dumps(profile_dict),
                    now,
                    now,
                ),
            )
            row = cur.fetchone()
            return map_row_to_profile(row)


def fetch_company_profile(company_id: str) -> CompanyProfileDB:
    sql = """
    SELECT id, name, description, profile_json, created_at, updated_at
    FROM companies
    WHERE id = %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (company_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Company not found")
            return map_row_to_profile(row)


def fetch_company_profiles(query: str | None, limit: int, offset: int) -> list[CompanyProfileDB]:
    sql = """
    SELECT id, name, description, profile_json, created_at, updated_at
    FROM companies
    WHERE (%s IS NULL OR name ILIKE %s OR description ILIKE %s)
    ORDER BY created_at DESC
    LIMIT %s OFFSET %s;
    """
    like = f"%{query}%" if query else None
    params = (query, like, like, limit, offset)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [map_row_to_profile(row) for row in rows]
