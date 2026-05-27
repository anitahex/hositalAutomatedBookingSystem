import pandas as pd
from psycopg2.extras import execute_values

from app.db.connection import connect_db


def ingest_relational_data():
    doctors = pd.read_csv("doctors_roster.csv")
    slots = pd.read_csv("appointment_slots.csv")

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE EXTENSION IF NOT EXISTS pgcrypto;

                DROP TABLE IF EXISTS appointment_slots;
                DROP TABLE IF EXISTS doctors;

                CREATE TABLE doctors (
                    doctor_id UUID PRIMARY KEY,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    experience_years INTEGER NOT NULL
                );

                CREATE TABLE appointment_slots (
                    slot_id UUID PRIMARY KEY,
                    doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    is_booked BOOLEAN NOT NULL DEFAULT FALSE,
                    booked_by_patient_id TEXT,
                    UNIQUE (doctor_id, start_time)
                );

                CREATE INDEX idx_doctors_department ON doctors(department);
                CREATE INDEX idx_slots_available ON appointment_slots(start_time)
                    WHERE is_booked = FALSE;
                """
            )

            execute_values(
                cur,
                """
                INSERT INTO doctors (name, department, experience_years, doctor_id)
                VALUES %s
                """,
                list(
                    doctors[
                        ["name", "department", "experience_years", "doctor_id"]
                    ].itertuples(index=False, name=None)
                ),
            )

            execute_values(
                cur,
                """
                INSERT INTO appointment_slots (
                    slot_id,
                    doctor_id,
                    start_time,
                    end_time,
                    is_booked,
                    booked_by_patient_id
                )
                VALUES %s
                """,
                list(
                    slots[
                        [
                            "slot_id",
                            "doctor_id",
                            "start_time",
                            "end_time",
                            "is_booked",
                            "booked_by_patient_id",
                        ]
                    ].where(pd.notna(slots), None).itertuples(index=False, name=None)
                ),
            )

        conn.commit()

    print(f"Inserted {len(doctors)} doctors and {len(slots)} appointment slots.")
