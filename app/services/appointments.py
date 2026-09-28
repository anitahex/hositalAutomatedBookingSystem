import logging
import re
from difflib import SequenceMatcher, get_close_matches
from datetime import date, timedelta

from app.db.connection import connect_db
from app.db.schema_once import once_per_process

logger = logging.getLogger(__name__)


BOOKING_LOOKAHEAD_DAYS = 7


DEPARTMENT_ALIASES = {
    "physician": "General Physician",
    "general physician": "General Physician",
    "general": "General Physician",
    "general medicine": "General Physician",
    "gp": "General Physician",
    "cardio": "Cardiology",
    "cardiologist": "Cardiology",
    "heart": "Cardiology",
    "neuro": "Neurology",
    "neurologist": "Neurology",
    "ortho": "Orthopedics",
    "orthopedic": "Orthopedics",
    "orthopaedic": "Orthopedics",
    "derm": "Dermatology",
    "skin": "Dermatology",
    "gastro": "Gastroenterology",
    "pulmo": "Pulmonology",
    "psych": "Psychiatry",
    "nephro": "Nephrology",
    "endo": "Endocrinology",
    "hema": "Hematology",
    "onco": "Oncology",
    # Practitioner and lay terms. Patients ask for "a psychiatrist", not for "Psychiatry",
    # and the substring/canonical checks miss that entirely ("psychiatry" is not a
    # substring of "psychiatrist"). Mapping the words people actually use is what makes
    # free text resolvable at all.
    "psychiatrist": "Psychiatry",
    # There is no Psychology department here, and Psychiatry is the closest we have. This
    # is a routing convenience, NOT a claim the two are equivalent — the resolver still
    # confirms with the patient before anything is booked.
    "psychologist": "Psychiatry",
    "psychology": "Psychiatry",
    "mental health": "Psychiatry",
    "therapist": "Psychiatry",
    "counsellor": "Psychiatry",
    "counselor": "Psychiatry",
    "gastroenterologist": "Gastroenterology",
    "pulmonologist": "Pulmonology",
    "nephrologist": "Nephrology",
    "endocrinologist": "Endocrinology",
    "hematologist": "Hematology",
    "haematologist": "Hematology",
    "oncologist": "Oncology",
    "dermatologist": "Dermatology",
    "orthopedist": "Orthopedics",
    "orthopaedics": "Orthopedics",
    "general practitioner": "General Physician",
    "family doctor": "General Physician",
}

# Services that PRODUCE a document, never departments that TREAT a patient. You do not
# book a follow-up with the radiologist who read your scan or the lab that ran your
# blood — you follow up with whoever ordered it. Kept as an explicit denylist rather than
# relying on their absence from CANONICAL_DEPARTMENTS, so a future data change cannot
# quietly make them bookable.
NEVER_ROUTE_TO_DEPARTMENTS = frozenset({
    "radiology", "pathology", "laboratory", "lab", "diagnostics", "imaging",
})

CANONICAL_DEPARTMENTS = [
    "General Physician",
    "Gastroenterology",
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "Oncology",
    "Pulmonology",
    "Psychiatry",
    "Nephrology",
    "Endocrinology",
    "Hematology",
    "Dermatology",
]

_NORMALIZED_CANONICAL_DEPARTMENTS = {
    " ".join(department.lower().split()): department
    for department in CANONICAL_DEPARTMENTS
}

_NORMALIZED_DEPARTMENT_ALIASES = {
    " ".join(alias.lower().split()): canonical
    for alias, canonical in DEPARTMENT_ALIASES.items()
}

_DEPARTMENT_STOPWORDS = {
    "department",
    "dept",
    "doctor",
    "dr",
    "specialist",
    "specialists",
    "clinic",
    "unit",
    "center",
    "centre",
    "care",
}


# Confidence floor for a STRICT match. A fuzzy hit below this is real enough to offer the
# patient as a candidate but not to act on silently — "physiatrist" (physical medicine)
# sits one edit from "psychiatrist" (mental health), and picking either one without asking
# would route a patient on a typo.
STRICT_MATCH_CONFIDENCE = 0.86


def _clean_department_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = " ".join(str(text).strip().lower().replace("-", " ").replace("/", " ").split())
    if not cleaned:
        return ""
    words = [word for word in cleaned.split() if word not in _DEPARTMENT_STOPWORDS]
    return " ".join(words).strip() or cleaned


def _lookup_exact(candidate: str) -> str | None:
    if candidate in _NORMALIZED_DEPARTMENT_ALIASES:
        return _NORMALIZED_DEPARTMENT_ALIASES[candidate]
    if candidate in _NORMALIZED_CANONICAL_DEPARTMENTS:
        return _NORMALIZED_CANONICAL_DEPARTMENTS[candidate]
    return None


