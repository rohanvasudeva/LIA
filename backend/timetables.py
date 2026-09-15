import re
from datetime import datetime
from pathlib import Path

import pymupdf


PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_DIR / "data" / "pdfs"

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday")
DAY_ALIASES = {
    "mon": "monday",
    "tue": "tuesday",
    "wed": "wednesday",
    "thu": "thursday",
    "fri": "friday",
    "sat": "saturday",
}
YEAR_ALIASES = {
    "second": 2,
    "2nd": 2,
    "ii": 2,
    "third": 3,
    "3rd": 3,
    "iii": 3,
    "fourth": 4,
    "4th": 4,
    "iv": 4,
}
IGNORED_SUBJECTS = {"", "B", "R", "E", "A", "K", "L", "U", "N", "C", "H"}

_cache = {"signature": None, "records": []}


def _normalise_year(value):
    return {"II": 2, "III": 3, "IV": 4}.get(value.upper())


def _normalise_branch(value):
    value = re.sub(r"\s+", "", value.upper()).replace("_", "-")
    return value.strip("-")


def _normalise_time(value):
    match = re.search(r"\b(\d{1,2})[.:](\d{2})\b", value or "")
    if not match:
        return None
    return f"{int(match.group(1))}:{match.group(2)}"


def _room(value):
    match = re.search(
        r"\b([A-Z]{3,4})\s*[- ]\s*(\d{1,3})\b", value.upper()
    )
    return f"{match.group(1)}-{match.group(2)}" if match else None


