import pandas as pd
from psycopg2.extras import execute_values

from app.db.connection import connect_db
from app.services.appointments import ensure_booking_schema


def ingest_relational_data():
    doctors = pd.read_csv("doctors_roster.csv")
    slots = pd.read_csv("appointment_slots.csv")

    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE EXTENSION IF NOT EXISTS pgcrypto;
                """
            )

            execute_values(
                cur,
                """
                INSERT INTO doctors (name, department, experience_years, doctor_id)
                VALUES %s
                ON CONFLICT (doctor_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    department = EXCLUDED.department,
                    experience_years = EXCLUDED.experience_years,
                    updated_at = NOW()
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
                ON CONFLICT (slot_id)
                DO UPDATE SET
                    doctor_id = EXCLUDED.doctor_id,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    is_booked = EXCLUDED.is_booked,
                    booked_by_patient_id = EXCLUDED.booked_by_patient_id,
                    updated_at = NOW()
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

    print(f"Merged {len(doctors)} doctors and {len(slots)} appointment slots.")
