"""Every encounter a patient has had, across all doctors.

WHAT CHANGED, AND WHY IT IS A ONE-WAY DOOR. Until now a doctor saw only their own signed
notes (patient_brief) and only patients they treat. This widens the second half: past the
existing treating-relationship gate, a doctor sees the whole hospital's history for that
patient. That was the agreed decision — withholding history from a clinician who is
treating the patient is itself a clinical risk — but it means every open is a disclosure,
so every open is audited.

WHAT IS STILL WITHHELD, deliberately:

  - UNSIGNED DRAFTS. A draft is model output no clinician has taken responsibility for.
    Showing another doctor's draft in a history timeline would launder it into the record
    by presentation alone. Only `status = 'signed'` notes appear, for anyone.
  - SENSITIVE DEPARTMENTS. Notes from a department in SENSITIVE_DEPARTMENTS are withheld
    from doctors outside it. The ENCOUNTER is always shown — the date, the department,
    that it happened — because hiding the visit itself would misrepresent the record and
    let a doctor believe there is no history when there is. Only the clinical content is
    held back.

WHY SENSITIVE_DEPARTMENTS IS IN CODE. The approved plan proposed an `is_sensitive` column.
There is no departments table — `department` is a text column on `doctors` — so the column
would have to sit per-doctor, which models it wrongly: sensitivity is a property of the
specialty, not of the individual. A code-owned set matches how every other department rule
in this codebase is expressed (appointments.CANONICAL_DEPARTMENTS,
NEVER_ROUTE_TO_DEPARTMENTS) and is directly testable. It should move to a table the day an
administrator needs to change it without a deploy.

KNOWN GAP, not silently left: this restricts NOTE content. A document uploaded around a
psychiatry visit is still reachable through the existing document routes, which have no
concept of sensitivity. Closing that belongs with the break-glass work.

QUERY SHAPE. Four queries for a whole page, never per row. The application runs one
connection pool of ten for every user and it raises rather than queues when exhausted, so
an N+1 here would take the workspace down under a handful of doctors, not hundreds.
"""
from __future__ import annotations

import logging
from datetime import datetime

from app.db.connection import connect_db

logger = logging.getLogger(__name__)

TIMELINE_DEFAULT_LIMIT = 20
TIMELINE_MAX_LIMIT = 100

# Specialties whose note content is withheld from doctors outside them. Lowercase; matched
# case-insensitively against doctors.department.
SENSITIVE_DEPARTMENTS = frozenset({"psychiatry"})

# How a withheld note is described. Says that something exists and is restricted, which is
# the honest position — never an empty note, which reads as "nothing was written".
RESTRICTED_NOTE_LABEL = "Restricted — clinical content from a sensitive specialty."


def is_sensitive_department(department: str | None) -> bool:
    return " ".join(str(department or "").lower().split()) in SENSITIVE_DEPARTMENTS


def may_read_note(viewer_department: str | None, encounter_department: str | None) -> bool:
    """Whether this doctor may read the note content of this encounter.

    A doctor inside the sensitive specialty reads its notes normally — the restriction is
    about disclosure ACROSS specialties, not about making psychiatry notes unreadable to
    psychiatrists.
    """
    if not is_sensitive_department(encounter_department):
        return True
    return " ".join(str(viewer_department or "").lower().split()) == \
        " ".join(str(encounter_department or "").lower().split())


def _note_summary(note_row) -> str:
    """One line from a signed note: the assessment if there is one, else the plan.

    Assessment first because it is the clinical conclusion — what a colleague scanning a
    history needs. Truncated on a word boundary so a timeline row cannot become a wall of
    text; the full note is one click away.
    """
    assessment, plan = (note_row or (None, None))
    text = " ".join(str(assessment or plan or "").split())
    if len(text) <= 180:
        return text
    return text[:180].rsplit(" ", 1)[0] + "…"