def _metadata(text):
    match = re.search(
        r"YEAR\s*&?\s*SEM\s*:?\s*"
        r"(II|III|IV)\s*-\s*I\s*\(?\s*([A-Z]{2,5})\s*[- ]?\s*([A-Z])?\s*\)?",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None, None, None
    branch = _normalise_branch(match.group(2) + (f"-{match.group(3)}" if match.group(3) else ""))
    room_match = re.search(r"(?:CLASS\s*ROOM|ROOM\s*NO)\s*:?\s*([^\n]+)", text, re.IGNORECASE)
    return _normalise_year(match.group(1)), branch, (_room(room_match.group(1)) if room_match else None)


def _table_metadata(page, table):
    extracted = table.extract()
    header_text = "\n".join(
        " ".join(str(cell or "") for cell in row[:])
        for row in extracted[:2]
    )
    year, branch, room = _metadata(header_text)
    if year:
        return year, branch, room, extracted

    x0, y0, x1, _ = table.bbox
    clip = pymupdf.Rect(max(0, x0 - 100), max(0, y0 - 28), x1 + 8, y0 + 4)
    nearby = page.get_text("text", clip=clip)
    year, branch, room = _metadata(nearby)
    if year:
        return year, branch, room, extracted
    return None


def _cell_subject(value):
    raw_value = str(value or "")
    value = re.sub(r"\s+", " ", raw_value).strip()
    if not value:
        return None, None
    cell_room = _room(value)
    subject = re.sub(r"\s*\(?[A-Z]{3,4}\s*[- ]\s*\d{1,3}\)?", "", value)
    subject = subject.strip(" ()")
    if "\n" in raw_value:
        subject = raw_value.splitlines()[0].strip()
    subject = re.sub(r"\s+", " ", subject).strip()
    compact_subject = re.sub(r"\s+", "", subject.upper())
    if (
        subject.upper() in IGNORED_SUBJECTS
        or compact_subject in {"BREAK", "LUNCH"}
        or compact_subject in {"E", "R", "A", "K"}
    ):
        return None, cell_room
    if compact_subject == "ADS":
        subject = "ADSA"
    return subject or None, cell_room


def _records_from_table(page, table):
    metadata = _table_metadata(page, table)
    if not metadata:
        return []
    year, branch, default_room, rows = metadata
    day_row_index = next(
        (
            index for index, row in enumerate(rows[:3])
            if any(str(cell or "").strip().upper() == "DAY" for cell in row)
        ),
        None,
    )
    if day_row_index is None or len(rows) <= day_row_index + 1:
        return []

    header_rows = rows[:day_row_index]
    times = []
    for column in range(1, max(len(row) for row in rows[:2])):
        value = next(
            (
                str(row[column]).strip()
                for row in header_rows
                if column < len(row) and str(row[column] or "").strip()
            ),
            "",
        )
        times.append(_normalise_time(value))

    records = []
    for row in rows[day_row_index + 1:]:
        if not row:
            continue
        day = DAY_ALIASES.get(str(row[0] or "").strip().lower())
        if not day:
            continue
        for index, value in enumerate(row[1:]):
            if index >= len(times):
                continue
            subject, cell_room = _cell_subject(value)
            if subject:
                records.append({
                    "year": year,
                    "branch": branch,
                    "room": cell_room or default_room,
                    "day": day,
                    "time": times[index],
                    "subject": subject,
                })
    return records


def _load_records():
    files = sorted(PDF_DIR.glob("*.pdf"))
    signature = tuple((path.name, path.stat().st_mtime_ns) for path in files)
    if signature == _cache["signature"]:
        return _cache["records"]

    records = []
    for pdf_path in files:
        try:
            with pymupdf.open(pdf_path) as document:
                for page in document:
                    for table in page.find_tables().tables:
                        records.extend(_records_from_table(page, table))
        except (OSError, RuntimeError):
            continue

    _cache["signature"] = signature
    _cache["records"] = records
    return records


def _year(question):
    normalized = question.lower()
    for label, year in YEAR_ALIASES.items():
        if re.search(rf"\b{re.escape(label)}(?:\s*year)?\b", normalized):
            return year
    return None


def _branch(question):
    normalized = question.lower().replace(" ", "")
    match = re.search(r"(csm|cai|csd|aiml|cse)(?:-?([abc]))?", normalized)
    if not match:
        return None
    branch = f"{match.group(1)}-{match.group(2)}" if match.group(2) else match.group(1)
    return branch.upper()


def _day(question):
    normalized = question.lower()
    if re.search(r"\btoday\b", normalized):
        return datetime.now().strftime("%A").lower()
    return next((day for day in DAYS if re.search(rf"\b{day}\b", normalized)), None)


def _time(question):
    if re.search(r"\b(?:first|1st|one)\s+(?:hour|period)\b", question.lower()):
        return "first"
    return _normalise_time(question)


def _matches(records, year, branch):
    selected = [record for record in records if year is None or record["year"] == year]
    if branch:
        exact = [record for record in selected if record["branch"] == branch]
        if exact:
            return exact
        selected = [record for record in selected if record["branch"].startswith(branch + "-")]
    return selected


def _ordinal(year):
    return {2: "2nd", 3: "3rd", 4: "4th"}.get(year, f"{year}th")


def _scope(year, branch):
    if year:
        scope = f"{_ordinal(year)} year"
    else:
        scope = "the matching years"
    return f"{scope} {branch.upper()}" if branch else scope


def _answer_subjects(matches, year, branch):
    subjects = sorted({record["subject"] for record in matches})
    if not subjects:
        return None
    scope = _scope(year, branch)
    return f"Subjects for {scope}: {', '.join(subjects)}."


def _answer_rooms(matches, year, branch, day, time):
    if time == "first":
        time = next(
            (record["time"] for record in matches if record["time"]),
            None,
        )

    scoped = [
        record for record in matches
        if (not day or record["day"] == day)
        and (not time or record["time"] == time)
    ]
    if not scoped:
        return None

    scope = _scope(year, branch)

    if day and time:
        entries = []
        for record in scoped:
            label = record["room"] or "not specified"
            entries.append(f"{record['subject']} is in {label}")
        return f"For {scope} on {day.title()} at {time}: {'; '.join(entries)}."

    rows = []
    for record in scoped:
        room = record["room"] or "not specified"
        rows.append(f"{record['day'].title()} {record['time']}: {record['subject']} ({room})")
    return f"Classrooms for {scope}: {'; '.join(rows)}."


def _answer_subject_at_time(matches, year, branch, day, time):
    if time == "first":
        time = next(
            (record["time"] for record in matches if record["time"]),
            None,
        )

    scoped = [
        record for record in matches
        if (not day or record["day"] == day)
        and (not time or record["time"] == time)
    ]
    if not scoped:
        return None

    scope = _scope(year, branch)

    if day and time:
        entries = []
        for record in scoped:
            subject = record["subject"]
            entries.append(
                f"{_ordinal(record['year'])} year: {subject}"
                if not year
                else subject
            )
        return f"For {scope}, the {time} hour on {day.title()} is {'; '.join(entries)}."

    rows = [
        f"{record['day'].title()} {record['time']}: {record['subject']}"
        for record in scoped
    ]
    return f"Subjects for {scope} at {time}: {'; '.join(rows)}."


def _table_response(matches, year, branch, day):
    scoped = [
        record for record in matches
        if not day or record["day"] == day
    ]
    if not scoped:
        return None

    day_order = {name: index for index, name in enumerate(DAYS)}
    time_order = {}
    for record in matches:
        if record["time"] and record["time"] not in time_order:
            time_order[record["time"]] = len(time_order)
    scoped.sort(
        key=lambda record: (
            day_order.get(record["day"], 99),
            time_order.get(record["time"], 99),
        )
    )

    rows = [
        [
            record["day"].title(),
            record["time"] or "—",
            record["subject"],
            record["room"] or "Not specified",
        ]
        for record in scoped
    ]
    scope = _scope(year, branch)
    title = f"{scope} timetable"
    if day:
        title = f"{scope} timetable for {day.title()}"
    return {
        "answer": f"Here is the {title.lower()}.",
        "table": {
            "title": title,
            "columns": ["Day", "Time", "Subject", "Classroom"],
            "rows": rows,
        },
    }


def timetable_response(question):
    normalized = question.lower()
    year = _year(question)
    branch = _branch(question)
    asks_subjects = any(term in normalized for term in ("subject", "course", "what do", "have"))
    asks_room = any(term in normalized for term in ("classroom", "class room", "room no", "which room", "where"))
    asks_schedule = any(term in normalized for term in ("timetable", "time table", "hour", "period", "class"))
    requested_time = _time(question)
    day = _day(question)
    if not ((year or branch) and (asks_subjects or asks_room or asks_schedule or requested_time)):
        return None

    matches = _matches(_load_records(), year, branch)
    if not matches:
        return {
            "answer": f"I couldn't find timetable data for {_scope(year, branch)}."
        }

    if asks_schedule and not asks_room and not requested_time and not asks_subjects:
        return _table_response(matches, year, branch, day)

    if asks_room:
        return {"answer": _answer_rooms(matches, year, branch, day, requested_time)}

    if requested_time:
        return {"answer": _answer_subject_at_time(matches, year, branch, day, requested_time)}

    if asks_subjects:
        return {"answer": _answer_subjects(matches, year, branch)}

    return {"answer": _answer_subjects(matches, year, branch)}


def timetable_answer(question):
    response = timetable_response(question)
    return response["answer"] if response else None