def match_department_scored(
    text: str | None, valid_departments: list[str] | None = None
) -> tuple[str | None, float]:
    """Resolve free text to a real department, with a confidence score.

    Returns (None, 0.0) when nothing matches — it NEVER invents a department name, which
    is the difference between this and normalize_department_name below. A caller that
    gets None is expected to ask the patient rather than guess.

    Handles three shapes of input, because all three occur in practice:
      - a bare department or practitioner word  ("Psychiatry", "psychiatrist")
      - a misspelling of one                    ("phyciatrist", "psychitary")
      - a whole sentence containing one         ("can i see a psychiatrist?")

    `valid_departments` constrains the result to what this hospital actually offers
    (normally read from the doctors table). Anything on NEVER_ROUTE_TO_DEPARTMENTS is
    rejected outright: those are services that produce documents, not departments that
    treat patients.
    """
    cleaned = _clean_department_text(text)
    if not cleaned:
        return None, 0.0

    # Reject a producing service on the way IN, not just on the way out. Checking only the
    # result let "radiology" fuzzy-match to "Cardiology" at 0.84 and "pathology" to
    # "Psychiatry" at 0.74 — plausible-looking scores for two departments the patient never
    # mentioned. A document produced by Radiology tells us nothing about who should treat.
    if cleaned in NEVER_ROUTE_TO_DEPARTMENTS or any(
        token in NEVER_ROUTE_TO_DEPARTMENTS for token in cleaned.split()
    ):
        return None, 0.0

    allowed = None
    if valid_departments is not None:
        allowed = {" ".join(str(d).lower().split()) for d in valid_departments}

    def _accept(department: str | None, score: float) -> tuple[str | None, float]:
        if not department:
            return None, 0.0
        if " ".join(department.lower().split()) in NEVER_ROUTE_TO_DEPARTMENTS:
            return None, 0.0
        if allowed is not None and " ".join(department.lower().split()) not in allowed:
            return None, 0.0
        return department, score

    # 1. Whole string, exact.
    exact = _lookup_exact(cleaned)
    if exact:
        return _accept(exact, 1.0)

    known = list(_NORMALIZED_CANONICAL_DEPARTMENTS.keys()) + list(_NORMALIZED_DEPARTMENT_ALIASES.keys())

    # 2. Token-wise, exact — pulls "psychiatrist" out of "can i see a psychiatrist ?",
    #    which the regex-based extractor in supervisor.py cannot do.
    tokens = cleaned.split()
    for token in tokens:
        hit = _lookup_exact(token)
        if hit:
            return _accept(hit, 0.95)

    # 3. Whole string, fuzzy.
    best: tuple[str | None, float] = (None, 0.0)
    matches = get_close_matches(cleaned, known, n=1, cutoff=0.78)
    if matches:
        best = (_lookup_exact(matches[0]), SequenceMatcher(None, cleaned, matches[0]).ratio())

    # 4. Token-wise, fuzzy — catches a single misspelled word inside a sentence
    #    ("can i see a phyciatrist ?"). Deliberately last and scored, not trusted.
    for token in tokens:
        if len(token) < 5:
            continue  # too short to fuzzy-match safely ("ct", "mri", "the")
        token_matches = get_close_matches(token, known, n=1, cutoff=0.72)
        if not token_matches:
            continue
        score = SequenceMatcher(None, token, token_matches[0]).ratio()
        if score > best[1]:
            best = (_lookup_exact(token_matches[0]), score)

    return _accept(best[0], round(best[1], 3))


def match_department(text: str | None, valid_departments: list[str] | None = None) -> str | None:
    """Strict resolution: a real department name, or None. Never fabricates.

    Only high-confidence matches are returned. Use match_department_scored() when a weak
    match is still worth offering the patient as a candidate to confirm.
    """
    department, score = match_department_scored(text, valid_departments)
    return department if department and score >= STRICT_MATCH_CONFIDENCE else None


def normalize_department_name(department: str | None) -> str:
    """Legacy behaviour, unchanged: always returns a string, falling back to a
    title-cased version of whatever the caller passed.

    That fallback is why a typo could become a department ("physcologist" ->
    'Physcologist'). It is preserved here because ten call sites across booking, admin and
    consults depend on a non-None return; new code should call match_department() and
    handle None by asking the patient instead.
    """
    if not department:
        return "General Physician"

    cleaned = _clean_department_text(department)
    if not cleaned:
        return "General Physician"

    matched, score = match_department_scored(department)
    if matched and score >= 0.78:
        return matched

    return " ".join(word.capitalize() for word in cleaned.split())


