import csv
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SLOTS_PATH = ROOT / "appointment_slots.csv"
DOCTORS_PATH = ROOT / "doctors_roster.csv"
FIELDNAMES = [
    "slot_id",
    "doctor_id",
    "start_time",
    "end_time",
    "is_booked",
    "booked_by_patient_id",
]
SLOT_NAMESPACE = uuid.UUID("f39d4c77-59a4-4d9e-a3c3-5c4c6b6d9f10")


def working_day(day: date) -> bool:
    return day.weekday() < 6  # Monday through Saturday


def slot_times():
    starts = []
    for hour in range(9, 13):
        starts.append(time(hour, 0))
        starts.append(time(hour, 30))
    for hour in range(14, 17):
        starts.append(time(hour, 0))
        starts.append(time(hour, 30))
    return starts


def main():
    with DOCTORS_PATH.open(newline="", encoding="utf-8") as handle:
        doctors = list(csv.DictReader(handle))

    with SLOTS_PATH.open(newline="", encoding="utf-8") as handle:
        existing = list(csv.DictReader(handle))

    by_key = {(row["doctor_id"], row["start_time"]): row for row in existing}
    start_day = date(2026, 9, 1)
    end_day = date(2026, 10, 31)
    day = start_day
    added = 0
    while day <= end_day:
        if working_day(day):
            for doctor in doctors:
                for start_clock in slot_times():
                    start = datetime.combine(day, start_clock)
                    end = start + timedelta(minutes=30)
                    start_text = start.strftime("%Y-%m-%d %H:%M:%S")
                    key = (doctor["doctor_id"], start_text)
                    if key not in by_key:
                        by_key[key] = {
                            "slot_id": str(uuid.uuid5(SLOT_NAMESPACE, f"{key[0]}|{key[1]}")),
                            "doctor_id": doctor["doctor_id"],
                            "start_time": start_text,
                            "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
                            "is_booked": "False",
                            "booked_by_patient_id": "",
                        }
                        added += 1
        day += timedelta(days=1)

    rows = sorted(by_key.values(), key=lambda row: (row["start_time"], row["doctor_id"]))
    with SLOTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Added {added} slots; total slots: {len(rows)}")


if __name__ == "__main__":
    main()
