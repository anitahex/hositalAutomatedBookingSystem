import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No SQLAlchemy ORM models — migrations use raw SQL via op.execute()
target_metadata = None


def get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # Alembic auto-creates alembic_version with version_num VARCHAR(32) if the
        # table doesn't exist yet, but this repo's revision ids (e.g.
        # "0002_add_document_original_filename") are longer than that — a fresh
        # install would fail past the first migration. Pre-create the table with a
        # wider column so Alembic just uses it as-is (it only creates the table when
        # missing, never alters an existing one's width).
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(255) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        )
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
