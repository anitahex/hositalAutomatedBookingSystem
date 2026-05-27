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