def routable_departments(limit: int = 50) -> list[str]:
    """Every department this hospital actually staffs — the list used to VALIDATE a
    department before it can be shown to a patient or used in a booking query.

    Deliberately NOT available_departments() below, which is gated on having a free,
    unbooked slot inside the next seven days. That gate is right for "what can I book this
    week" and wrong for "does this department exist": Psychiatry has exactly one doctor, so
    in any week she is fully booked, available_departments() omits Psychiatry entirely and
    a validator built on it would conclude the hospital has no such department — the exact
    failure this validation exists to prevent.

    Falls back to CANONICAL_DEPARTMENTS if the database is unreachable. A validator that
    returns an empty list would reject every department and take the booking flow down
    with it; degrading to the static list keeps the app working and still blocks the
    fabricated names this guards against.
    """
    try:
        with connect_db() as conn:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT DISTINCT department
                    FROM doctors
                    WHERE {_active_doctor_clause()}
                        AND department IS NOT NULL
                        AND length(trim(department)) > 0
                    ORDER BY department
                    LIMIT %s
                    """,
                    (max(1, int(limit)),),
                )
                departments = [row[0] for row in cur.fetchall() if row and row[0]]
        return departments or list(CANONICAL_DEPARTMENTS)
    except Exception:
        return list(CANONICAL_DEPARTMENTS)


def available_departments(limit: int = 20):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    d.department,
                    COUNT(DISTINCT d.doctor_id) AS doctor_count,
                    COUNT(s.slot_id) AS available_slot_count,
                    MIN(s.start_time) AS next_available_time
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND s.start_time > NOW() + INTERVAL '30 minutes'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                GROUP BY d.department
                ORDER BY next_available_time ASC, d.department ASC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "department": str(department),
            "doctor_count": int(doctor_count),
            "available_slot_count": int(available_slot_count),
            "next_available_time": next_available_time.isoformat() if next_available_time else None,
        }
        for department, doctor_count, available_slot_count, next_available_time in rows
    ]


def _requested_date_within_booking_window(requested_date: str | None) -> bool:
    if not requested_date:
        return False
    try:
        parsed = date.fromisoformat(requested_date)
    except ValueError:
        return False

    today = date.today()
    return today <= parsed <= today + timedelta(days=BOOKING_LOOKAHEAD_DAYS)


def _parse_requested_date(requested_date: str | None) -> date | None:
    if not requested_date:
        return None
    try:
        parsed = date.fromisoformat(requested_date)
    except ValueError:
        return None
    if not _requested_date_within_booking_window(parsed.isoformat()):
        return None
    return parsed


def _active_doctor_clause() -> str:
    return "COALESCE(d.is_active, TRUE) = TRUE"


def _active_slot_clause() -> str:
    return "COALESCE(s.is_active, TRUE) = TRUE"


def _holiday_block_clause() -> str:
    return """
                    AND NOT EXISTS (
                        SELECT 1
                        FROM schedule_holidays h
                        WHERE h.is_active = TRUE
                            AND (
                                h.doctor_id IS NULL
                                OR h.doctor_id = d.doctor_id
                            )
                            AND DATE(s.start_time) BETWEEN h.start_date AND h.end_date
                    )
    """


@once_per_process
def ensure_booking_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                experience_years INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            ALTER TABLE doctors
                ALTER COLUMN doctor_id SET DEFAULT gen_random_uuid();
            ALTER TABLE doctors
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
            ALTER TABLE doctors
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
            ALTER TABLE doctors
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

            CREATE TABLE IF NOT EXISTS appointment_slots (
                slot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                is_booked BOOLEAN NOT NULL DEFAULT FALSE,
                booked_by_patient_id TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (doctor_id, start_time)
            );

            ALTER TABLE appointment_slots
                ALTER COLUMN slot_id SET DEFAULT gen_random_uuid();
            ALTER TABLE appointment_slots
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
            ALTER TABLE appointment_slots
                ADD COLUMN IF NOT EXISTS booked_by_patient_id TEXT;
            ALTER TABLE appointment_slots
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
            ALTER TABLE appointment_slots
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

            CREATE TABLE IF NOT EXISTS schedule_holidays (
                holiday_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                doctor_id UUID REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                reason TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CHECK (end_date >= start_date)
            );

            ALTER TABLE schedule_holidays
                ALTER COLUMN holiday_id SET DEFAULT gen_random_uuid();
            ALTER TABLE schedule_holidays
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
            ALTER TABLE schedule_holidays
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
            ALTER TABLE schedule_holidays
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

            CREATE TABLE IF NOT EXISTS appointment_bookings (
                booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slot_id UUID NOT NULL REFERENCES appointment_slots(slot_id) ON DELETE CASCADE,
                doctor_id UUID NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                patient_id TEXT,
                booking_note TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'booked',
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );

            ALTER TABLE appointment_bookings
                DROP CONSTRAINT IF EXISTS appointment_bookings_slot_id_status_key;

            CREATE INDEX IF NOT EXISTS idx_appointment_bookings_active
                ON appointment_bookings(slot_id, end_time)
                WHERE status = 'booked';

            CREATE UNIQUE INDEX IF NOT EXISTS ux_appointment_bookings_booked_slot
                ON appointment_bookings(slot_id)
                WHERE status = 'booked';

            CREATE INDEX IF NOT EXISTS idx_schedule_holidays_active
                ON schedule_holidays(doctor_id, start_date, end_date)
                WHERE is_active = TRUE;

            ALTER TABLE appointment_bookings
                ADD COLUMN IF NOT EXISTS booking_note TEXT;

            INSERT INTO appointment_bookings (
                slot_id,
                doctor_id,
                patient_id,
                booking_note,
                start_time,
                end_time
            )
            SELECT
                s.slot_id,
                s.doctor_id,
                s.booked_by_patient_id,
                NULL,
                s.start_time,
                s.end_time
            FROM appointment_slots s
            WHERE s.is_booked = TRUE
                AND NOT EXISTS (
                    -- Guard on ANY existing booking row for this slot, not just a
                    -- 'booked'-status one: the unique index below only covers
                    -- status='booked', so a slot left is_booked=TRUE with a
                    -- 'completed'/'cancelled' booking (e.g. a stale bulk import via
                    -- ingest_relational.py, or a direct SQL edit) would otherwise
                    -- pass straight through ON CONFLICT DO NOTHING and duplicate.
                    SELECT 1 FROM appointment_bookings b WHERE b.slot_id = s.slot_id
                )
            ON CONFLICT DO NOTHING;

            UPDATE appointment_bookings
            SET status = 'completed'
            WHERE status = 'booked' AND end_time <= NOW();

            UPDATE appointment_slots s
            SET is_booked = FALSE,
                booked_by_patient_id = NULL
            WHERE s.is_booked = TRUE
                AND NOT EXISTS (
                    SELECT 1
                    FROM appointment_bookings b
                    WHERE b.slot_id = s.slot_id
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                );
            """
        )


