"""Чтение входных файлов журнала успеваемости."""

import csv
import json
from datetime import date
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    """Прочитать CSV с заголовками и вернуть строки как словари."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def read_rules(path: Path) -> dict:
    """Прочитать правила деканата из JSON-файла."""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def normalize_grade(
    raw_grade: str, control_type: str, rules: dict
) -> int | str:
    """Привести оценку к допустимому виду по правилам деканата."""
    value = raw_grade.strip().casefold()
    if not value:
        raise ValueError("пустая оценка")

    absent_mark = rules["absent_mark"]
    if value == absent_mark.casefold():
        return absent_mark

    if control_type == "экзамен":
        normalized = rules["grade_aliases"].get(value, value)
        if isinstance(normalized, str) and normalized.isdecimal():
            normalized = int(normalized)
        if normalized in rules["valid_grades"]:
            return normalized
        raise ValueError(f"недопустимая экзаменационная оценка {raw_grade!r}")

    if control_type == "зачёт":
        normalized = rules["credit_aliases"].get(value, value)
        if normalized in rules["credit_values"]:
            return normalized
        raise ValueError(f"недопустимая отметка о зачёте {raw_grade!r}")

    raise ValueError(f"неизвестный вид контроля {control_type!r}")


def validate_grades(
    rows: list[dict[str, str]],
    students: list[dict[str, str]],
    plan: list[dict[str, str]],
    rules: dict,
) -> tuple[list[dict], list[str], list[str]]:
    """Проверить ведомость и вернуть попытки, ошибки и исправления."""
    student_ids = {row["student_id"].strip() for row in students}
    control_types = {
        row["discipline"].strip(): row["type"].strip().casefold()
        for row in plan
    }
    valid_rows = []
    errors = []
    corrections = []

    for line_number, row in enumerate(rows, start=2):
        student_id = (row.get("student_id") or "").strip()
        discipline = (row.get("discipline") or "").strip()
        raw_date = (row.get("date") or "").strip()
        raw_grade = row.get("grade") or ""
        context = f"строка {line_number}: {student_id}, {discipline}"

        if None in row or any(value is None for value in row.values()):
            errors.append(f"{context}: неверное число столбцов")
            continue
        if student_id not in student_ids:
            errors.append(f"{context}: студент отсутствует в students.csv")
            continue
        if discipline not in control_types:
            errors.append(f"{context}: дисциплина отсутствует в plan.csv")
            continue

        try:
            attempt_date = date.fromisoformat(raw_date)
        except ValueError:
            errors.append(f"{context}: неверная дата {raw_date!r}")
            continue

        try:
            grade = normalize_grade(
                raw_grade, control_types[discipline], rules
            )
        except ValueError as error:
            errors.append(f"{context}: {error}")
            continue

        if str(grade) != raw_grade:
            corrections.append(
                f"{context}: замена оценки {raw_grade!r} на {grade!r}"
            )

        valid_rows.append(
            {
                "student_id": student_id,
                "discipline": discipline,
                "date": attempt_date,
                "grade": grade,
            }
        )

    return valid_rows, errors, corrections
