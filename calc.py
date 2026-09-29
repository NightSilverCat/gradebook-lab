"""Расчёты по проверенным записям журнала успеваемости."""


def select_final_attempts(
    grades: list[dict], rules: dict
) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """Выбрать одну попытку для каждой пары студент–дисциплина."""
    attempts_by_key = {}
    for grade in grades:
        key = (grade["student_id"], grade["discipline"])
        attempts_by_key.setdefault(key, []).append(grade)

    final_attempts = {}
    problems = []
    for key, attempts in attempts_by_key.items():
        student_id, discipline = key
        seen = set()
        for attempt in attempts:
            marker = (attempt["date"], attempt["grade"])
            if marker in seen:
                problems.append(
                    f"{student_id}, {discipline}: "
                    "повтор одной и той же попытки "
                    f"от {attempt['date']}"
                )
            seen.add(marker)

        if rules["last_attempt_counts"]:
            selected_date = max(attempt["date"] for attempt in attempts)
        else:
            selected_date = min(attempt["date"] for attempt in attempts)

        selected = [
            attempt for attempt in attempts
            if attempt["date"] == selected_date
        ]
        if len({attempt["grade"] for attempt in selected}) > 1:
            problems.append(
                f"{student_id}, {discipline}: разные оценки "
                f"за {selected_date}; итог не определён"
            )
            continue

        final_attempts[key] = selected[0]

    return final_attempts, problems


def find_missing_grades(
    students: list[dict[str, str]],
    plan: list[dict[str, str]],
    final_attempts: dict[tuple[str, str], dict],
) -> list[tuple[str, str]]:
    """Найти дисциплины без допустимой итоговой оценки."""
    missing = []
    for student in students:
        student_id = student["student_id"].strip()
        for subject in plan:
            discipline = subject["discipline"].strip()
            if (student_id, discipline) not in final_attempts:
                missing.append((student_id, discipline))
    return missing


def calculate_stipend(student_result: dict, rules: dict) -> tuple[str, int]:
    """Определить вид и сумму стипендии по правилам деканата."""
    if student_result["funding"] != rules["eligible_funding"]:
        return "нет", 0
    if student_result["debts"] or not student_result["exam_grades"]:
        return "нет", 0

    exam_grades = student_result["exam_grades"]
    increased = rules["stipend"]["increased"]
    if all(grade >= increased["min_grade"] for grade in exam_grades):
        return "повышенная", increased["amount"]

    academic = rules["stipend"]["academic"]
    if all(grade >= academic["min_grade"] for grade in exam_grades):
        return "академическая", academic["amount"]

    return "нет", 0


def calculate_student_results(
    students: list[dict[str, str]],
    plan: list[dict[str, str]],
    final_attempts: dict[tuple[str, str], dict],
    rules: dict,
) -> list[dict]:
    """Посчитать средний балл, долги и стипендию каждого студента."""
    failing_exam = min(rules["valid_grades"])
    failing_credit = next(
        mark for mark in rules["credit_values"]
        if mark.casefold().startswith("не")
    )
    results = []

    for student in students:
        student_id = student["student_id"].strip()
        exam_grades = []
        debts = []

        for subject in plan:
            discipline = subject["discipline"].strip()
            control_type = subject["type"].strip().casefold()
            attempt = final_attempts.get((student_id, discipline))

            if attempt is None:
                debts.append(discipline)
                continue

            grade = attempt["grade"]
            if grade == rules["absent_mark"]:
                debts.append(discipline)
            elif control_type == "экзамен":
                exam_grades.append(grade)
                if grade == failing_exam:
                    debts.append(discipline)
            elif control_type == "зачёт" and grade == failing_credit:
                debts.append(discipline)

        average = (
            sum(exam_grades) / len(exam_grades)
            if exam_grades else None
        )
        result = {
            "student_id": student_id,
            "fio": student["fio"].strip(),
            "funding": student["funding"].strip(),
            "exam_grades": exam_grades,
            "average": average,
            "debts": debts,
        }
        result["stipend_type"], result["stipend_amount"] = (
            calculate_stipend(result, rules)
        )
        results.append(result)

    return results


def calculate_subject_averages(
    plan: list[dict[str, str]],
    final_attempts: dict[tuple[str, str], dict],
) -> dict[str, float | None]:
    """Найти средний балл каждой экзаменационной дисциплины."""
    averages = {}
    for subject in plan:
        discipline = subject["discipline"].strip()
        if subject["type"].strip().casefold() != "экзамен":
            averages[discipline] = None
            continue

        grades = [
            attempt["grade"]
            for key, attempt in final_attempts.items()
            if key[1] == discipline
            and isinstance(attempt["grade"], int)
        ]
        averages[discipline] = (
            sum(grades) / len(grades) if grades else None
        )

    return averages


def calculate_unsatisfactory_counts(
    plan: list[dict[str, str]],
    final_attempts: dict[tuple[str, str], dict],
    rules: dict,
) -> dict[str, tuple[int, int]]:
    """Посчитать неудовлетворительные и все выставленные итоговые оценки."""
    failing_exam = min(rules["valid_grades"])
    failing_credit = next(
        mark for mark in rules["credit_values"]
        if mark.casefold().startswith("не")
    )
    counts = {}

    for subject in plan:
        discipline = subject["discipline"].strip()
        control_type = subject["type"].strip().casefold()
        grades = [
            attempt["grade"]
            for key, attempt in final_attempts.items()
            if key[1] == discipline
        ]

        if control_type == "экзамен":
            assessed = [
                grade for grade in grades if isinstance(grade, int)
            ]
            unsatisfactory = sum(
                grade == failing_exam for grade in assessed
            )
        elif control_type == "зачёт":
            assessed = [
                grade for grade in grades
                if grade in rules["credit_values"]
            ]
            unsatisfactory = sum(
                grade == failing_credit for grade in assessed
            )
        else:
            continue

        counts[discipline] = (unsatisfactory, len(assessed))

    return counts


def recommend_stipend_actions(
    student: dict,
    plan: list[dict[str, str]],
    final_attempts: dict[tuple[str, str], dict],
    rules: dict,
) -> str | None:
    """Назвать минимальные действия для следующего уровня стипендии."""
    if student["funding"] != rules["eligible_funding"]:
        return "не претендует"
    if student["stipend_type"] == "повышенная":
        return None

    if student["stipend_type"] == "академическая":
        goal = "повышенной стипендии"
        target_grade = rules["stipend"]["increased"]["min_grade"]
    else:
        goal = "академической стипендии"
        target_grade = rules["stipend"]["academic"]["min_grade"]

    actions = []
    for subject in plan:
        discipline = subject["discipline"].strip()
        control_type = subject["type"].strip().casefold()
        attempt = final_attempts.get((student["student_id"], discipline))

        if control_type == "зачёт":
            if discipline in student["debts"]:
                actions.append(
                    f"получить зачёт по дисциплине «{discipline}»"
                )
            continue

        if control_type == "экзамен":
            grade = attempt["grade"] if attempt is not None else None
            if not isinstance(grade, int):
                actions.append(
                    f"сдать экзамен по дисциплине "
                    f"«{discipline}» на {target_grade}"
                )
            elif grade < target_grade:
                actions.append(
                    f"пересдать экзамен по дисциплине "
                    f"«{discipline}» на {target_grade}"
                )

    if not actions:
        return "нет экзаменов или условий для перехода на следующий уровень"
    return f"Для {goal}: " + "; ".join(actions)