def available_doctors_for_department(department: str, limit: int = 5):
    department = normalize_department_name(department)
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    d.doctor_id,
                    d.name,
                    d.experience_years,
                    MIN(s.start_time) AS next_available_time,
                    COUNT(s.slot_id) AS available_slot_count
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.department = %s
                    AND {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND s.start_time > NOW() + INTERVAL '30 minutes'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                GROUP BY d.doctor_id, d.name, d.experience_years
                ORDER BY next_available_time ASC, d.experience_years DESC
                LIMIT %s;
                """,
                (department, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "doctor_id": str(doctor_id),
            "doctor_name": doctor_name,
            "experience_years": experience_years,
            "next_available_time": next_available_time.isoformat(),
            "available_slot_count": int(available_slot_count),
        }
        for doctor_id, doctor_name, experience_years, next_available_time, available_slot_count in rows
    ]


def available_doctors_for_department_on_date(department: str, requested_date: str, limit: int = 5):
    department = normalize_department_name(department)
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    d.doctor_id,
                    d.name,
                    d.experience_years,
                    MIN(s.start_time) AS next_available_time,
                    COUNT(s.slot_id) AS available_slot_count
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.department = %s
                    AND {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND s.start_time > NOW() + INTERVAL '30 minutes'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND DATE(s.start_time) = %s
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                GROUP BY d.doctor_id, d.name, d.experience_years
                ORDER BY next_available_time ASC, d.experience_years DESC
                LIMIT %s;
                """,
                (department, parsed_date, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "doctor_id": str(doctor_id),
            "doctor_name": doctor_name,
            "experience_years": experience_years,
            "next_available_time": next_available_time.isoformat(),
            "available_slot_count": int(available_slot_count),
        }
        for doctor_id, doctor_name, experience_years, next_available_time, available_slot_count in rows
    ]


def available_doctors_by_name(name: str, limit: int = 5):
    clean_name = re.sub(r"\b(dr\.?|doctor)\b", "", name, flags=re.IGNORECASE)
    clean_name = " ".join(clean_name.replace(".", " ").split())
    search = f"%{clean_name or name.strip()}%"
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    d.doctor_id,
                    d.name,
                    d.department,
                    d.experience_years,
                    MIN(s.start_time) AS next_available_time,
                    COUNT(s.slot_id) AS available_slot_count
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.name ILIKE %s
                    AND {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND s.start_time > NOW() + INTERVAL '30 minutes'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                GROUP BY d.doctor_id, d.name, d.department, d.experience_years
                ORDER BY next_available_time ASC, d.experience_years DESC
                LIMIT %s;
                """,
                (search, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "doctor_id": str(doctor_id),
            "doctor_name": doctor_name,
            "department": department,
            "experience_years": experience_years,
            "next_available_time": next_available_time.isoformat(),
            "available_slot_count": int(available_slot_count),
        }
        for doctor_id, doctor_name, department, experience_years, next_available_time, available_slot_count in rows
    ]


def available_doctors_by_name_on_date(name: str, requested_date: str, limit: int = 5):
    clean_name = re.sub(r"\b(dr\.?|doctor)\b", "", name, flags=re.IGNORECASE)
    clean_name = " ".join(clean_name.replace(".", " ").split())
    search = f"%{clean_name or name.strip()}%"
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    d.doctor_id,
                    d.name,
                    d.department,
                    d.experience_years,
                    MIN(s.start_time) AS next_available_time,
                    COUNT(s.slot_id) AS available_slot_count
                FROM doctors d
                JOIN appointment_slots s ON s.doctor_id = d.doctor_id
                WHERE d.name ILIKE %s
                    AND {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND s.start_time > NOW() + INTERVAL '30 minutes'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND DATE(s.start_time) = %s
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                GROUP BY d.doctor_id, d.name, d.department, d.experience_years
                ORDER BY next_available_time ASC, d.experience_years DESC
                LIMIT %s;
                """,
                (search, parsed_date, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "doctor_id": str(doctor_id),
            "doctor_name": doctor_name,
            "department": department,
            "experience_years": experience_years,
            "next_available_time": next_available_time.isoformat(),
            "available_slot_count": int(available_slot_count),
        }
        for doctor_id, doctor_name, department, experience_years, next_available_time, available_slot_count in rows
    ]


def available_slots_for_doctor(doctor_id: str, limit: int = 5):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT s.slot_id, s.start_time, s.end_time, d.name
                FROM appointment_slots s
                JOIN doctors d ON s.doctor_id = d.doctor_id
                WHERE s.doctor_id = %s
                    AND {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND s.start_time > NOW() + INTERVAL '30 minutes'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                ORDER BY s.start_time ASC
                LIMIT %s;
                """,
                (doctor_id, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "slot_id": str(slot_id),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "doctor_name": doctor_name,
        }
        for slot_id, start_time, end_time, doctor_name in rows
    ]


def available_slots_for_doctor_on_date(doctor_id: str, requested_date: str, limit: int = 5):
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT s.slot_id, s.start_time, s.end_time, d.name
                FROM appointment_slots s
                JOIN doctors d ON s.doctor_id = d.doctor_id
                WHERE s.doctor_id = %s
                    AND {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND s.start_time > NOW() + INTERVAL '30 minutes'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND DATE(s.start_time) = %s
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                ORDER BY s.start_time ASC
                LIMIT %s;
                """,
                (doctor_id, parsed_date, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "slot_id": str(slot_id),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "doctor_name": doctor_name,
        }
        for slot_id, start_time, end_time, doctor_name in rows
    ]


def first_available_slots(department: str, limit: int = 5):
    department = normalize_department_name(department)
    doctors = available_doctors_for_department(department=department, limit=limit)
    slots = []

    for doctor in doctors:
        doctor_slots = available_slots_for_doctor(doctor["doctor_id"], limit=1)
        slots.extend(doctor_slots)

    return slots[:limit]


