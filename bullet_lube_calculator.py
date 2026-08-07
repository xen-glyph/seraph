#!/usr/bin/env python3
"""
Bullet Lube Calculator v1.2.0

A dependency-free terminal calculator for percentage-based bullet lube recipes.
It calculates ingredient weights, saves reusable recipes, and exports clean
plain-text batch sheets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

APP_NAME = "Bullet Lube Calculator"
VERSION = "1.2.0"
HEADER_WIDTH = 76

UNITS = {
    "1": "lb",
    "2": "oz",
    "3": "kg",
    "4": "g",
}

UNIT_ALIASES = {
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "gram": "g",
    "grams": "g",
}

GRAMS_PER_UNIT = {
    "lb": Decimal("453.59237"),
    "oz": Decimal("28.349523125"),
    "kg": Decimal("1000"),
    "g": Decimal("1"),
}

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
RESET = ""
BOLD = ""
BORDER = ""
TITLE = ""
BLUE = ""
ACCENT = ""


def configure_theme(use_color: bool) -> None:
    """Configure ANSI colors without affecting exported text."""
    global USE_COLOR, RESET, BOLD, BORDER, TITLE, BLUE, ACCENT
    USE_COLOR = bool(use_color)
    RESET = "\033[0m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    BORDER = "\033[1;37m" if USE_COLOR else ""   # bold white
    TITLE = "\033[1;32m" if USE_COLOR else ""    # bold green
    BLUE = "\033[1;34m" if USE_COLOR else ""     # bold blue
    ACCENT = "\033[1;32m" if USE_COLOR else ""   # bold green


def get_data_dir() -> Path:
    """Return a sensible per-user data directory on Linux, macOS, or Windows."""
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "BulletLubeCalculator"
        return Path.home() / "AppData" / "Local" / "BulletLubeCalculator"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "bullet-lube-calculator"

    return Path.home() / ".local" / "share" / "bullet-lube-calculator"


DATA_DIR = get_data_dir()
RECIPE_FILE = DATA_DIR / "recipes.json"

RecipeStore = Dict[str, List[Dict[str, str]]]
IngredientList = List[Tuple[str, Decimal]]
CalculatedRows = List[Tuple[str, Decimal, Decimal]]


# ---------- BASIC HELPERS ----------


def clear() -> None:
    if sys.stdout.isatty() and os.environ.get("TERM"):
        os.system("cls" if os.name == "nt" else "clear")


def pause() -> None:
    input(f"\n{BLUE}Press Enter to continue...{RESET}")


def clean_title(title: str) -> str:
    title = str(title).replace("=", "").replace("—", "").strip()
    return " ".join(title.split())


def print_border() -> None:
    print(f"{BORDER}{'—' * HEADER_WIDTH}{RESET}")


def print_header(title: str) -> None:
    clear()
    title = clean_title(title)
    if len(title) > HEADER_WIDTH:
        title = title[: HEADER_WIDTH - 1].rstrip() + "…"
    print_border()
    print(f"{TITLE}{title.center(HEADER_WIDTH)}{RESET}")
    print_border()
    print()


def styled_prompt(text: str) -> str:
    return input(f"{BLUE}{text}{RESET}")


def decimal_input(prompt: str, minimum: Optional[Decimal] = None) -> Decimal:
    while True:
        raw = styled_prompt(prompt).strip().replace(",", "")
        try:
            value = Decimal(raw)
        except InvalidOperation:
            print(f"{TITLE}Please enter a valid number.{RESET}")
            continue

        if minimum is not None and value < minimum:
            print(f"{TITLE}Please enter a value of at least {minimum}.{RESET}")
            continue
        return value


def choose_unit() -> str:
    print("Select the batch-weight unit:")
    print()
    print(f"{BLUE}1){RESET} Pounds (lb)")
    print(f"{BLUE}2){RESET} Ounces (oz)")
    print(f"{BLUE}3){RESET} Kilograms (kg)")
    print(f"{BLUE}4){RESET} Grams (g)")

    while True:
        choice = styled_prompt("\nUnit: ").strip().lower()
        if choice in UNITS:
            return UNITS[choice]
        if choice in UNIT_ALIASES:
            return UNIT_ALIASES[choice]
        print(f"{TITLE}Choose 1-4 or enter lb, oz, kg, or g.{RESET}")


def format_decimal(value: Decimal, places: int) -> str:
    quantum = Decimal("1").scaleb(-places)
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    text = f"{rounded:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def format_weight(grams: Decimal, unit: str) -> str:
    value = grams / GRAMS_PER_UNIT[unit]
    places = {"lb": 4, "oz": 3, "kg": 4, "g": 2}[unit]
    return f"{format_decimal(value, places)} {unit}"


def clipped(text: str, width: int) -> str:
    text = str(text)
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "bullet-lube-recipe"


# ---------- RECIPE STORAGE ----------


def load_recipes() -> RecipeStore:
    if not RECIPE_FILE.exists():
        return {}

    try:
        with RECIPE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass

    return {}


def save_recipes(recipes: RecipeStore) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = RECIPE_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as handle:
        json.dump(recipes, handle, indent=2, ensure_ascii=False)
    temp_file.replace(RECIPE_FILE)


def find_recipe_key(recipes: RecipeStore, name: str) -> Optional[str]:
    lowered = name.casefold()
    for existing_name in recipes:
        if existing_name.casefold() == lowered:
            return existing_name
    return None


# ---------- CALCULATION / REPORT ----------


def enter_ingredients() -> IngredientList:
    while True:
        ingredients: IngredientList = []
        running_total = Decimal("0")

        print()
        print("Enter ingredients one at a time.")
        print("Leave the ingredient name blank when finished.")
        print()

        while True:
            name = styled_prompt("Ingredient name: ").strip()
            if not name:
                if not ingredients:
                    print(f"{TITLE}Enter at least one ingredient.{RESET}")
                    continue
                break

            if any(existing.casefold() == name.casefold() for existing, _ in ingredients):
                print(f"{TITLE}That ingredient has already been entered.{RESET}")
                continue

            percent = decimal_input(
                f"Percentage for {name}: ",
                minimum=Decimal("0.0001"),
            )

            if running_total + percent > Decimal("100"):
                attempted = format_decimal(running_total + percent, 4)
                print(f"{TITLE}That would bring the total to {attempted}%.{RESET}")
                print(f"{TITLE}Percentages cannot exceed 100%.{RESET}")
                continue

            ingredients.append((name, percent))
            running_total += percent
            print(
                f"Running total: "
                f"{ACCENT}{format_decimal(running_total, 4)}%{RESET}\n"
            )

            if running_total == Decimal("100"):
                print(f"{ACCENT}Percentages total 100%.{RESET}")
                break

        if running_total == Decimal("100"):
            return ingredients

        print()
        print(
            f"The percentages total "
            f"{format_decimal(running_total, 4)}%, not 100%."
        )
        choice = styled_prompt("Re-enter the ingredient list? [Y/n]: ").strip().lower()
        if choice in ("", "y", "yes"):
            continue
        print("Recipe entry cancelled.")
        return []


def calculate_rows(
    total_amount: Decimal,
    input_unit: str,
    ingredients: Sequence[Tuple[str, Decimal]],
) -> Tuple[Decimal, CalculatedRows]:
    total_grams = total_amount * GRAMS_PER_UNIT[input_unit]
    rows = [
        (name, percent, total_grams * percent / Decimal("100"))
        for name, percent in ingredients
    ]
    return total_grams, rows


def table_lines(
    total_grams: Decimal,
    input_unit: str,
    rows: CalculatedRows,
) -> List[str]:
    # 74 visible characters, safely inside a 76-column terminal or text page.
    name_w = 24
    percent_w = 8
    primary_w = 12
    ounces_w = 10
    grams_w = 12

    header = (
        f"{'INGREDIENT':<{name_w}}  "
        f"{'PERCENT':>{percent_w}}  "
        f"{'PRIMARY':>{primary_w}}  "
        f"{'OUNCES':>{ounces_w}}  "
        f"{'GRAMS':>{grams_w}}"
    )
    rule = (
        f"{'-' * name_w}  "
        f"{'-' * percent_w}  "
        f"{'-' * primary_w}  "
        f"{'-' * ounces_w}  "
        f"{'-' * grams_w}"
    )

    lines = [header, rule]
    for name, percent, ingredient_grams in rows:
        lines.append(
            f"{clipped(name, name_w):<{name_w}}  "
            f"{format_decimal(percent, 4) + '%':>{percent_w}}  "
            f"{format_weight(ingredient_grams, input_unit):>{primary_w}}  "
            f"{format_weight(ingredient_grams, 'oz'):>{ounces_w}}  "
            f"{format_weight(ingredient_grams, 'g'):>{grams_w}}"
        )

    lines.extend(
        [
            rule,
            (
                f"{'TOTAL':<{name_w}}  "
                f"{'100%':>{percent_w}}  "
                f"{format_weight(total_grams, input_unit):>{primary_w}}  "
                f"{format_weight(total_grams, 'oz'):>{ounces_w}}  "
                f"{format_weight(total_grams, 'g'):>{grams_w}}"
            ),
        ]
    )
    return lines


def build_report_lines(
    recipe_name: str,
    total_amount: Decimal,
    input_unit: str,
    ingredients: Sequence[Tuple[str, Decimal]],
    prepared_at: Optional[datetime] = None,
) -> List[str]:
    total_grams, rows = calculate_rows(total_amount, input_unit, ingredients)
    title = recipe_name or "Unnamed Bullet Lube Recipe"
    divider = "—" * HEADER_WIDTH
    prepared = prepared_at or datetime.now()

    lines = [
        divider,
        "BULLET LUBE RECIPE".center(HEADER_WIDTH),
        divider,
        "",
        f"Recipe:     {clipped(title, 64)}",
        f"Batch size: {format_weight(total_grams, input_unit)}",
        f"Metric:     {format_weight(total_grams, 'g')}",
        f"Imperial:   {format_weight(total_grams, 'oz')}",
        f"Prepared:   {prepared.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    lines.extend(table_lines(total_grams, input_unit, rows))
    lines.extend(
        [
            "",
            "Formula: ingredient weight = batch weight x percentage / 100",
            "",
            divider,
        ]
    )
    return lines


def display_results(
    recipe_name: str,
    total_amount: Decimal,
    input_unit: str,
    ingredients: IngredientList,
) -> None:
    total_grams, rows = calculate_rows(total_amount, input_unit, ingredients)
    title = recipe_name or "Unnamed Bullet Lube Recipe"

    print_header("Bullet Lube Calculator — Results")
    print(f"Recipe:     {ACCENT}{title}{RESET}")
    print(f"Batch size: {ACCENT}{format_weight(total_grams, input_unit)}{RESET}")
    print(f"Metric:     {ACCENT}{format_weight(total_grams, 'g')}{RESET}")
    print(f"Imperial:   {ACCENT}{format_weight(total_grams, 'oz')}{RESET}")
    print()

    for line in table_lines(total_grams, input_unit, rows):
        print(line)

    print()
    print("Formula: ingredient weight = batch weight x percentage / 100")


def default_export_filename(
    recipe_name: str,
    total_amount: Decimal,
    input_unit: str,
) -> str:
    recipe_part = slugify(recipe_name or "bullet-lube-recipe")
    amount_part = slugify(format_decimal(total_amount, 4))
    return f"{recipe_part}-{amount_part}-{input_unit}.txt"


def export_report(
    recipe_name: str,
    total_amount: Decimal,
    input_unit: str,
    ingredients: IngredientList,
) -> bool:
    default_name = default_export_filename(recipe_name, total_amount, input_unit)
    default_path = Path.cwd() / default_name

    print()
    print("Export the current batch as a plain-text recipe sheet.")
    print(f"Default: {default_path}")
    raw_path = styled_prompt("Output path (press Enter for default): ").strip()

    if raw_path:
        output_path = Path(os.path.expandvars(raw_path)).expanduser()
        if output_path.exists() and output_path.is_dir():
            output_path = output_path / default_name
        elif raw_path.endswith(("/", "\\")):
            output_path = output_path / default_name
        elif output_path.suffix == "":
            output_path = output_path.with_suffix(".txt")
    else:
        output_path = default_path

    if output_path.exists():
        overwrite = styled_prompt(
            f'"{output_path}" already exists. Overwrite it? [y/N]: '
        ).strip().lower()
        if overwrite not in ("y", "yes"):
            print("Export cancelled.")
            return False

    report = "\n".join(
        build_report_lines(recipe_name, total_amount, input_unit, ingredients)
    ) + "\n"

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    except OSError as exc:
        print(f"{TITLE}Could not export the text file: {exc}{RESET}")
        return False

    print(f"{ACCENT}Recipe sheet exported successfully.{RESET}")
    print(output_path.resolve())
    return True


# ---------- RESULT ACTIONS ----------


def result_actions(
    recipe_name: str,
    total_amount: Decimal,
    input_unit: str,
    ingredients: IngredientList,
    allow_save: bool,
) -> None:
    while True:
        print()
        print(f"{BLUE}r){RESET} Recalculate batch size")
        print(f"{BLUE}e){RESET} Export current batch as a text file")
        if allow_save:
            print(f"{BLUE}s){RESET} Save recipe percentages")
        print(f"{BLUE}b){RESET} Back to main menu")

        choice = styled_prompt("\nSelect: ").strip().lower()

        if choice in ("r", "recalculate"):
            print_header("Recalculate Batch Size")
            total_amount = decimal_input(
                "Desired total batch weight: ",
                minimum=Decimal("0.0001"),
            )
            print()
            input_unit = choose_unit()
            display_results(recipe_name, total_amount, input_unit, ingredients)
            continue

        if choice in ("e", "export", "text"):
            export_report(recipe_name, total_amount, input_unit, ingredients)
            continue

        if allow_save and choice in ("s", "save"):
            name = recipe_name.strip()
            if not name:
                name = styled_prompt("Recipe name to save: ").strip()
            if not name:
                print(f"{TITLE}A recipe name is required to save.{RESET}")
                continue

            recipes = load_recipes()
            existing_key = find_recipe_key(recipes, name)
            if existing_key is not None:
                overwrite = styled_prompt(
                    f'"{existing_key}" already exists. Overwrite it? [y/N]: '
                ).strip().lower()
                if overwrite not in ("y", "yes"):
                    print("Recipe was not overwritten.")
                    continue
                if existing_key != name:
                    del recipes[existing_key]

            recipes[name] = [
                {"name": ingredient, "percent": str(percent)}
                for ingredient, percent in ingredients
            ]
            try:
                save_recipes(recipes)
                print(f'{ACCENT}Recipe saved as "{name}".{RESET}')
                allow_save = False
                recipe_name = name
            except OSError as exc:
                print(f"{TITLE}Could not save recipe: {exc}{RESET}")
            continue

        if choice in ("b", "back", "m", "menu", ""):
            return

        valid = "r, e, s, or b" if allow_save else "r, e, or b"
        print(f"{TITLE}Choose {valid}.{RESET}")


# ---------- MENU FUNCTIONS ----------


def calculate_new_recipe() -> None:
    print_header("New Bullet Lube Recipe")
    recipe_name = styled_prompt(
        "Optional recipe name (press Enter to skip): "
    ).strip()
    total_amount = decimal_input(
        "Desired total batch weight: ",
        minimum=Decimal("0.0001"),
    )
    print()
    input_unit = choose_unit()
    ingredients = enter_ingredients()
    if not ingredients:
        pause()
        return

    display_results(recipe_name, total_amount, input_unit, ingredients)
    result_actions(
        recipe_name,
        total_amount,
        input_unit,
        ingredients,
        allow_save=True,
    )


def select_saved_recipe() -> Optional[Tuple[str, IngredientList]]:
    recipes = load_recipes()
    if not recipes:
        print("No saved recipes were found.")
        pause()
        return None

    names = sorted(recipes, key=str.casefold)
    for index, name in enumerate(names, start=1):
        print(f"{BLUE}{index}){RESET} {name}")
    print()
    print(f"{BLUE}b){RESET} Back")

    while True:
        raw = styled_prompt("\nSelect: ").strip().lower()
        if raw in ("", "b", "back", "q", "quit"):
            return None
        try:
            index = int(raw)
        except ValueError:
            print(f"{TITLE}Enter a valid recipe number.{RESET}")
            continue
        if 1 <= index <= len(names):
            name = names[index - 1]
            try:
                ingredients = [
                    (item["name"], Decimal(item["percent"]))
                    for item in recipes[name]
                ]
            except (KeyError, InvalidOperation, TypeError):
                print(f"{TITLE}That saved recipe is damaged or invalid.{RESET}")
                pause()
                return None
            return name, ingredients
        print(f"{TITLE}Choose one of the listed recipe numbers.{RESET}")


def load_saved_recipe() -> None:
    print_header("Load Saved Recipe")
    selection = select_saved_recipe()
    if selection is None:
        return

    recipe_name, ingredients = selection
    print_header(recipe_name)
    total_amount = decimal_input(
        "Desired total batch weight: ",
        minimum=Decimal("0.0001"),
    )
    print()
    input_unit = choose_unit()

    display_results(recipe_name, total_amount, input_unit, ingredients)
    result_actions(
        recipe_name,
        total_amount,
        input_unit,
        ingredients,
        allow_save=False,
    )


def view_saved_recipes() -> None:
    print_header("Saved Bullet Lube Recipes")
    recipes = load_recipes()
    if not recipes:
        print("No saved recipes were found.")
        pause()
        return

    for name in sorted(recipes, key=str.casefold):
        print(f"{ACCENT}{name}{RESET}")
        print("—" * min(HEADER_WIDTH, max(12, len(name))))
        for item in recipes[name]:
            print(f"  {item.get('name', 'Unknown')}: {item.get('percent', '?')}%")
        print()

    print(f"Recipe data file: {RECIPE_FILE}")
    pause()


def delete_saved_recipe() -> None:
    print_header("Delete Saved Recipe")
    recipes = load_recipes()
    if not recipes:
        print("No saved recipes were found.")
        pause()
        return

    names = sorted(recipes, key=str.casefold)
    for index, name in enumerate(names, start=1):
        print(f"{BLUE}{index}){RESET} {name}")
    print()
    print(f"{BLUE}b){RESET} Back")

    raw = styled_prompt("\nSelect recipe to delete: ").strip().lower()
    if raw in ("", "b", "back", "q", "quit"):
        return

    try:
        index = int(raw)
        name = names[index - 1]
    except (ValueError, IndexError):
        print(f"{TITLE}Invalid recipe number.{RESET}")
        pause()
        return

    confirm = styled_prompt(f'Delete "{name}"? [y/N]: ').strip().lower()
    if confirm not in ("y", "yes"):
        print("Nothing was deleted.")
        pause()
        return

    del recipes[name]
    try:
        save_recipes(recipes)
        print(f'{ACCENT}Deleted "{name}".{RESET}')
    except OSError as exc:
        print(f"{TITLE}Could not update the recipe file: {exc}{RESET}")
    pause()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate ingredient weights for percentage-based bullet lube recipes."
        )
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI terminal colors",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_arg_parser().parse_args(argv)
    configure_theme(USE_COLOR and not args.no_color)

    while True:
        print_header(f"{APP_NAME} v{VERSION}")
        print(f"{BLUE}1){RESET} Calculate a new recipe")
        print(f"{BLUE}2){RESET} Load a saved recipe")
        print(f"{BLUE}3){RESET} View saved recipes")
        print(f"{BLUE}4){RESET} Delete a saved recipe")
        print()
        print(f"{BLUE}q){RESET} Quit")

        choice = styled_prompt("\nSelect: ").strip().lower()

        if choice in ("1", "new", "calculate"):
            calculate_new_recipe()
        elif choice in ("2", "load"):
            load_saved_recipe()
        elif choice in ("3", "view", "list"):
            view_saved_recipes()
        elif choice in ("4", "delete", "remove"):
            delete_saved_recipe()
        elif choice in ("q", "quit", "exit"):
            clear()
            return
        else:
            print(f"{TITLE}Choose 1-4 or q.{RESET}")
            pause()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nBullet Lube Calculator closed.")
        sys.exit(0)
