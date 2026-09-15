import re


DAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
)

YEAR_LABELS = {
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

# These are the first-period columns from the college timetable PDFs. Keeping
# them structured prevents retrieval from mixing adjacent branch panels.
FIRST_PERIODS = {
    2: {
        "csm-a": ["AI", "ADSA", "DLCO", "DMGT", "ADSA", "DMGT"],
        "csm-b": ["DMGT", "ADSA", "AI", "DMGT", "DLCO", "JAVA"],
        "csm-c": ["DLCO", "DMGT", "ADSA", "JAVA", "DMGT", "AI"],
        "cai-a": ["AI", "DLCO", "JAVA", "AI", "JAVA", "ADSA"],
        "cai-b": ["DMGT", "JAVA", "ADSA", "DLCO", "AI", "ADSA"],
        "cai-c": ["JAVA", "DLCO", "AI", "ADSA", "AI", "DMGT"],
        "csd-a": ["COA", "ADSA", "IDS", "JAVA", "ADSA", "COA"],
        "csd-b": ["JAVA", "DMGT", "COA", "JAVA", "IDS", "COA"],
    },
    3: {
        "csm-a": ["IRS", "SE", "RES", "IRS", "IRS", "SE"],
        "csm-b": ["RES", "OS", "OS", "CN", "RES", "SE"],
        "cai-a": ["ML", "CN", "CN", "SC", "RES", "SE"],
        "cai-b": ["CN", "RES", "SE", "SE", "RES", "ML"],
        "csd-a": ["OS", "RES", "OS", "CN", "SC", "SC"],
        "csd-b": ["RES", "SC", "SC", "DL", "DL", "SC"],
    },
    4: {
        "aiml": ["PE LAB", "BCT", "NPTEL", "ESIA", "PE LAB", "ESIA"],
        "cai": ["RL", "PE LAB", "NPTEL", "ESIA", "PE LAB", "ESIA"],
        "csm": ["PE LAB", "BCT", "NPTEL", "PE LAB", "HRPM", "BDA"],
        "csd": ["RL", "FSD-II LAB", "NPTEL(SWM)", "FSD-II LAB", "HRPM", "BDA"],
    },
}

ROOMS = {
    (2, "csd-b"): "AFF-5",
}

FULL_TIMETABLES = {
    (2, "csd-b"): {
        "monday": "9:00 JAVA; 10:00 COA; 11:15 DMGT; 12:15 COA; 2:15-5:00 IDS LAB (AFF-12)",
        "tuesday": "9:00 DMGT; 10:00 JAVA; 11:15 COA; 12:15 ADSA; 2:15 DMGT; 3:10 IDS; 4:05 LIB",
        "wednesday": "9:00 COA; 10:00 IDS; 11:15 JAVA; 12:15 ADSA; 2:15 DMGT; 3:10 JAVA; 4:05 SPORTS",
        "thursday": "9:00 JAVA; 10:00 ADSA; 11:15 PP LAB (AFF-12); 2:15 ADSA; 3:10 IDS; 4:05 COUN",
        "friday": "9:00 DMGT; 10:00 COA; 11:15 IDS; 12:15 ADSA; 2:15 JAVA; 3:10 IDS; 4:05 SEMI",
        "saturday": "9:00 IDS; 10:00 DMGT; 11:15 COA; 12:15 ADSA; 2:15 JAVA LAB (AFF-12)",
    }
}


def _ordinal(year):
    return {2: "2nd", 3: "3rd", 4: "4th"}.get(year, f"{year}th")


def _year(question):
    normalized = question.lower()
    for label, year in YEAR_LABELS.items():
        if re.search(rf"\b{re.escape(label)}(?:\s*year)?\b", normalized):
            return year
    return None


def _branch(question, year):
    normalized = question.lower()
    for branch in FIRST_PERIODS.get(year, {}):
        if re.search(rf"\b{re.escape(branch)}\b", normalized):
            return branch
    return None


def _day(question):
    normalized = question.lower()
    return next((day for day in DAY_NAMES if day in normalized), None)


def _is_first_period(question):
    return bool(re.search(r"\b(?:1st|first|one|1)\s*(?:hour|period)?\b", question.lower()))


def _format_full_timetable(year, branch):
    full = FULL_TIMETABLES.get((year, branch))
    if full:
        rows = "; ".join(f"{day.title()}: {value}" for day, value in full.items())
        room = ROOMS.get((year, branch))
        return f"{_ordinal(year)} year {branch.upper()} timetable (room {room}): {rows}."

    values = FIRST_PERIODS[year][branch]
    rows = "; ".join(
        f"{day.title()}: {subject}" for day, subject in zip(DAY_NAMES, values)
    )
    room = ROOMS.get((year, branch))
    room_text = f" Room: {room}." if room else ""
    return (
        f"First-hour timetable for {_ordinal(year)} year "
        f"{branch.upper()}.{room_text} {rows}."
    )


def timetable_answer(question):
    normalized = question.lower()
    if not (
        any(term in normalized for term in ("timetable", "hour", "period", "class"))
        or re.search(r"time\s*table", normalized)
    ):
        return None

    year = _year(question)
    branch = _branch(question, year) if year else None
    if year is None or branch is None:
        return None

    day = _day(question)
    if day and _is_first_period(question):
        index = DAY_NAMES.index(day)
        subject = FIRST_PERIODS[year][branch][index]
        return (
            f"For {_ordinal(year)} {branch.upper()}, "
            f"the first hour on {day.title()} is {subject}."
        )

    if re.search(r"time\s*table", normalized) and not day:
        return _format_full_timetable(year, branch)

    return None