BOOKING_NOTE_MAX_LENGTH = 4000

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_booking_note(note: str | None, *, max_length: int = BOOKING_NOTE_MAX_LENGTH) -> str | None:
    """Strip control characters and cap length for anything written into
    appointment_bookings.booking_note. This field is ultimately sourced (directly
    or via an LLM-generated summary) from patient chat input, which is untrusted —
    see FULL_SYSTEM_AUDIT.md P0 #5. Preserves normal whitespace/newlines/markdown."""
    if not note:
        return None
    cleaned = _CONTROL_CHAR_RE.sub("", str(note)).strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "\n[truncated]"
    return cleaned


def book_selected_slot(
    slot_id: str,
    patient_id: str | None = None,
    booking_note: str | None = None,
    booking_context=None,
):
    """Books a slot, and records the pre-visit context in the SAME transaction.

    `booking_context` is an optional booking_context.SnapshotContext describing the
    conversation that produced this booking. It is keyword-optional so the REST booking
    route (app/api/routes/appointments.py) is unaffected — a booking made directly has no
    conversation, and that is recorded honestly as 'skipped' rather than left looking like
    a summary that failed to generate.
    """
    note = _sanitize_booking_note(" ".join(str(booking_note).strip().split())) if booking_note else None
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT d.name, d.department, s.start_time, s.end_time, s.slot_id, s.doctor_id
                    FROM appointment_slots s
                    JOIN doctors d ON s.doctor_id = d.doctor_id
                    WHERE s.slot_id = %s
                        AND {_active_doctor_clause()}
                        AND {_active_slot_clause()}
                        AND s.start_time > NOW() + INTERVAL '30 minutes'
                        AND s.start_time <= NOW() + INTERVAL '7 days'
                        AND NOT EXISTS (
                            SELECT 1
                            FROM appointment_bookings b
                            WHERE b.slot_id = s.slot_id
                                AND b.status = 'booked'
                                AND b.end_time > NOW()
                        )
                        {_holiday_block_clause()}
                    FOR UPDATE OF s SKIP LOCKED;
                    """,
                    (slot_id,),
                )
                slot = cur.fetchone()

                if not slot:
                    conn.rollback()
                    return None

                doctor_name, department, start_time, end_time, booked_slot_id, doctor_id = slot
                cur.execute(
                    """
                    INSERT INTO appointment_bookings (
                        slot_id,
                        doctor_id,
                        patient_id,
                        booking_note,
                        start_time,
                        end_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (booked_slot_id, doctor_id, patient_id, note, start_time, end_time),
                )
                cur.execute(
                    """
                    SELECT booking_id
                    FROM appointment_bookings
                    WHERE slot_id = %s
                        AND status = 'booked'
                    ORDER BY created_at DESC
                    LIMIT 1;
                    """,
                    (booked_slot_id,),
                )
                booking_id = cur.fetchone()[0]
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = TRUE,
                        booked_by_patient_id = %s
                    WHERE slot_id = %s;
                    """,
                    (patient_id, booked_slot_id),
                )

                # The pre-visit context, in this transaction so it commits with the
                # booking or not at all — there is no state where an appointment exists
                # without the record of what produced it.
                #
                # Inside a SAVEPOINT because in Postgres a failed statement aborts the
                # ENTIRE transaction: without it, a snapshot error would roll back the
                # booking itself. A missing context is a degraded record; a lost booking
                # is a patient who does not get seen, and that trade is not close.
                from app.services.booking_context import (
                    SnapshotContext, capture_snapshot_safely, ensure_booking_context_schema,
                )

                context = booking_context or SnapshotContext(chosen_department=department)
                cur.execute("SAVEPOINT booking_context_capture")
                try:
                    ensure_booking_context_schema(conn)
                    capture_snapshot_safely(
                        cur, booking_id=booking_id, patient_id=patient_id, context=context
                    )
                    cur.execute("RELEASE SAVEPOINT booking_context_capture")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT booking_context_capture")
                    logger.exception(
                        "book_selected_slot: pre-visit context not recorded for booking %s",
                        booking_id,
                    )

                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "doctor": doctor_name,
        "doctor_name": doctor_name,
        "department": department,
        "time": start_time.isoformat(),
        "start_time": start_time,
        "end_time": end_time,
        "slot_id": booked_slot_id,
        "booking_id": booking_id,
        "booking_note": note,
    }


def _normalized_booking_note(note: str | None) -> str | None:
    if not note:
        return None
    # Only strip leading/trailing whitespace; preserve internal newlines and markdown structure.
    # Control-character stripping / length capping happens in _sanitize_booking_note, applied
    # by the caller (update_booking_note) — kept separate so existing-note reads (which should
    # not be re-truncated on every read) go through this lighter normalization only.
    cleaned = str(note).strip()
    return cleaned or None


def update_booking_note(booking_id: str, patient_id: str, booking_note: str):
    note = _sanitize_booking_note(_normalized_booking_note(booking_note))
    if not note:
        return None

    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT booking_note
                    FROM appointment_bookings
                    WHERE booking_id::text = %s
                        AND patient_id = %s
                        AND status = 'booked';
                    """,
                    (booking_id, patient_id),
                )
                existing_row = cur.fetchone()
                if not existing_row:
                    conn.rollback()
                    return None

                existing_note = _normalized_booking_note(existing_row[0])
                combined_note = note if not existing_note else f"{existing_note}\n{note}"
                # Re-cap after combining — the per-call cap above bounds a single write, but
                # repeated forwarding requests could otherwise still grow the field unboundedly.
                combined_note = _sanitize_booking_note(combined_note)

                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET booking_note = %s
                    WHERE booking_id::text = %s
                        AND patient_id = %s
                        AND status = 'booked'
                    RETURNING booking_id;
                    """,
                    (combined_note, booking_id, patient_id),
                )
                updated = cur.fetchone()
                if not updated:
                    conn.rollback()
                    return None

                cur.execute(
                    """
                    SELECT
                        b.booking_id,
                        b.slot_id,
                        d.name,
                        d.department,
                        b.booking_note,
                        b.start_time,
                        b.end_time,
                        b.status,
                        b.start_time > NOW() + INTERVAL '24 hours' AS can_modify
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE b.booking_id::text = %s
                        AND b.patient_id = %s
                        AND b.status = 'booked';
                    """,
                    (booking_id, patient_id),
                )
                row = cur.fetchone()
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    if not row:
        return None

    booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time, status, can_modify = row
    return {
        "booking_id": str(booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "booking_note": booking_note,
        "time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": str(status),
        "can_modify": bool(can_modify),
    }


def active_bookings_for_patient(patient_id: str | None = None, limit: int = 10):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            if patient_id:
                cur.execute(
                    """
                SELECT
                    b.booking_id,
                    b.slot_id,
                    d.name,
                    d.department,
                    b.booking_note,
                    b.start_time,
                    b.end_time
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE b.patient_id = %s
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                    ORDER BY b.start_time ASC
                    LIMIT %s;
                    """,
                    (patient_id, limit),
                )
            else:
                cur.execute(
                    """
                SELECT
                    b.booking_id,
                    b.slot_id,
                    d.name,
                    d.department,
                    b.booking_note,
                    b.start_time,
                    b.end_time
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE b.status = 'booked'
                        AND b.end_time > NOW()
                    ORDER BY b.start_time ASC
                    LIMIT %s;
                    """,
                    (limit,),
                )
            rows = cur.fetchall()

    return [
        {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "doctor": str(doctor_name),
            "department": str(department),
            "booking_note": booking_note,
            "time": str(start_time),
            "end_time": str(end_time),
        }
        for booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time in rows
    ]


def upcoming_bookings_for_patient(patient_id: str, limit: int = 20):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.booking_id,
                    b.slot_id,
                    d.name,
                    d.department,
                    b.booking_note,
                    b.start_time,
                    b.end_time,
                    b.status,
                    b.start_time > NOW() + INTERVAL '24 hours' AS can_modify
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                WHERE b.patient_id = %s
                    AND b.status = 'booked'
                    AND b.end_time > NOW()
                ORDER BY b.start_time ASC
                LIMIT %s;
                """,
                (patient_id, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "doctor": str(doctor_name),
            "department": str(department),
            "booking_note": booking_note,
            "time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": str(status),
            "can_modify": bool(can_modify),
        }
        for booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time, status, can_modify in rows
    ]


