CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS appointment_bookings;
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

CREATE TABLE appointment_bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slot_id UUID NOT NULL REFERENCES appointment_slots(slot_id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
    patient_id TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'booked',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (slot_id, status)
);

CREATE INDEX idx_doctors_department ON doctors(department);
CREATE INDEX idx_slots_available ON appointment_slots(start_time)
    WHERE is_booked = FALSE;
CREATE INDEX idx_appointment_bookings_active
    ON appointment_bookings(slot_id, end_time)
    WHERE status = 'booked';
