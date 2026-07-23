import sys
from pathlib import Path
from typing import List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.analytics_service import AnalyticsService
from backend.services.experience_service import experience_service


def show_total_experiences() -> int:
    experiences = experience_service.get_all_experiences()
    print(f"Experiences: {len(experiences)}")
    return len(experiences)


def show_skill_growth() -> List[Tuple[str, int]]:
    experiences = experience_service.get_all_experiences()
    analytics = AnalyticsService(experiences)
    growth = analytics.get_skill_growth()
    print("Top Skill Growth:")
    if not growth:
        print("No growth data available")
        return []

    ranked_growth = sorted(growth.items(), key=lambda item: item[1], reverse=True)[:5]
    for skill, delta in ranked_growth:
        sign = "+" if delta >= 0 else ""
        print(f"{skill.title()} {sign}{delta}")
    return ranked_growth


def show_best_actions() -> List[Tuple[str, float]]:
    experiences = experience_service.get_all_experiences()
    analytics = AnalyticsService(experiences)
    results = analytics.get_most_effective_actions()
    print("Most Effective Actions:")
    if not results:
        print("No action data available")
        return []

    for index, (action, average_outcome) in enumerate(results[:5], start=1):
        print(f"{index}. {action:<20} {average_outcome:.2f}")
    return results


def show_worst_actions() -> List[Tuple[str, float]]:
    experiences = experience_service.get_all_experiences()
    analytics = AnalyticsService(experiences)
    results = analytics.get_most_effective_actions()
    print("Least Effective Actions:")
    if not results:
        print("No action data available")
        return []

    worst = sorted(results, key=lambda item: item[1])[:5]
    for index, (action, average_outcome) in enumerate(worst, start=1):
        print(f"{index}. {action:<20} {average_outcome:.2f}")
    return worst


def show_average_outcome() -> float:
    experiences = experience_service.get_all_experiences()
    analytics = AnalyticsService(experiences)
    average_outcome = analytics.get_average_outcome()
    print(f"Average Outcome: {average_outcome:.2f}")
    return average_outcome


def main() -> None:
    print("==================================")
    print("AURA GROWTH REPORT")
    print("==================================")
    print()
    show_total_experiences()
    print()
    show_skill_growth()
    print()
    show_best_actions()
    print()
    show_worst_actions()
    print()
    show_average_outcome()


if __name__ == "__main__":
    main()