def previous_bookings_for_patient(patient_id: str, limit: int = 20):
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE appointment_bookings
                SET status = 'completed'
                WHERE patient_id = %s
                    AND status = 'booked'
                    AND end_time <= NOW();

                SELECT
                    b.booking_id,
                    b.slot_id,
                    d.name,
                    d.department,
                    b.booking_note,
                    b.start_time,
                    b.end_time,
                    b.status
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                WHERE b.patient_id = %s
                    AND (
                        b.status IN ('completed', 'cancelled')
                        OR b.end_time <= NOW()
                    )
                ORDER BY b.start_time DESC
                LIMIT %s;
                """,
                (patient_id, patient_id, limit),
            )
            rows = cur.fetchall()
        conn.commit()

    return [
        {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "doctor": str(doctor_name),
            "department": str(department),
            "booking_note": booking_note,
            "time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": str(status),
        }
        for booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time, status in rows
    ]


def _modifiable_booking(cur, booking_id: str, patient_id: str):
    cur.execute(
        """
        SELECT
            b.booking_id,
            b.slot_id,
            b.doctor_id,
            d.name,
            d.department,
            b.booking_note,
            b.start_time,
            b.end_time
        FROM appointment_bookings b
        JOIN doctors d ON d.doctor_id = b.doctor_id
        WHERE b.booking_id::text = %s
            AND b.patient_id = %s
            AND b.status = 'booked'
            AND b.start_time > NOW() + INTERVAL '24 hours'
        FOR UPDATE OF b;
        """,
        (booking_id, patient_id),
    )
    return cur.fetchone()


def cancel_patient_booking(booking_id: str, patient_id: str):
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                row = _modifiable_booking(cur, booking_id, patient_id)
                if not row:
                    conn.rollback()
                    return None

                booking_id, slot_id, doctor_id, doctor_name, department, booking_note, start_time, end_time = row
                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET status = 'cancelled'
                    WHERE booking_id = %s;
                    """,
                    (booking_id,),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = FALSE,
                        booked_by_patient_id = NULL
                    WHERE slot_id = %s;
                    """,
                    (slot_id,),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "booking_id": str(booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "booking_note": booking_note,
        "time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "cancelled",
    }


def reschedule_options_for_booking(
    booking_id: str,
    patient_id: str,
    requested_date: str,
    limit: int = 8,
):
    parsed_date = _parse_requested_date(requested_date)
    if not parsed_date:
        return []
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.doctor_id
                FROM appointment_bookings b
                WHERE b.booking_id::text = %s
                    AND b.patient_id = %s
                    AND b.status = 'booked'
                    AND b.start_time > NOW() + INTERVAL '24 hours';
                """,
                (booking_id, patient_id),
            )
            booking = cur.fetchone()
            if not booking:
                return []

            doctor_id = booking[0]
            cur.execute(
                f"""
                SELECT s.slot_id, s.start_time, s.end_time, d.name
                FROM appointment_slots s
                JOIN doctors d ON d.doctor_id = s.doctor_id
                WHERE s.doctor_id = %s
                    AND {_active_doctor_clause()}
                    AND {_active_slot_clause()}
                    AND DATE(s.start_time) = %s
                    AND s.start_time > NOW() + INTERVAL '24 hours'
                    AND s.start_time <= NOW() + INTERVAL '7 days'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM appointment_bookings b
                        WHERE b.slot_id = s.slot_id
                            AND b.status = 'booked'
                            AND b.end_time > NOW()
                    )
                    {_holiday_block_clause()}
                ORDER BY s.start_time ASC
                LIMIT %s;
                """,
                (doctor_id, parsed_date, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "slot_id": str(slot_id),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "doctor_name": doctor_name,
        }
        for slot_id, start_time, end_time, doctor_name in rows
    ]


