from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

DATABASE_URL = settings.DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # Ensure models are registered
    from backend import models
    # Automatically create tables for SQLite MVP
    Base.metadata.create_all(bind=engine)

    # Simple migration for DocumentChunk columns (Option B)
    from sqlalchemy import text
    with engine.begin() as conn:
        try:
            # Users plan migration
            result_users = conn.execute(text("PRAGMA table_info(users)"))
            existing_users_columns = [row[1] for row in result_users.fetchall()]
            if "plan" not in existing_users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN plan VARCHAR DEFAULT 'free'"))

            result = conn.execute(text("PRAGMA table_info(document_chunks)"))
            existing_columns = [row[1] for row in result.fetchall()]
            
            columns_to_add = [
                ("embedding_json", "TEXT"),
                ("embedding_provider", "VARCHAR"),
                ("embedding_model", "VARCHAR"),
                ("embedding_dimension", "INTEGER"),
                ("embedding_created_at", "DATETIME")
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    conn.execute(text(f"ALTER TABLE document_chunks ADD COLUMN {col_name} {col_type}"))
            
            # Simple migration for CourseFile columns
            result_cf = conn.execute(text("PRAGMA table_info(course_files)"))
            existing_cf_columns = [row[1] for row in result_cf.fetchall()]
            
            cf_columns_to_add = [
                ("processing_status", "VARCHAR DEFAULT 'uploaded'"),
                ("extraction_status", "VARCHAR DEFAULT 'pending'"),
                ("embedding_status", "VARCHAR DEFAULT 'pending'"),
                ("chunk_count", "INTEGER DEFAULT 0"),
                ("embedded_count", "INTEGER DEFAULT 0"),
                ("processing_error", "TEXT"),
                ("processed_at", "DATETIME")
            ]
            
            for col_name, col_type in cf_columns_to_add:
                if col_name not in existing_cf_columns:
                    conn.execute(text(f"ALTER TABLE course_files ADD COLUMN {col_name} {col_type}"))

            # Simple migration for LMSConnection columns
            result_lms = conn.execute(text("PRAGMA table_info(lms_connections)"))
            existing_lms_columns = [row[1] for row in result_lms.fetchall()]
            
            lms_columns_to_add = [
                ("external_user_id", "VARCHAR"),
                ("token_expires_at", "DATETIME"),
                ("scopes", "VARCHAR"),
                ("status", "VARCHAR DEFAULT 'disconnected'"),
                ("updated_at", "DATETIME")
            ]
            
            for col_name, col_type in lms_columns_to_add:
                if col_name not in existing_lms_columns:
                    conn.execute(text(f"ALTER TABLE lms_connections ADD COLUMN {col_name} {col_type}"))

            # Simple migration for Assignment columns
            result_assign = conn.execute(text("PRAGMA table_info(assignments)"))
            existing_assign_columns = [row[1] for row in result_assign.fetchall()]
            
            assign_columns_to_add = [
                ("external_provider", "VARCHAR"),
                ("external_id", "VARCHAR"),
                ("external_course_id", "VARCHAR")
            ]
            
            for col_name, col_type in assign_columns_to_add:
                if col_name not in existing_assign_columns:
                    conn.execute(text(f"ALTER TABLE assignments ADD COLUMN {col_name} {col_type}"))
        except Exception as e:
            print(f"Database migration warning: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
