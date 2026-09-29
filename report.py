"""Сохранение рейтинга и списка задолжников в CSV-файлы."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def rating_sort_key(student: dict) -> tuple[float, int, str]:
    """Задать порядок: средний балл, число долгов, затем ФИО."""
    average = student["average"]
    descending_average = (
        -average if average is not None else float("inf")
    )
    return (
        descending_average,
        len(student["debts"]),
        student["fio"].casefold(),
    )


def write_rating(path: Path, students: list[dict]) -> None:
    """Записать рейтинг всех студентов в CSV-файл."""
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["student_id", "fio", "average", "debt_count"])
        for student in sorted(students, key=rating_sort_key):
            average = student["average"]
            average_text = "" if average is None else f"{average:.2f}"
            writer.writerow(
                [
                    student["student_id"],
                    student["fio"],
                    average_text,
                    len(student["debts"]),
                ]
            )


def write_debtors(path: Path, students: list[dict]) -> None:
    """Записать студентов с долгами и названия дисциплин."""
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["student_id", "fio", "debts"])
        for student in students:
            if student["debts"]:
                writer.writerow(
                    [
                        student["student_id"],
                        student["fio"],
                        ", ".join(student["debts"]),
                    ]
                )


def save_subject_chart(
    path: Path, averages: dict[str, float | None]
) -> None:
    """Сохранить столбчатую диаграмму средних экзаменационных баллов."""
    subjects = [
        (name, average)
        for name, average in averages.items()
        if average is not None
    ]
    figure, axis = plt.subplots(figsize=(10, 5))
    if subjects:
        names, values = zip(*subjects)
        bars = axis.bar(names, values, color="#3274a1")
        axis.set_ylabel("Средний балл")
        axis.set_ylim(0, max(values) * 1.15)
        axis.bar_label(bars, fmt="%.2f", padding=3)
        axis.tick_params(axis="x", labelrotation=20)
        for label in axis.get_xticklabels():
            label.set_horizontalalignment("right")
    else:
        axis.text(0.5, 0.5, "Нет числовых оценок", ha="center")
        axis.set_axis_off()

    axis.set_title("Средний балл по экзаменационным дисциплинам")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def print_stipend_recommendations(
    recommendations: list[tuple[str, str]]
) -> None:
    """Показать рекомендации студентам понятными фразами."""
    print("Что нужно для стипендии:")
    for fio, recommendation in recommendations:
        print(f"  {fio}: {recommendation}")