def reschedule_patient_booking(booking_id: str, patient_id: str, new_slot_id: str):
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                booking = _modifiable_booking(cur, booking_id, patient_id)
                if not booking:
                    conn.rollback()
                    return None

                (
                    current_booking_id,
                    old_slot_id,
                    _old_doctor_id,
                    _doctor_name,
                    _department,
                    booking_note,
                    _old_start_time,
                    _old_end_time,
                ) = booking

                cur.execute(
                    f"""
                SELECT s.slot_id, s.doctor_id, d.name, d.department, s.start_time, s.end_time
                    FROM appointment_slots s
                    JOIN doctors d ON d.doctor_id = s.doctor_id
                    WHERE s.slot_id::text = %s
                        AND {_active_doctor_clause()}
                        AND {_active_slot_clause()}
                        AND s.start_time > NOW() + INTERVAL '24 hours'
                        AND s.start_time <= NOW() + INTERVAL '7 days'
                        AND NOT EXISTS (
                            SELECT 1
                            FROM appointment_bookings b
                            WHERE b.slot_id = s.slot_id
                                AND b.status = 'booked'
                                AND b.end_time > NOW()
                        )
                        {_holiday_block_clause()}
                    FOR UPDATE OF s SKIP LOCKED;
                    """,
                    (new_slot_id,),
                )
                slot = cur.fetchone()
                if not slot:
                    conn.rollback()
                    return None

                slot_id, doctor_id, doctor_name, department, start_time, end_time = slot
                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET slot_id = %s,
                        doctor_id = %s,
                        start_time = %s,
                        end_time = %s
                    WHERE booking_id = %s;
                    """,
                    (slot_id, doctor_id, start_time, end_time, current_booking_id),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = FALSE,
                        booked_by_patient_id = NULL
                    WHERE slot_id = %s;
                    """,
                    (old_slot_id,),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = TRUE,
                        booked_by_patient_id = %s
                    WHERE slot_id = %s;
                    """,
                    (patient_id, slot_id),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "booking_id": str(current_booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "booking_note": booking_note,
        "time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "booked",
        "can_modify": True,
    }


def doctor_appointments(doctor_id: str, scope: str, limit: int = 100):
    """Appointments for one doctor's own bookings only, filtered strictly by doctor_id."""
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            if scope == "upcoming":
                cur.execute(
                    """
                    SELECT
                        b.booking_id,
                        b.patient_id,
                        COALESCE(pp.name, 'Unknown patient') AS patient_name,
                        d.department,
                        b.booking_note,
                        b.start_time,
                        b.end_time,
                        b.status
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    LEFT JOIN patient_profiles pp ON pp.user_id::text = b.patient_id
                    WHERE b.doctor_id = %s
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                    ORDER BY b.start_time ASC
                    LIMIT %s;
                    """,
                    (doctor_id, limit),
                )
            else:
                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET status = 'completed'
                    WHERE doctor_id = %s
                        AND status = 'booked'
                        AND end_time <= NOW();

                    SELECT
                        b.booking_id,
                        b.patient_id,
                        COALESCE(pp.name, 'Unknown patient') AS patient_name,
                        d.department,
                        b.booking_note,
                        b.start_time,
                        b.end_time,
                        b.status
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    LEFT JOIN patient_profiles pp ON pp.user_id::text = b.patient_id
                    WHERE b.doctor_id = %s
                        AND (b.status IN ('completed', 'cancelled') OR b.end_time <= NOW())
                    ORDER BY b.start_time DESC
                    LIMIT %s;
                    """,
                    (doctor_id, doctor_id, limit),
                )
            rows = cur.fetchall()
        conn.commit()

    return [
        {
            "booking_id": str(booking_id),
            "patient_id": str(patient_id) if patient_id is not None else None,
            "patient_name": str(patient_name),
            "department": str(department),
            "booking_note": booking_note,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": str(status),
        }
        for booking_id, patient_id, patient_name, department, booking_note, start_time, end_time, status in rows
    ]


def doctor_patients(doctor_id: str, limit: int = 200):
    """Distinct patients this doctor has an actual booking history with — never patients they haven't treated."""
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.patient_id,
                    COALESCE(pp.name, 'Unknown patient') AS patient_name,
                    pp.email,
                    pp.mobile_number,
                    COUNT(*) AS visit_count,
                    MAX(b.start_time) AS last_visit
                FROM appointment_bookings b
                LEFT JOIN patient_profiles pp ON pp.user_id::text = b.patient_id
                WHERE b.doctor_id = %s
                    AND b.patient_id IS NOT NULL
                GROUP BY b.patient_id, pp.name, pp.email, pp.mobile_number
                ORDER BY last_visit DESC
                LIMIT %s;
                """,
                (doctor_id, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "patient_id": str(patient_id),
            "patient_name": str(patient_name),
            "email": email,
            "mobile_number": mobile_number,
            "visit_count": int(visit_count),
            "last_visit": last_visit.isoformat() if last_visit else None,
        }
        for patient_id, patient_name, email, mobile_number, visit_count, last_visit in rows
    ]


def doctor_patient_detail(doctor_id: str, patient_id: str, limit: int = 100):
    """Returns None if this doctor has no booking history with this patient — the caller
    must treat that as a 404, since a doctor must never see a patient they haven't treated."""
    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.booking_id,
                    d.department,
                    b.start_time,
                    b.end_time,
                    b.status,
                    lc.id,
                    lc.status,
                    lc.ended_at,
                    lc.note_status
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                -- The visit's latest consult that was not discarded, and its note. LATERAL
                -- with LIMIT 1 because a booking can have several consults (one discarded,
                -- one restarted); a plain join would list the visit once per consult. So the
                -- visit-history card can say what actually happened instead of the
                -- "No clinical note yet" it used to print for every visit, signed or not.
                LEFT JOIN LATERAL (
                    SELECT c.id, c.status, c.ended_at, sn.status AS note_status
                    FROM consultations c
                    LEFT JOIN soap_notes sn ON sn.consultation_id = c.id
                    WHERE c.booking_id = b.booking_id AND c.status <> 'discarded'
                    ORDER BY c.created_at DESC
                    LIMIT 1
                ) lc ON TRUE
                WHERE b.doctor_id = %s
                    AND b.patient_id = %s
                ORDER BY b.start_time DESC
                LIMIT %s;
                """,
                (doctor_id, patient_id, limit),
            )
            visit_rows = cur.fetchall()

            if not visit_rows:
                return None

            cur.execute(
                """
                SELECT name, age, mobile_number, email, blood_group, health_issues
                FROM patient_profiles
                WHERE user_id::text = %s;
                """,
                (patient_id,),
            )
            profile_row = cur.fetchone()

    if profile_row:
        name, age, mobile_number, email, blood_group, health_issues = profile_row
    else:
        name = age = mobile_number = email = blood_group = health_issues = None

    return {
        "patient_id": patient_id,
        "name": name or "Unknown patient",
        "age": age,
        "mobile_number": mobile_number,
        "email": email,
        "blood_group": blood_group,
        "health_issues": health_issues,
        "visits": [
            {
                "booking_id": str(booking_id),
                "department": str(department),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "status": str(status),
                "consult_id": str(consult_id) if consult_id else None,
                "consult_status": consult_status,
                "consult_ended_at": consult_ended_at.isoformat() if consult_ended_at else None,
                "note_status": note_status,
            }
            for (booking_id, department, start_time, end_time, status,
                 consult_id, consult_status, consult_ended_at, note_status) in visit_rows
        ],
    }


def doctor_treats_patient(doctor_id: str, patient_id: str) -> bool:
    """The authorization predicate behind every doctor-to-patient data access: TRUE only
    if this doctor has a real booking history with this patient.

    This is the cheap EXISTS form of the exact condition doctor_patient_detail already
    enforces with its `if not visit_rows: return None` gate — same table, same two
    columns, no status filter — for callers that need the yes/no without paying for the
    visit list. The two MUST stay in agreement; test_doctor_patient_documents.py asserts
    that they do, so a change to one that isn't mirrored in the other fails a test rather
    than silently widening access.
    """
    if not doctor_id or not patient_id:
        return False

    with connect_db() as conn:
        ensure_booking_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM appointment_bookings
                    WHERE doctor_id = %s AND patient_id = %s
                )
                """,
                (doctor_id, patient_id),
            )
            return bool(cur.fetchone()[0])


