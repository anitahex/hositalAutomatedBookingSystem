from app.db.hydrate_vectors import hydrate_vector_db
from app.db.ingest_relational import ingest_relational_data


def rebuild_database():
    ingest_relational_data()
    hydrate_vector_db()


if __name__ == "__main__":
    rebuild_database()