# Which documents belong to which encounter. Two records say so, and nothing else is used:
#
#   - document_catalog.booking_id, when the document was attached to a booking directly
#   - booking_context_snapshots.document_ids — the documents uploaded in the conversation
#     where the patient booked, frozen onto the booking when it was made
#
# The timeline used to read only the first, which nothing sets for a patient's own
# uploads, so every document filter returned no encounters and no encounter listed its
# documents. A document neither record ties to a booking is NOT guessed onto one (by
# upload time, say): it appears as its own timeline entry instead, "uploaded by the
# patient", dated by the document.
_ENCOUNTER_DOCUMENTS = """
    SELECT dc.booking_id, dc.document_id
    FROM document_catalog dc
    JOIN appointment_bookings eb ON eb.booking_id = dc.booking_id AND eb.patient_id = %(patient_id)s
    WHERE dc.user_id = %(patient_id)s AND dc.ingestion_status = 'complete'
    UNION
    SELECT s.booking_id, ids.document_id
    FROM booking_context_snapshots s
    JOIN appointment_bookings eb ON eb.booking_id = s.booking_id AND eb.patient_id = %(patient_id)s
    CROSS JOIN LATERAL jsonb_array_elements_text(s.document_ids) AS ids(document_id)
    JOIN document_catalog dc ON dc.document_id = ids.document_id
         AND dc.user_id = %(patient_id)s AND dc.ingestion_status = 'complete'
"""

# When a document with no visit sits on the timeline: the date the report itself carries,
# else when it was uploaded.
_DOCUMENT_TIME = "COALESCE(dc.clinical_date::timestamp, dc.created_at::timestamp)"