def cancel_booking(reference: str, patient_id: str | None = None):
    with connect_db() as conn:
        try:
            ensure_booking_schema(conn)
            with conn.cursor() as cur:
                params = [reference, reference]
                patient_clause = ""
                if patient_id:
                    patient_clause = "AND b.patient_id = %s"
                    params.append(patient_id)

                cur.execute(
                    f"""
                    SELECT
                        b.booking_id,
                        b.slot_id,
                        d.name,
                        d.department,
                        b.booking_note,
                        b.start_time,
                        b.end_time
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE (b.booking_id::text = %s OR b.slot_id::text = %s)
                        AND b.status = 'booked'
                        AND b.end_time > NOW()
                        AND b.start_time > NOW() + INTERVAL '24 hours'
                        {patient_clause}
                    FOR UPDATE OF b;
                    """,
                    tuple(params),
                )
                row = cur.fetchone()

                if not row:
                    conn.rollback()
                    return None

                booking_id, slot_id, doctor_name, department, booking_note, start_time, end_time = row
                cur.execute(
                    """
                    UPDATE appointment_bookings
                    SET status = 'cancelled'
                    WHERE booking_id = %s;
                    """,
                    (booking_id,),
                )
                cur.execute(
                    """
                    UPDATE appointment_slots
                    SET is_booked = FALSE,
                        booked_by_patient_id = NULL
                    WHERE slot_id = %s;
                    """,
                    (slot_id,),
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {
        "booking_id": str(booking_id),
        "slot_id": str(slot_id),
        "doctor": str(doctor_name),
        "department": str(department),
        "booking_note": booking_note,
        "time": str(start_time),
        "end_time": str(end_time),
    }
