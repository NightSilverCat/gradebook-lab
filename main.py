"""Запуск обработки журнала успеваемости."""

from pathlib import Path

from calc import (
    calculate_student_results,
    calculate_subject_averages,
    calculate_unsatisfactory_counts,
    find_missing_grades,
    recommend_stipend_actions,
    select_final_attempts,
)
from data_io import read_csv, read_rules, validate_grades
from report import (
    print_stipend_recommendations,
    save_subject_chart,
    write_debtors,
    write_rating,
)


def main() -> None:
    """Проверить ведомость и посчитать итоги по каждому студенту."""
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"

    students = read_csv(data_dir / "students.csv")
    plan = read_csv(data_dir / "plan.csv")
    grades = read_csv(data_dir / "grades.csv")
    rules = read_rules(data_dir / "rules.json")
    valid_grades, errors, corrections = validate_grades(
        grades, students, plan, rules
    )
    final_attempts, attempt_problems = select_final_attempts(
        valid_grades, rules
    )
    missing = find_missing_grades(students, plan, final_attempts)
    student_results = calculate_student_results(
        students, plan, final_attempts, rules
    )
    subject_averages = calculate_subject_averages(plan, final_attempts)
    unsatisfactory_counts = calculate_unsatisfactory_counts(
        plan, final_attempts, rules
    )
    debtor_count = sum(bool(result["debts"]) for result in student_results)
    academic_count = sum(
        result["stipend_type"] == "академическая"
        for result in student_results
    )
    increased_count = sum(
        result["stipend_type"] == "повышенная"
        for result in student_results
    )
    stipend_fund = sum(
        result["stipend_amount"] for result in student_results
    )
    recommendations = []
    for student in student_results:
        advice = recommend_stipend_actions(
            student, plan, final_attempts, rules
        )
        if advice is not None:
            recommendations.append((student["fio"], advice))

    missing_problems = [
        f"{student_id}, {discipline}: нет допустимой итоговой оценки"
        for student_id, discipline in missing
    ]
    log_lines = errors + corrections + attempt_problems + missing_problems
    log_text = "\n".join(log_lines)
    if log_text:
        log_text += "\n"
    (project_dir / "errors.log").write_text(log_text, encoding="utf-8")
    write_rating(project_dir / "rating.csv", student_results)
    write_debtors(project_dir / "debtors.csv", student_results)
    save_subject_chart(
        project_dir / "average_by_subject.png", subject_averages
    )

    print(f"Студентов: {len(students)}")
    print(f"Дисциплин: {len(plan)}")
    print(f"Записей в ведомости: {len(grades)}")
    print(f"Допустимых попыток: {len(valid_grades)}")
    print(f"Ошибочных строк: {len(errors)}")
    print(f"Исправлений: {len(corrections)}")
    print(f"Итоговых оценок: {len(final_attempts)}")
    print(f"Дисциплин без допустимой оценки: {len(missing)}")
    print(f"Студентов с долгами: {debtor_count}")
    print(f"Академическая стипендия: {academic_count}")
    print(f"Повышенная стипендия: {increased_count}")
    print(f"Стипендиальный фонд: {stipend_fund} руб.")
    print("Средний балл по дисциплинам:")
    for discipline, average in subject_averages.items():
        value = "не рассчитывается" if average is None else f"{average:.2f}"
        print(f"  {discipline}: {value}")
    print("Доля неудовлетворительных оценок по дисциплинам:")
    print("  Учитываются только выставленные итоговые оценки.")
    for discipline, (unsatisfactory, total) in (
        unsatisfactory_counts.items()
    ):
        if total:
            value = f"{unsatisfactory / total:.1%} ({unsatisfactory}/{total})"
        else:
            value = "не рассчитывается (0/0)"
        print(f"  {discipline}: {value}")
    print_stipend_recommendations(recommendations)
    print("Подробности: errors.log")
    print("Отчёты: rating.csv, debtors.csv, average_by_subject.png")


if __name__ == "__main__":
    main()