def get_patient_timeline(
    doctor_id: str,
    patient_id: str,
    viewer_department: str | None = None,
    *,
    department: str | None = None,
    other_doctor_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    document_type: str | None = None,
    limit: int = TIMELINE_DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict:
    """Encounters, and documents that belong to no encounter, newest first — with filters
    and a cursor.

    `items` is the timeline in order, each {"kind": "encounter" | "document", ...}.
    `encounters` is the encounter items alone, as before.

    Documents with no visit have no department and no doctor, so they are included only
    while neither of those filters is set.

    Authorization is the caller's responsibility (the treating-relationship check) and is
    applied by the route before this runs — this function assumes it has already passed
    and is scoped to one patient throughout.
    """
    limit = max(1, min(int(limit), TIMELINE_MAX_LIMIT))
    params: dict = {"patient_id": patient_id, "limit": limit + 1}

    encounter_conditions = ["b.patient_id = %(patient_id)s"]
    document_conditions = [
        "dc.user_id = %(patient_id)s", "dc.ingestion_status = 'complete'",
        "dc.document_id NOT IN (SELECT document_id FROM encounter_documents)",
    ]
    if department:
        encounter_conditions.append("LOWER(d.department) = LOWER(%(department)s)")
        params["department"] = department
    if other_doctor_id:
        encounter_conditions.append("b.doctor_id = %(other_doctor_id)s")
        params["other_doctor_id"] = other_doctor_id
    if date_from:
        encounter_conditions.append("b.start_time >= %(date_from)s")
        document_conditions.append(f"{_DOCUMENT_TIME} >= %(date_from)s")
        params["date_from"] = date_from
    if date_to:
        # Inclusive of the whole end day: a doctor filtering "to 20 Sep" means everything
        # that happened on the 20th, not everything before midnight that morning.
        encounter_conditions.append("b.start_time < (%(date_to)s::date + 1)")
        document_conditions.append(f"{_DOCUMENT_TIME} < (%(date_to)s::date + 1)")
        params["date_to"] = date_to
    if document_type:
        encounter_conditions.append(
            "EXISTS (SELECT 1 FROM encounter_documents ed JOIN document_catalog f"
            " ON f.document_id = ed.document_id"
            " WHERE ed.booking_id = b.booking_id AND f.document_type = %(document_type)s)"
        )
        document_conditions.append("dc.document_type = %(document_type)s")
        params["document_type"] = document_type
    include_documents = not department and not other_doctor_id
    params["cursor"] = cursor

    # One entry per distinct document: the same report uploaded three times is one entry,
    # "uploaded 3 times", as in the visit brief — not three identical rows.
    document_items = f"""
        UNION ALL
        SELECT 'document', latest_copy.at, latest_copy.document_id
        FROM (
            SELECT DISTINCT ON (dc.original_filename, dc.clinical_date, dc.document_type)
                   {_DOCUMENT_TIME} AS at, dc.document_id
            FROM document_catalog dc
            WHERE {" AND ".join(document_conditions)}
            ORDER BY dc.original_filename, dc.clinical_date, dc.document_type, dc.created_at DESC
        ) latest_copy
    """ if include_documents else ""

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                WITH encounter_documents AS ({_ENCOUNTER_DOCUMENTS}),
                items AS (
                    SELECT 'encounter' AS kind, b.start_time AS at, b.booking_id::text AS item_id
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    WHERE {" AND ".join(encounter_conditions)}
                    {document_items}
                )
                SELECT kind, at, item_id FROM items
                WHERE %(cursor)s::timestamp IS NULL OR at < %(cursor)s::timestamp
                ORDER BY at DESC, item_id
                LIMIT %(limit)s
                """,
                params,
            )
            ordered = cur.fetchall()

            # One extra row was requested to detect a further page without counting the
            # whole history on every request.
            has_more = len(ordered) > limit
            ordered = ordered[:limit]
            booking_ids = [item_id for kind, _at, item_id in ordered if kind == "encounter"]
            standalone_ids = [item_id for kind, _at, item_id in ordered if kind == "document"]

            bookings: dict = {}
            if booking_ids:
                # The visit's latest consult that was not discarded. LATERAL with LIMIT 1:
                # a booking with two consults (one discarded, one restarted) was listed twice.
                cur.execute(
                    """
                    SELECT b.booking_id::text, b.start_time, b.status, b.booking_note,
                           b.doctor_id, d.name, d.department, lc.id
                    FROM appointment_bookings b
                    JOIN doctors d ON d.doctor_id = b.doctor_id
                    LEFT JOIN LATERAL (
                        SELECT c.id FROM consultations c
                        WHERE c.booking_id = b.booking_id AND c.status <> 'discarded'
                        ORDER BY c.created_at DESC
                        LIMIT 1
                    ) lc ON TRUE
                    WHERE b.booking_id = ANY(%s::uuid[])
                    """,
                    (booking_ids,),
                )
                bookings = {row[0]: row for row in cur.fetchall()}
            consultation_ids = [row[7] for row in bookings.values() if row[7]]

            notes: dict = {}
            prescriptions: dict = {}
            if consultation_ids:
                cur.execute(
                    """
                    SELECT consultation_id, assessment, plan, signed_at
                    FROM soap_notes
                    WHERE consultation_id = ANY(%s::uuid[]) AND status = 'signed'
                    """,
                    (consultation_ids,),
                )
                notes = {row[0]: row for row in cur.fetchall()}

                cur.execute(
                    """
                    SELECT consultation_id, content
                    FROM consult_clinical_items
                    WHERE consultation_id = ANY(%s::uuid[]) AND kind = 'prescription'
                      AND status = 'approved'
                    """,
                    (consultation_ids,),
                )
                prescriptions = {row[0]: row[1] for row in cur.fetchall()}

            documents: dict = {}
            if booking_ids:
                cur.execute(
                    f"""
                    WITH encounter_documents AS ({_ENCOUNTER_DOCUMENTS})
                    SELECT ed.booking_id::text, dc.document_id, dc.original_filename,
                           dc.document_type, dc.clinical_date
                    FROM encounter_documents ed
                    JOIN document_catalog dc ON dc.document_id = ed.document_id
                    WHERE ed.booking_id::text = ANY(%(bookings)s)
                    ORDER BY dc.created_at
                    """,
                    {"patient_id": patient_id, "bookings": booking_ids},
                )
                for row in cur.fetchall():
                    documents.setdefault(row[0], []).append({
                        "document_id": str(row[1]),
                        "original_filename": row[2],
                        "document_type": row[3],
                        "clinical_date": row[4].isoformat() if row[4] else None,
                    })

            standalone: dict = {}
            if standalone_ids:
                cur.execute(
                    """
                    SELECT dc.document_id, dc.original_filename, dc.document_type, dc.clinical_date,
                           dc.created_at,
                           (SELECT COUNT(*) FROM document_catalog o
                            WHERE o.user_id = dc.user_id AND o.ingestion_status = 'complete'
                              AND o.original_filename IS NOT DISTINCT FROM dc.original_filename
                              AND o.clinical_date IS NOT DISTINCT FROM dc.clinical_date
                              AND o.document_type IS NOT DISTINCT FROM dc.document_type)
                    FROM document_catalog dc
                    WHERE dc.document_id = ANY(%s) AND dc.user_id = %s
                    """,
                    (standalone_ids, patient_id),
                )
                standalone = {row[0]: row for row in cur.fetchall()}
        conn.commit()

    items = []
    for kind, at, item_id in ordered:
        if kind == "document":
            row = standalone.get(item_id)
            if row:
                items.append({
                    "kind": "document",
                    "at": at.isoformat() if at else None,
                    "document_id": str(row[0]),
                    "original_filename": row[1],
                    "document_type": row[2],
                    "clinical_date": row[3].isoformat() if row[3] else None,
                    "uploaded_at": row[4].isoformat() if row[4] else None,
                    "copies": int(row[5] or 1),
                })
            continue
        row = bookings.get(item_id)
        if row:
            items.append(_encounter(row, doctor_id, viewer_department, notes, prescriptions, documents))

    return {
        "items": items,
        "encounters": [item for item in items if item["kind"] == "encounter"],
        "next_cursor": ordered[-1][1].isoformat() if (has_more and ordered) else None,
        "has_more": has_more,
    }


def _encounter(row, doctor_id, viewer_department, notes, prescriptions, documents) -> dict:
    booking_id, start_time, status, booking_note, enc_doctor_id, doctor_name, dept, consult_id = row
    readable = may_read_note(viewer_department, dept)
    note_row = notes.get(consult_id)

    encounter = {
        "kind": "encounter",
        "booking_id": str(booking_id),
        "start_time": start_time.isoformat() if start_time else None,
        "status": status,
        "doctor_id": str(enc_doctor_id),
        "doctor_name": doctor_name,
        "department": dept,
        "is_own": str(enc_doctor_id) == str(doctor_id),
        # Withheld alongside the note: a booking note is the pre-visit clinical
        # summary and is exactly as sensitive as the note itself.
        "reason": (booking_note or None) if readable else None,
        "restricted": not readable,
        "documents": documents.get(str(booking_id), []),
        "prescription": prescriptions.get(consult_id) if readable else None,
    }

    if note_row is None:
        # No SIGNED note. Distinct from restricted: one means nobody has signed
        # anything, the other means something exists and is being withheld.
        encounter["note"] = None
    elif readable:
        encounter["note"] = {
            "summary": _note_summary((note_row[1], note_row[2])),
            "signed_at": note_row[3].isoformat() if note_row[3] else None,
        }
    else:
        encounter["note"] = {"restricted": True, "summary": RESTRICTED_NOTE_LABEL}
    return encounter


def get_timeline_filters(patient_id: str) -> dict:
    """The values that actually occur in this patient's history, and how they combine.

    `facets` is one row per (department, doctor) the patient has seen, with the document
    types attached to those visits; `unlinked_document_types` are the types of documents
    that belong to no visit. The page narrows its dropdowns from these — a department
    offers only its doctors, a department and doctor offer only the document types their
    visits hold — so no combination offered can come back empty.

    `departments`, `doctors` and `document_types` are the unfiltered lists, as before.
    """
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                WITH encounter_documents AS ({_ENCOUNTER_DOCUMENTS})
                SELECT d.department, b.doctor_id::text, d.name,
                       ARRAY_REMOVE(ARRAY_AGG(DISTINCT dc.document_type), NULL)
                FROM appointment_bookings b
                JOIN doctors d ON d.doctor_id = b.doctor_id
                LEFT JOIN encounter_documents ed ON ed.booking_id = b.booking_id
                LEFT JOIN document_catalog dc ON dc.document_id = ed.document_id
                WHERE b.patient_id = %(patient_id)s
                GROUP BY d.department, b.doctor_id, d.name
                ORDER BY d.department, d.name
                """,
                {"patient_id": patient_id},
            )
            rows = cur.fetchall()

            cur.execute(
                f"""
                WITH encounter_documents AS ({_ENCOUNTER_DOCUMENTS})
                SELECT DISTINCT dc.document_type
                FROM document_catalog dc
                WHERE dc.user_id = %(patient_id)s AND dc.ingestion_status = 'complete'
                  AND dc.document_type IS NOT NULL
                  AND dc.document_id NOT IN (SELECT document_id FROM encounter_documents)
                ORDER BY 1
                """,
                {"patient_id": patient_id},
            )
            unlinked = [row[0] for row in cur.fetchall()]
        conn.commit()

    facets = [
        {"department": row[0], "doctor_id": row[1], "doctor_name": row[2],
         "document_types": sorted(row[3] or [])}
        for row in rows
    ]
    return {
        "facets": facets,
        "unlinked_document_types": unlinked,
        "departments": sorted({facet["department"] for facet in facets if facet["department"]}),
        "doctors": [{"doctor_id": facet["doctor_id"], "name": facet["doctor_name"]} for facet in facets],
        # Only types that can actually match something — on a visit, or on their own.
        "document_types": sorted({t for facet in facets for t in facet["document_types"]} | set(unlinked)),
    }
