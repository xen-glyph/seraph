#!/usr/bin/env python3
"""
Cast Bullet Workshop Calculator v2.0.0

A dependency-free terminal workshop utility for:
  * percentage-based bullet lube recipes
  * established and custom cast-bullet alloy recipes
  * exact source-alloy blending to a target Pb/Sn/Sb composition
  * plain-text export and CUPS printing

The program uses Decimal arithmetic for predictable shop calculations and stores
user recipes outside the installation directory.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

getcontext().prec = 36

APP_NAME = "Cast Bullet Workshop Calculator"
VERSION = "2.0.0"
SCHEMA_VERSION = 2
HEADER_WIDTH = 76
DEFAULT_LEADING_BLANK_LINES = 2

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

METAL_NAMES = {
    "Pb": "Lead",
    "Sn": "Tin",
    "Sb": "Antimony",
}

METAL_SYMBOLS = {value.casefold(): key for key, value in METAL_NAMES.items()}
METAL_SYMBOLS.update({symbol.casefold(): symbol for symbol in METAL_NAMES})

# Traditional Pb:Sn recipes are stored as exact parts ratios. Their familiar
# commercial percentage labels are retained only as notes.
BUILTIN_ALLOYS: Dict[str, Dict[str, Any]] = {
    "Pure Lead": {
        "method": "percent",
        "components": {"Lead": "100"},
        "approx_bhn": "~5",
        "category": "Soft / traditional",
        "notes": "Nominally pure lead. Verify actual material purity before use.",
    },
    "40:1 Lead/Tin": {
        "method": "ratio",
        "parts": {"Lead": "40", "Tin": "1"},
        "commercial_label": "Common commercial label: 97.5% Pb / 2.5% Sn",
        "approx_bhn": "Not fixed",
        "category": "Soft / traditional",
        "notes": "Calculated as an exact 40 parts lead to 1 part tin ratio.",
    },
    "30:1 Lead/Tin": {
        "method": "ratio",
        "parts": {"Lead": "30", "Tin": "1"},
        "commercial_label": "Common commercial label: 97% Pb / 3% Sn",
        "approx_bhn": "~9",
        "category": "Soft / traditional",
        "notes": "Calculated as an exact 30 parts lead to 1 part tin ratio.",
    },
    "25:1 Lead/Tin": {
        "method": "ratio",
        "parts": {"Lead": "25", "Tin": "1"},
        "commercial_label": "Common commercial label: 96% Pb / 4% Sn",
        "approx_bhn": "~9",
        "category": "Soft / traditional",
        "notes": "Calculated as an exact 25 parts lead to 1 part tin ratio.",
    },
    "20:1 Lead/Tin": {
        "method": "ratio",
        "parts": {"Lead": "20", "Tin": "1"},
        "commercial_label": "Common commercial label: 95% Pb / 5% Sn",
        "approx_bhn": "~10",
        "category": "Soft / traditional",
        "notes": "Calculated as an exact 20 parts lead to 1 part tin ratio.",
    },
    "16:1 Lead/Tin": {
        "method": "ratio",
        "parts": {"Lead": "16", "Tin": "1"},
        "commercial_label": "Common commercial label: 94% Pb / 6% Sn",
        "approx_bhn": "~11",
        "category": "Soft / traditional",
        "notes": "Calculated as an exact 16 parts lead to 1 part tin ratio.",
    },
    "Lyman No. 2": {
        "method": "percent",
        "components": {"Lead": "90", "Tin": "5", "Antimony": "5"},
        "approx_bhn": "~16",
        "category": "General purpose / hard",
        "notes": "Established 90/5/5 lead-tin-antimony alloy.",
    },
    "Hardball": {
        "method": "percent",
        "components": {"Lead": "92", "Tin": "2", "Antimony": "6"},
        "approx_bhn": "~16",
        "category": "General purpose / hard",
        "notes": "Established 92/2/6 lead-tin-antimony alloy.",
    },
    "Linotype 84/4/12": {
        "method": "percent",
        "components": {"Lead": "84", "Tin": "4", "Antimony": "12"},
        "approx_bhn": "~22",
        "category": "General purpose / hard",
        "notes": "Known 84/4/12 linotype composition; generic type metal can vary.",
    },
}

BUILTIN_SOURCE_ALLOYS: Dict[str, Dict[str, Any]] = {
    "Pure Lead": {
        "composition": {"Pb": "100", "Sn": "0", "Sb": "0"},
        "notes": "Nominally pure lead.",
        "preference": 1,
    },
    "Pure Tin": {
        "composition": {"Pb": "0", "Sn": "100", "Sb": "0"},
        "notes": "Nominally pure tin.",
        "preference": 2,
    },
    "Pure Antimony": {
        "composition": {"Pb": "0", "Sn": "0", "Sb": "100"},
        "notes": "Nominally pure antimony; direct handling requires appropriate practice.",
        "preference": 10,
    },
    "Linotype 84/4/12": {
        "composition": {"Pb": "84", "Sn": "4", "Sb": "12"},
        "notes": "Known linotype source alloy.",
        "preference": 3,
    },
    "SuperHard 70/30": {
        "composition": {"Pb": "70", "Sn": "0", "Sb": "30"},
        "notes": "Concentrated antimony-bearing source alloy.",
        "preference": 5,
    },
    "Foundry Type 64.5/12.5/23": {
        "composition": {"Pb": "64.5", "Sn": "12.5", "Sb": "23"},
        "notes": "Tin- and antimony-rich source alloy.",
        "preference": 6,
    },
    "Antimonial Lead 94/6": {
        "composition": {"Pb": "94", "Sn": "0", "Sb": "6"},
        "notes": "Six-percent-antimony lead source alloy.",
        "preference": 4,
    },
}

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
RESET = ""
BOLD = ""
BORDER = ""
TITLE = ""
BLUE = ""
ACCENT = ""
WARNING = ""


def configure_theme(use_color: bool) -> None:
    global USE_COLOR, RESET, BOLD, BORDER, TITLE, BLUE, ACCENT, WARNING
    USE_COLOR = bool(use_color)
    RESET = "\033[0m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    BORDER = "\033[1;37m" if USE_COLOR else ""   # bold white
    TITLE = "\033[1;32m" if USE_COLOR else ""    # bold green
    BLUE = "\033[1;34m" if USE_COLOR else ""     # bold blue
    ACCENT = "\033[1;32m" if USE_COLOR else ""   # bold green
    WARNING = "\033[1;33m" if USE_COLOR else ""  # bold yellow


def get_data_dir() -> Path:
    override = os.environ.get("CBWC_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "CastBulletWorkshopCalculator"
        return Path.home() / "AppData" / "Local" / "CastBulletWorkshopCalculator"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "cast-bullet-workshop-calculator"
    return Path.home() / ".local" / "share" / "cast-bullet-workshop-calculator"


DATA_DIR = get_data_dir()
STORE_FILE = DATA_DIR / "workshop.json"
LAST_PRINT_FILE = DATA_DIR / "last_print_report.txt"

LEGACY_RECIPE_FILES = [
    Path.home() / ".local" / "share" / "bullet-lube-calculator" / "recipes.json",
    Path.home() / ".local" / "share" / "seraph" / "bullet_lube_recipes.json",
]

IngredientList = List[Tuple[str, Decimal]]
Composition = Dict[str, Decimal]


@dataclass
class ReportSpec:
    report_title: str
    recipe_name: str
    total_amount: Decimal
    input_unit: str
    rows: IngredientList
    info_lines: List[str] = field(default_factory=list)
    footer_lines: List[str] = field(default_factory=list)
    formula: str = "component weight = batch weight x percentage / 100"
    filename_prefix: str = "workshop-recipe"


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------


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


def print_header(title: str, clear_screen: bool = True) -> None:
    if clear_screen:
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


def yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    raw = styled_prompt(f"{prompt} {suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def decimal_input(
    prompt: str,
    minimum: Optional[Decimal] = None,
    maximum: Optional[Decimal] = None,
    allow_blank: bool = False,
    default: Optional[Decimal] = None,
) -> Optional[Decimal]:
    while True:
        raw = styled_prompt(prompt).strip().replace(",", "")
        if not raw and allow_blank:
            return default
        try:
            value = Decimal(raw)
        except InvalidOperation:
            print(f"{TITLE}Please enter a valid number.{RESET}")
            continue
        if minimum is not None and value < minimum:
            print(f"{TITLE}Please enter a value of at least {minimum}.{RESET}")
            continue
        if maximum is not None and value > maximum:
            print(f"{TITLE}Please enter a value no greater than {maximum}.{RESET}")
            continue
        return value


def integer_input(prompt: str, minimum: int, maximum: int) -> int:
    while True:
        raw = styled_prompt(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"{TITLE}Please enter a whole number.{RESET}")
            continue
        if value < minimum or value > maximum:
            print(f"{TITLE}Enter a number from {minimum} to {maximum}.{RESET}")
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


def format_decimal(value: Decimal, places: int = 4) -> str:
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
    return text or "workshop-recipe"


def wrap_text(text: str, width: int = HEADER_WIDTH) -> List[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: List[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def choose_from_names(
    title: str,
    names: Sequence[str],
    descriptions: Optional[Mapping[str, str]] = None,
) -> Optional[str]:
    print_header(title)
    for index, name in enumerate(names, start=1):
        print(f"{BLUE}{index}){RESET} {name}")
        if descriptions and descriptions.get(name):
            for line in wrap_text(descriptions[name], HEADER_WIDTH - 4):
                print(f"    {line}")
    print()
    print(f"{BLUE}b){RESET} Back")
    while True:
        raw = styled_prompt("\nSelect: ").strip().lower()
        if raw in {"", "b", "back", "q", "quit"}:
            return None
        try:
            index = int(raw)
        except ValueError:
            print(f"{TITLE}Enter one of the listed numbers.{RESET}")
            continue
        if 1 <= index <= len(names):
            return names[index - 1]
        print(f"{TITLE}Choose one of the listed numbers.{RESET}")


# ---------------------------------------------------------------------------
# Storage and migration
# ---------------------------------------------------------------------------


def default_store() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "lube_recipes": {},
        "alloy_recipes": {},
        "source_alloys": {},
        "settings": {
            "printer_queue": "",
            "leading_blank_lines": DEFAULT_LEADING_BLANK_LINES,
        },
        "migration": {
            "legacy_lube_checked": False,
            "legacy_lube_imported": 0,
        },
    }


def normalize_store(raw: Any) -> Dict[str, Any]:
    store = default_store()
    if not isinstance(raw, dict):
        return store
    for section in ("lube_recipes", "alloy_recipes", "source_alloys"):
        if isinstance(raw.get(section), dict):
            store[section] = raw[section]
    if isinstance(raw.get("settings"), dict):
        store["settings"].update(raw["settings"])
    if isinstance(raw.get("migration"), dict):
        store["migration"].update(raw["migration"])
    store["schema_version"] = SCHEMA_VERSION
    try:
        lines = int(store["settings"].get("leading_blank_lines", DEFAULT_LEADING_BLANK_LINES))
    except (TypeError, ValueError):
        lines = DEFAULT_LEADING_BLANK_LINES
    store["settings"]["leading_blank_lines"] = max(0, min(10, lines))
    queue = store["settings"].get("printer_queue", "")
    store["settings"]["printer_queue"] = str(queue or "")
    return store


def load_store() -> Dict[str, Any]:
    if not STORE_FILE.exists():
        return default_store()
    try:
        with STORE_FILE.open("r", encoding="utf-8") as handle:
            return normalize_store(json.load(handle))
    except (OSError, json.JSONDecodeError):
        return default_store()


def save_store(store: Mapping[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = STORE_FILE.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(store, handle, indent=2, ensure_ascii=False)
    temp.replace(STORE_FILE)


def find_casefold_key(mapping: Mapping[str, Any], name: str) -> Optional[str]:
    target = name.casefold()
    for key in mapping:
        if key.casefold() == target:
            return key
    return None


def migrate_legacy_lube_recipes(store: Dict[str, Any]) -> Tuple[int, List[str]]:
    migration = store.setdefault("migration", {})
    if migration.get("legacy_lube_checked"):
        return 0, []
    imported = 0
    sources: List[str] = []
    lube_recipes = store.setdefault("lube_recipes", {})
    for path in LEGACY_RECIPE_FILES:
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        source_imported = 0
        for name, entries in raw.items():
            if find_casefold_key(lube_recipes, str(name)) is not None:
                continue
            if not isinstance(entries, list):
                continue
            ingredients: List[Dict[str, str]] = []
            total = Decimal("0")
            valid = True
            for entry in entries:
                try:
                    ingredient_name = str(entry["name"]).strip()
                    percent = Decimal(str(entry["percent"]))
                except (KeyError, InvalidOperation, TypeError):
                    valid = False
                    break
                if not ingredient_name or percent <= 0:
                    valid = False
                    break
                ingredients.append({"name": ingredient_name, "percent": str(percent)})
                total += percent
            if not valid or not ingredients or total != Decimal("100"):
                continue
            lube_recipes[str(name)] = {
                "ingredients": ingredients,
                "notes": f"Imported from legacy file: {path}",
            }
            imported += 1
            source_imported += 1
        if source_imported:
            sources.append(str(path))
    migration["legacy_lube_checked"] = True
    migration["legacy_lube_imported"] = int(migration.get("legacy_lube_imported", 0)) + imported
    save_store(store)
    return imported, sources


# ---------------------------------------------------------------------------
# Percentage, alloy, and report calculations
# ---------------------------------------------------------------------------


def normalize_percentages(values: Mapping[str, Decimal]) -> IngredientList:
    total = sum(values.values(), Decimal("0"))
    if total <= 0:
        raise ValueError("Percentage total must be greater than zero.")
    return [(name, value * Decimal("100") / total) for name, value in values.items()]


def alloy_components(alloy: Mapping[str, Any]) -> IngredientList:
    method = alloy.get("method")
    if method == "ratio":
        parts = {
            str(name): Decimal(str(value))
            for name, value in dict(alloy.get("parts", {})).items()
        }
        return normalize_percentages(parts)
    components = [
        (str(name), Decimal(str(value)))
        for name, value in dict(alloy.get("components", {})).items()
    ]
    total = sum((percent for _, percent in components), Decimal("0"))
    if total != Decimal("100"):
        raise ValueError(f"Alloy composition totals {total}%, not 100%.")
    return components


def component_list_to_metal_composition(components: IngredientList) -> Composition:
    composition: Composition = {"Pb": Decimal("0"), "Sn": Decimal("0"), "Sb": Decimal("0")}
    for name, percent in components:
        symbol = METAL_SYMBOLS.get(name.casefold())
        if symbol:
            composition[symbol] += percent
        elif percent != 0:
            raise ValueError(f"Blend calculations support only Lead, Tin, and Antimony; found {name}.")
    return composition


def calculate_rows(
    total_amount: Decimal,
    input_unit: str,
    components: Sequence[Tuple[str, Decimal]],
) -> Tuple[Decimal, List[Tuple[str, Decimal, Decimal]]]:
    total_grams = total_amount * GRAMS_PER_UNIT[input_unit]
    rows = [
        (name, percent, total_grams * percent / Decimal("100"))
        for name, percent in components
    ]
    return total_grams, rows


def table_lines(
    total_grams: Decimal,
    input_unit: str,
    rows: Sequence[Tuple[str, Decimal, Decimal]],
) -> List[str]:
    name_w = 24
    percent_w = 8
    primary_w = 12
    ounces_w = 10
    grams_w = 12
    header = (
        f"{'COMPONENT':<{name_w}}  "
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
    for name, percent, grams in rows:
        lines.append(
            f"{clipped(name, name_w):<{name_w}}  "
            f"{format_decimal(percent, 4) + '%':>{percent_w}}  "
            f"{format_weight(grams, input_unit):>{primary_w}}  "
            f"{format_weight(grams, 'oz'):>{ounces_w}}  "
            f"{format_weight(grams, 'g'):>{grams_w}}"
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


def build_report_lines(spec: ReportSpec, prepared_at: Optional[datetime] = None) -> List[str]:
    total_grams, calculated = calculate_rows(spec.total_amount, spec.input_unit, spec.rows)
    divider = "—" * HEADER_WIDTH
    prepared = prepared_at or datetime.now()
    lines = [
        divider,
        spec.report_title.upper().center(HEADER_WIDTH),
        divider,
        "",
        f"Recipe:     {clipped(spec.recipe_name or 'Unnamed Recipe', 64)}",
        f"Batch size: {format_weight(total_grams, spec.input_unit)}",
        f"Metric:     {format_weight(total_grams, 'g')}",
        f"Imperial:   {format_weight(total_grams, 'oz')}",
        f"Prepared:   {prepared.strftime('%Y-%m-%d %H:%M')}",
    ]
    if spec.info_lines:
        lines.append("")
        for info in spec.info_lines:
            lines.extend(wrap_text(info, HEADER_WIDTH))
    lines.append("")
    lines.extend(table_lines(total_grams, spec.input_unit, calculated))
    if spec.formula:
        lines.extend(["", f"Formula: {spec.formula}"])
    if spec.footer_lines:
        lines.append("")
        for footer in spec.footer_lines:
            lines.extend(wrap_text(footer, HEADER_WIDTH))
    lines.extend(["", divider])
    return lines


def report_text(spec: ReportSpec) -> str:
    return "\n".join(build_report_lines(spec)) + "\n"


def display_report(spec: ReportSpec) -> None:
    total_grams, calculated = calculate_rows(spec.total_amount, spec.input_unit, spec.rows)
    print_header(f"{spec.report_title} — Results")
    print(f"Recipe:     {ACCENT}{spec.recipe_name or 'Unnamed Recipe'}{RESET}")
    print(f"Batch size: {ACCENT}{format_weight(total_grams, spec.input_unit)}{RESET}")
    print(f"Metric:     {ACCENT}{format_weight(total_grams, 'g')}{RESET}")
    print(f"Imperial:   {ACCENT}{format_weight(total_grams, 'oz')}{RESET}")
    if spec.info_lines:
        print()
        for line in spec.info_lines:
            for wrapped in wrap_text(line, HEADER_WIDTH):
                print(wrapped)
    print()
    for line in table_lines(total_grams, spec.input_unit, calculated):
        print(line)
    if spec.formula:
        print()
        print(f"Formula: {spec.formula}")
    if spec.footer_lines:
        print()
        for line in spec.footer_lines:
            for wrapped in wrap_text(line, HEADER_WIDTH):
                print(wrapped)


def default_export_filename(spec: ReportSpec) -> str:
    name = slugify(spec.recipe_name or spec.filename_prefix)
    amount = slugify(format_decimal(spec.total_amount, 4))
    return f"{name}-{amount}-{spec.input_unit}.txt"


def export_report(spec: ReportSpec) -> bool:
    default_name = default_export_filename(spec)
    default_path = Path.cwd() / default_name
    print()
    print("Export the current calculation as a 76-column plain-text report.")
    print(f"Default: {default_path}")
    raw = styled_prompt("Output path (press Enter for default): ").strip()
    if raw:
        path = Path(os.path.expandvars(raw)).expanduser()
        if (path.exists() and path.is_dir()) or raw.endswith(("/", "\\")):
            path = path / default_name
        elif path.suffix == "":
            path = path.with_suffix(".txt")
    else:
        path = default_path
    if path.exists() and not yes_no(f'"{path}" exists. Overwrite it?', default=False):
        print("Export cancelled.")
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report_text(spec), encoding="utf-8")
    except OSError as exc:
        print(f"{TITLE}Could not export the report: {exc}{RESET}")
        return False
    print(f"{ACCENT}Text report exported successfully.{RESET}")
    print(path.resolve())
    return True


def prepare_print_text(spec: ReportSpec, leading_blank_lines: int) -> str:
    return ("\n" * max(0, leading_blank_lines)) + report_text(spec)


def print_report(spec: ReportSpec, store: Dict[str, Any]) -> bool:
    settings = store.setdefault("settings", {})
    queue = str(settings.get("printer_queue", "") or "").strip()
    try:
        leading = int(settings.get("leading_blank_lines", DEFAULT_LEADING_BLANK_LINES))
    except (TypeError, ValueError):
        leading = DEFAULT_LEADING_BLANK_LINES
    document = prepare_print_text(spec, leading)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LAST_PRINT_FILE.write_text(document, encoding="utf-8")
    except OSError as exc:
        print(f"{TITLE}Could not save the print copy: {exc}{RESET}")
        return False
    if shutil.which("lp") is None:
        print(f"{TITLE}The CUPS 'lp' command is not installed.{RESET}")
        print("On Debian/Ubuntu systems, install it with:")
        print(f"{ACCENT}sudo apt install cups-client{RESET}")
        print(f"Print copy saved at: {LAST_PRINT_FILE}")
        return False
    command = ["lp"]
    if queue:
        command.extend(["-d", queue])
    try:
        result = subprocess.run(
            command,
            input=document,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"{TITLE}Print job failed.{RESET}")
        if detail:
            print(detail)
        print(f"Print copy saved at: {LAST_PRINT_FILE}")
        return False
    except OSError as exc:
        print(f"{TITLE}Unable to start the print job: {exc}{RESET}")
        return False
    destination = queue or "the system default printer"
    print(f"{ACCENT}Sent to {destination}.{RESET}")
    message = (result.stdout or "Print job accepted.").strip()
    if message:
        print(message)
    print(f"Print copy: {LAST_PRINT_FILE}")
    return True


# ---------------------------------------------------------------------------
# Recipe entry and common result actions
# ---------------------------------------------------------------------------


def enter_percentage_components(noun: str = "component") -> IngredientList:
    while True:
        items: IngredientList = []
        total = Decimal("0")
        print()
        print(f"Enter {noun}s one at a time.")
        print(f"Leave the {noun} name blank when finished.")
        print()
        while True:
            name = styled_prompt(f"{noun.title()} name: ").strip()
            if not name:
                if not items:
                    print(f"{TITLE}Enter at least one {noun}.{RESET}")
                    continue
                break
            if any(existing.casefold() == name.casefold() for existing, _ in items):
                print(f"{TITLE}That {noun} has already been entered.{RESET}")
                continue
            percent = decimal_input(
                f"Percentage for {name}: ",
                minimum=Decimal("0.0001"),
                maximum=Decimal("100"),
            )
            assert percent is not None
            if total + percent > Decimal("100"):
                print(
                    f"{TITLE}That would bring the total to "
                    f"{format_decimal(total + percent)}%. Percentages cannot exceed 100%.{RESET}"
                )
                continue
            items.append((name, percent))
            total += percent
            print(f"Running total: {ACCENT}{format_decimal(total)}%{RESET}\n")
            if total == Decimal("100"):
                print(f"{ACCENT}Percentages total 100%.{RESET}")
                break
        if total == Decimal("100"):
            return items
        print(f"The percentages total {format_decimal(total)}%, not 100%.")
        if yes_no(f"Re-enter the {noun} list?", default=True):
            continue
        return []


def recalculate_spec(spec: ReportSpec) -> ReportSpec:
    print_header("Recalculate Batch Size")
    amount = decimal_input("Desired total batch weight: ", minimum=Decimal("0.0001"))
    assert amount is not None
    print()
    unit = choose_unit()
    spec.total_amount = amount
    spec.input_unit = unit
    return spec


def result_actions(
    spec: ReportSpec,
    store: Dict[str, Any],
    save_label: Optional[str] = None,
    save_callback: Optional[Callable[[str], bool]] = None,
) -> None:
    while True:
        print()
        print(f"{BLUE}r){RESET} Recalculate batch size")
        print(f"{BLUE}e){RESET} Export current report as a text file")
        print(f"{BLUE}p){RESET} Print current report")
        if save_callback is not None:
            print(f"{BLUE}s){RESET} {save_label or 'Save recipe'}")
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice in {"r", "recalculate"}:
            spec = recalculate_spec(spec)
            display_report(spec)
        elif choice in {"e", "export", "text"}:
            export_report(spec)
        elif choice in {"p", "print"}:
            print_report(spec, store)
        elif save_callback is not None and choice in {"s", "save"}:
            name = spec.recipe_name.strip() or styled_prompt("Name to save: ").strip()
            if not name:
                print(f"{TITLE}A name is required.{RESET}")
                continue
            if save_callback(name):
                spec.recipe_name = name
                save_callback = None
                save_label = None
        elif choice in {"", "b", "back", "m", "menu"}:
            return
        else:
            valid = "r, e, p, s, or b" if save_callback is not None else "r, e, p, or b"
            print(f"{TITLE}Choose {valid}.{RESET}")


# ---------------------------------------------------------------------------
# Bullet lube module
# ---------------------------------------------------------------------------


def parse_saved_lube(entry: Mapping[str, Any]) -> IngredientList:
    ingredients = entry.get("ingredients", entry if isinstance(entry, list) else [])
    if not isinstance(ingredients, list):
        raise ValueError("Invalid lube recipe format.")
    rows = [(str(item["name"]), Decimal(str(item["percent"]))) for item in ingredients]
    if sum((p for _, p in rows), Decimal("0")) != Decimal("100"):
        raise ValueError("Saved lube recipe does not total 100%.")
    return rows


def save_lube_recipe(store: Dict[str, Any], name: str, ingredients: IngredientList) -> bool:
    recipes = store.setdefault("lube_recipes", {})
    existing = find_casefold_key(recipes, name)
    if existing is not None and not yes_no(f'"{existing}" already exists. Overwrite it?', False):
        print("Recipe was not overwritten.")
        return False
    if existing is not None and existing != name:
        del recipes[existing]
    recipes[name] = {
        "ingredients": [{"name": item, "percent": str(percent)} for item, percent in ingredients],
        "notes": "",
    }
    try:
        save_store(store)
    except OSError as exc:
        print(f"{TITLE}Could not save recipe: {exc}{RESET}")
        return False
    print(f'{ACCENT}Lube recipe saved as "{name}".{RESET}')
    return True


def run_lube_recipe(name: str, ingredients: IngredientList, store: Dict[str, Any], allow_save: bool) -> None:
    print_header("Bullet Lube Batch")
    amount = decimal_input("Desired total batch weight: ", minimum=Decimal("0.0001"))
    assert amount is not None
    print()
    unit = choose_unit()
    spec = ReportSpec(
        report_title="Bullet Lube Recipe",
        recipe_name=name or "Unnamed Bullet Lube",
        total_amount=amount,
        input_unit=unit,
        rows=ingredients,
        footer_lines=["Measure ingredients by weight. Actual performance depends on materials and application."],
        filename_prefix="bullet-lube",
    )
    display_report(spec)
    callback = None
    if allow_save:
        callback = lambda save_name: save_lube_recipe(store, save_name, ingredients)
    result_actions(spec, store, "Save lube recipe percentages", callback)


def new_lube_recipe(store: Dict[str, Any]) -> None:
    print_header("New Bullet Lube Recipe")
    name = styled_prompt("Optional recipe name (press Enter to skip): ").strip()
    ingredients = enter_percentage_components("ingredient")
    if not ingredients:
        pause()
        return
    run_lube_recipe(name, ingredients, store, allow_save=True)


def load_lube_recipe(store: Dict[str, Any]) -> None:
    recipes = store.get("lube_recipes", {})
    if not recipes:
        print_header("Saved Bullet Lube Recipes")
        print("No saved bullet lube recipes were found.")
        pause()
        return
    name = choose_from_names("Load Bullet Lube Recipe", sorted(recipes, key=str.casefold))
    if name is None:
        return
    try:
        ingredients = parse_saved_lube(recipes[name])
    except (ValueError, KeyError, InvalidOperation, TypeError) as exc:
        print(f"{TITLE}That saved recipe is invalid: {exc}{RESET}")
        pause()
        return
    run_lube_recipe(name, ingredients, store, allow_save=False)


def view_lube_recipes(store: Dict[str, Any]) -> None:
    print_header("Saved Bullet Lube Recipes")
    recipes = store.get("lube_recipes", {})
    if not recipes:
        print("No saved recipes were found.")
        pause()
        return
    for name in sorted(recipes, key=str.casefold):
        print(f"{ACCENT}{name}{RESET}")
        try:
            ingredients = parse_saved_lube(recipes[name])
            print("  " + ", ".join(f"{item} {format_decimal(percent)}%" for item, percent in ingredients))
        except Exception:
            print(f"  {WARNING}[Invalid saved recipe]{RESET}")
        print()
    pause()


def delete_lube_recipe(store: Dict[str, Any]) -> None:
    recipes = store.get("lube_recipes", {})
    if not recipes:
        print_header("Delete Bullet Lube Recipe")
        print("No saved recipes were found.")
        pause()
        return
    name = choose_from_names("Delete Bullet Lube Recipe", sorted(recipes, key=str.casefold))
    if name is None:
        return
    if yes_no(f'Delete "{name}"?', False):
        del recipes[name]
        save_store(store)
        print(f"{ACCENT}Recipe deleted.{RESET}")
        pause()


def lube_menu(store: Dict[str, Any]) -> None:
    while True:
        print_header("Bullet Lube Calculator")
        print(f"{BLUE}1){RESET} Calculate a new lube recipe")
        print(f"{BLUE}2){RESET} Load a saved lube recipe")
        print(f"{BLUE}3){RESET} View saved lube recipes")
        print(f"{BLUE}4){RESET} Delete a saved lube recipe")
        print()
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            new_lube_recipe(store)
        elif choice == "2":
            load_lube_recipe(store)
        elif choice == "3":
            view_lube_recipes(store)
        elif choice == "4":
            delete_lube_recipe(store)
        elif choice in {"", "b", "back", "q"}:
            return


# ---------------------------------------------------------------------------
# Alloy recipe module
# ---------------------------------------------------------------------------


def alloy_info_lines(name: str, alloy: Mapping[str, Any], components: IngredientList) -> List[str]:
    composition = ", ".join(f"{item} {format_decimal(percent, 6)}%" for item, percent in components)
    lines = [f"Exact calculated composition: {composition}"]
    if alloy.get("method") == "ratio":
        parts = dict(alloy.get("parts", {}))
        ratio = " : ".join(f"{value} {name}" for name, value in parts.items())
        lines.append(f"Parts ratio: {ratio}")
    if alloy.get("commercial_label"):
        lines.append(str(alloy["commercial_label"]))
    if alloy.get("approx_bhn"):
        lines.append(f"Approximate BHN: {alloy['approx_bhn']} (reference only; actual hardness varies)")
    if alloy.get("notes"):
        lines.append(str(alloy["notes"]))
    return lines


def run_alloy_recipe(
    name: str,
    components: IngredientList,
    store: Dict[str, Any],
    alloy_metadata: Optional[Mapping[str, Any]] = None,
    allow_save: bool = False,
) -> None:
    print_header("Cast Bullet Alloy Batch")
    amount = decimal_input("Desired total alloy weight: ", minimum=Decimal("0.0001"))
    assert amount is not None
    print()
    unit = choose_unit()
    info = []
    if alloy_metadata:
        info = alloy_info_lines(name, alloy_metadata, components)
    else:
        info = [
            "Composition: " + ", ".join(
                f"{item} {format_decimal(percent, 6)}%" for item, percent in components
            )
        ]
    spec = ReportSpec(
        report_title="Cast Bullet Alloy Recipe",
        recipe_name=name or "Unnamed Cast Bullet Alloy",
        total_amount=amount,
        input_unit=unit,
        rows=components,
        info_lines=info,
        footer_lines=[
            "Verify source-metal composition. Published BHN values are approximate and can vary with casting and heat history.",
            "Use appropriate ventilation, hygiene, protective equipment, and dry tools around molten metal.",
        ],
        filename_prefix="cast-bullet-alloy",
    )
    display_report(spec)

    def save_callback(save_name: str) -> bool:
        recipes = store.setdefault("alloy_recipes", {})
        existing = find_casefold_key(recipes, save_name)
        if existing is not None and not yes_no(f'"{existing}" already exists. Overwrite it?', False):
            print("Alloy recipe was not overwritten.")
            return False
        if existing is not None and existing != save_name:
            del recipes[existing]
        recipes[save_name] = {
            "components": [{"name": item, "percent": str(percent)} for item, percent in components],
            "notes": "",
        }
        save_store(store)
        print(f'{ACCENT}Alloy recipe saved as "{save_name}".{RESET}')
        return True

    result_actions(
        spec,
        store,
        "Save custom alloy composition",
        save_callback if allow_save else None,
    )


def choose_builtin_alloy() -> Optional[Tuple[str, Dict[str, Any], IngredientList]]:
    names = list(BUILTIN_ALLOYS)
    descriptions = {
        name: f"{data.get('category', '')}; BHN {data.get('approx_bhn', 'not listed')}"
        for name, data in BUILTIN_ALLOYS.items()
    }
    name = choose_from_names("Built-in Cast Bullet Alloys", names, descriptions)
    if name is None:
        return None
    alloy = BUILTIN_ALLOYS[name]
    return name, alloy, alloy_components(alloy)


def built_in_alloy_batch(store: Dict[str, Any]) -> None:
    selected = choose_builtin_alloy()
    if selected is None:
        return
    name, alloy, components = selected
    run_alloy_recipe(name, components, store, alloy_metadata=alloy, allow_save=False)


def new_custom_alloy(store: Dict[str, Any]) -> None:
    print_header("New Custom Cast Bullet Alloy")
    name = styled_prompt("Optional alloy name (press Enter to skip): ").strip()
    print()
    print("Enter elemental or material percentages by weight.")
    print("For blend-to-target calculations, use Lead, Tin, and Antimony names.")
    components = enter_percentage_components("component")
    if not components:
        pause()
        return
    run_alloy_recipe(name, components, store, alloy_metadata=None, allow_save=True)


def parse_saved_alloy(entry: Mapping[str, Any]) -> IngredientList:
    components_raw = entry.get("components", [])
    if not isinstance(components_raw, list):
        raise ValueError("Invalid alloy recipe format.")
    components = [(str(item["name"]), Decimal(str(item["percent"]))) for item in components_raw]
    if sum((p for _, p in components), Decimal("0")) != Decimal("100"):
        raise ValueError("Saved alloy recipe does not total 100%.")
    return components


def load_custom_alloy(store: Dict[str, Any]) -> None:
    recipes = store.get("alloy_recipes", {})
    if not recipes:
        print_header("Saved Custom Alloys")
        print("No saved custom alloy recipes were found.")
        pause()
        return
    name = choose_from_names("Load Custom Alloy", sorted(recipes, key=str.casefold))
    if name is None:
        return
    try:
        components = parse_saved_alloy(recipes[name])
    except Exception as exc:
        print(f"{TITLE}That saved alloy is invalid: {exc}{RESET}")
        pause()
        return
    run_alloy_recipe(name, components, store, alloy_metadata=None, allow_save=False)


def view_builtin_alloys() -> None:
    print_header("Built-in Alloy Library")
    for name, alloy in BUILTIN_ALLOYS.items():
        components = alloy_components(alloy)
        print(f"{ACCENT}{name}{RESET}")
        print("  " + ", ".join(f"{item} {format_decimal(percent, 6)}%" for item, percent in components))
        if alloy.get("approx_bhn"):
            print(f"  Approximate BHN: {alloy['approx_bhn']}")
        if alloy.get("commercial_label"):
            print(f"  {alloy['commercial_label']}")
        print(f"  {alloy.get('notes', '')}")
        print()
    pause()


def delete_custom_alloy(store: Dict[str, Any]) -> None:
    recipes = store.get("alloy_recipes", {})
    if not recipes:
        print_header("Delete Custom Alloy")
        print("No saved custom alloys were found.")
        pause()
        return
    name = choose_from_names("Delete Custom Alloy", sorted(recipes, key=str.casefold))
    if name is None:
        return
    if yes_no(f'Delete "{name}"?', False):
        del recipes[name]
        save_store(store)
        print(f"{ACCENT}Alloy recipe deleted.{RESET}")
        pause()


def alloy_menu(store: Dict[str, Any]) -> None:
    while True:
        print_header("Cast Bullet Alloy Calculator")
        print(f"{BLUE}1){RESET} Calculate a built-in alloy recipe")
        print(f"{BLUE}2){RESET} Create a custom alloy recipe")
        print(f"{BLUE}3){RESET} Load a saved custom alloy")
        print(f"{BLUE}4){RESET} View built-in alloy library")
        print(f"{BLUE}5){RESET} Delete a saved custom alloy")
        print()
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            built_in_alloy_batch(store)
        elif choice == "2":
            new_custom_alloy(store)
        elif choice == "3":
            load_custom_alloy(store)
        elif choice == "4":
            view_builtin_alloys()
        elif choice == "5":
            delete_custom_alloy(store)
        elif choice in {"", "b", "back", "q"}:
            return


# ---------------------------------------------------------------------------
# Source-alloy blend module
# ---------------------------------------------------------------------------


def source_composition(source: Mapping[str, Any]) -> Composition:
    raw = dict(source.get("composition", {}))
    composition = {symbol: Decimal(str(raw.get(symbol, "0"))) for symbol in METAL_NAMES}
    total = sum(composition.values(), Decimal("0"))
    if total != Decimal("100"):
        raise ValueError(f"Source alloy totals {total}%, not 100%.")
    return composition


def all_source_alloys(store: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    sources: Dict[str, Dict[str, Any]] = {name: dict(data) for name, data in BUILTIN_SOURCE_ALLOYS.items()}
    # Finished built-in alloys are also legitimate known source materials.
    for name, alloy in BUILTIN_ALLOYS.items():
        if name in sources:
            continue
        try:
            composition = component_list_to_metal_composition(alloy_components(alloy))
        except ValueError:
            continue
        sources[name] = {
            "composition": {symbol: str(value) for symbol, value in composition.items()},
            "notes": "Built-in finished alloy, available for use as a source material.",
            "preference": 7,
        }
    for name, data in dict(store.get("source_alloys", {})).items():
        sources[name] = dict(data)
        sources[name]["custom"] = True
        sources[name].setdefault("preference", 8)
    return sources


def enter_metal_composition(title: str) -> Composition:
    print_header(title)
    print("Enter percentages by weight. Lead + Tin + Antimony must equal 100%.")
    while True:
        values: Composition = {}
        for symbol in ("Pb", "Sn", "Sb"):
            value = decimal_input(
                f"{METAL_NAMES[symbol]} ({symbol}) %: ",
                minimum=Decimal("0"),
                maximum=Decimal("100"),
            )
            assert value is not None
            values[symbol] = value
        total = sum(values.values(), Decimal("0"))
        if total == Decimal("100"):
            return values
        print(f"{TITLE}Composition totals {format_decimal(total)}%, not 100%.{RESET}")
        if not yes_no("Re-enter composition?", True):
            raise KeyboardInterrupt


def solve_linear_system(matrix: List[List[Decimal]], vector: List[Decimal]) -> List[Decimal]:
    n = len(vector)
    augmented = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    tolerance = Decimal("1e-24")
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot][col]) <= tolerance:
            raise ValueError("The selected source compositions do not form a unique solution.")
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        augmented[col] = [value / pivot_value for value in augmented[col]]
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0:
                continue
            augmented[row] = [
                augmented[row][j] - factor * augmented[col][j]
                for j in range(n + 1)
            ]
    return [augmented[i][n] for i in range(n)]


def calculate_final_composition(
    source_names: Sequence[str],
    source_data: Mapping[str, Mapping[str, Any]],
    weights: Sequence[Decimal],
) -> Composition:
    total = sum(weights, Decimal("0"))
    if total <= 0:
        raise ValueError("Blend weight must be greater than zero.")
    final = {symbol: Decimal("0") for symbol in METAL_NAMES}
    for name, weight in zip(source_names, weights):
        composition = source_composition(source_data[name])
        for symbol in METAL_NAMES:
            final[symbol] += weight * composition[symbol] / total
    return final


def solve_blend(
    target: Composition,
    total_weight: Decimal,
    source_names: Sequence[str],
    source_data: Mapping[str, Mapping[str, Any]],
) -> Tuple[List[Decimal], Composition]:
    if len(source_names) not in {2, 3}:
        raise ValueError("Choose exactly two or three source alloys.")
    if len(set(source_names)) != len(source_names):
        raise ValueError("Each source alloy must be unique.")
    for name in source_names:
        source_composition(source_data[name])
    if sum(target.values(), Decimal("0")) != Decimal("100"):
        raise ValueError("Target composition must total 100%.")
    tolerance_weight = max(total_weight * Decimal("1e-12"), Decimal("1e-12"))
    if len(source_names) == 2:
        first = source_composition(source_data[source_names[0]])
        second = source_composition(source_data[source_names[1]])
        symbol = max(METAL_NAMES, key=lambda key: abs(first[key] - second[key]))
        denominator = first[symbol] - second[symbol]
        if denominator == 0:
            raise ValueError("The selected sources have indistinguishable compositions.")
        x1 = total_weight * (target[symbol] - second[symbol]) / denominator
        weights = [x1, total_weight - x1]
    else:
        compositions = [source_composition(source_data[name]) for name in source_names]
        matrix = [
            [Decimal("1"), Decimal("1"), Decimal("1")],
            [composition["Sn"] / Decimal("100") for composition in compositions],
            [composition["Sb"] / Decimal("100") for composition in compositions],
        ]
        vector = [
            total_weight,
            total_weight * target["Sn"] / Decimal("100"),
            total_weight * target["Sb"] / Decimal("100"),
        ]
        weights = solve_linear_system(matrix, vector)
    cleaned: List[Decimal] = []
    for weight in weights:
        if weight < -tolerance_weight:
            raise ValueError("Those sources require a negative amount and cannot make the target.")
        cleaned.append(Decimal("0") if abs(weight) <= tolerance_weight else weight)
    final = calculate_final_composition(source_names, source_data, cleaned)
    max_error = max(abs(final[symbol] - target[symbol]) for symbol in METAL_NAMES)
    if max_error > Decimal("0.000001"):
        raise ValueError(
            "Those sources do not reproduce the requested target composition exactly "
            f"(maximum error {format_decimal(max_error, 8)} percentage points)."
        )
    return cleaned, final


def find_blend_solutions(
    target: Composition,
    total_weight: Decimal,
    source_data: Mapping[str, Mapping[str, Any]],
    max_results: int = 12,
) -> List[Tuple[Tuple[str, ...], List[Decimal], Composition]]:
    names = list(source_data)
    solutions: List[Tuple[Tuple[str, ...], List[Decimal], Composition]] = []
    for count in (2, 3):
        for combination in itertools.combinations(names, count):
            try:
                weights, final = solve_blend(target, total_weight, combination, source_data)
            except ValueError:
                continue
            if any(weight <= 0 for weight in weights):
                continue
            solutions.append((combination, weights, final))
    def rank(item: Tuple[Tuple[str, ...], List[Decimal], Composition]) -> Tuple[Any, ...]:
        combination, weights, _ = item
        preference = sum(int(source_data[name].get("preference", 8)) for name in combination)
        smallest_share = min(weights) / total_weight
        return (len(combination), preference, -smallest_share, tuple(combination))
    solutions.sort(key=rank)
    return solutions[:max_results]


def choose_target_alloy(store: Dict[str, Any]) -> Optional[Tuple[str, Composition, List[str]]]:
    while True:
        print_header("Choose Target Alloy")
        print(f"{BLUE}1){RESET} Built-in target alloy")
        print(f"{BLUE}2){RESET} Saved custom alloy")
        print(f"{BLUE}3){RESET} Enter custom Pb/Sn/Sb target")
        print()
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            selected = choose_builtin_alloy()
            if selected is None:
                continue
            name, alloy, components = selected
            try:
                return name, component_list_to_metal_composition(components), alloy_info_lines(name, alloy, components)
            except ValueError as exc:
                print(f"{TITLE}{exc}{RESET}")
                pause()
        elif choice == "2":
            recipes = store.get("alloy_recipes", {})
            if not recipes:
                print(f"{TITLE}No saved custom alloys were found.{RESET}")
                pause()
                continue
            name = choose_from_names("Saved Target Alloys", sorted(recipes, key=str.casefold))
            if name is None:
                continue
            try:
                components = parse_saved_alloy(recipes[name])
                composition = component_list_to_metal_composition(components)
                return name, composition, [
                    "Target composition: " + ", ".join(
                        f"{symbol} {format_decimal(composition[symbol], 6)}%" for symbol in METAL_NAMES
                    )
                ]
            except ValueError as exc:
                print(f"{TITLE}{exc}{RESET}")
                pause()
        elif choice == "3":
            try:
                composition = enter_metal_composition("Custom Target Composition")
            except KeyboardInterrupt:
                continue
            name = styled_prompt("Target alloy name (optional): ").strip() or "Custom Target Alloy"
            return name, composition, [
                "Target composition: " + ", ".join(
                    f"{symbol} {format_decimal(composition[symbol], 6)}%" for symbol in METAL_NAMES
                )
            ]
        elif choice in {"", "b", "back", "q"}:
            return None


def choose_manual_sources(
    store: Dict[str, Any],
    source_data: Mapping[str, Mapping[str, Any]],
) -> Optional[List[str]]:
    print_header("Choose Source Alloys")
    print("Select two or three distinct source materials.")
    source_count = integer_input("Number of sources [2 or 3]: ", 2, 3)
    chosen: List[str] = []
    for position in range(1, source_count + 1):
        available = [name for name in source_data if name not in chosen]
        descriptions = {
            name: format_source_description(source_data[name]) for name in available
        }
        selected = choose_from_names(f"Choose Source {position} of {source_count}", available, descriptions)
        if selected is None:
            return None
        chosen.append(selected)
    return chosen


def format_source_description(source: Mapping[str, Any]) -> str:
    composition = source_composition(source)
    return ", ".join(f"{symbol} {format_decimal(composition[symbol], 4)}%" for symbol in METAL_NAMES)


def blend_report_spec(
    target_name: str,
    target: Composition,
    total_amount: Decimal,
    unit: str,
    source_names: Sequence[str],
    weights_in_unit: Sequence[Decimal],
    final: Composition,
    target_notes: Sequence[str],
) -> ReportSpec:
    rows = [
        (name, weight * Decimal("100") / total_amount)
        for name, weight in zip(source_names, weights_in_unit)
    ]
    target_line = "Target: " + ", ".join(
        f"{symbol} {format_decimal(target[symbol], 6)}%" for symbol in METAL_NAMES
    )
    final_line = "Calculated final: " + ", ".join(
        f"{symbol} {format_decimal(final[symbol], 6)}%" for symbol in METAL_NAMES
    )
    info = list(target_notes) + [target_line, final_line]
    return ReportSpec(
        report_title="Source Alloy Blend Plan",
        recipe_name=target_name,
        total_amount=total_amount,
        input_unit=unit,
        rows=rows,
        info_lines=info,
        footer_lines=[
            "Source compositions are mathematical inputs. Verify each actual source alloy before blending.",
            "The plan assumes no selective metal loss and no unlisted elements.",
        ],
        formula="source weights solve mass balance for total, tin, and antimony",
        filename_prefix="alloy-blend",
    )


def execute_blend(
    target_name: str,
    target: Composition,
    target_notes: List[str],
    store: Dict[str, Any],
) -> None:
    print_header("Alloy Blend Batch")
    total_amount = decimal_input("Desired total finished alloy weight: ", minimum=Decimal("0.0001"))
    assert total_amount is not None
    print()
    unit = choose_unit()
    sources = all_source_alloys(store)
    while True:
        print_header("Source Selection Method")
        print(f"Target: {ACCENT}{target_name}{RESET}")
        print()
        print(f"{BLUE}1){RESET} Select source alloys manually")
        print(f"{BLUE}2){RESET} Find exact source combinations automatically")
        print()
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            chosen = choose_manual_sources(store, sources)
            if chosen is None:
                continue
            try:
                weights, final = solve_blend(target, total_amount, chosen, sources)
            except ValueError as exc:
                print_header("Blend Not Possible")
                print(str(exc))
                print()
                print("Try a different combination, often including a source rich in the")
                print("element the target needs, such as pure tin or an antimony-bearing alloy.")
                pause()
                continue
            spec = blend_report_spec(target_name, target, total_amount, unit, chosen, weights, final, target_notes)
            display_report(spec)
            result_actions(spec, store)
            return
        if choice == "2":
            solutions = find_blend_solutions(target, total_amount, sources)
            if not solutions:
                print_header("No Exact Blend Found")
                print("No positive two- or three-source solution was found in the current library.")
                print("Add a custom source alloy or choose sources manually.")
                pause()
                continue
            print_header("Exact Blend Solutions")
            for index, (names, weights, _) in enumerate(solutions, start=1):
                summary = "; ".join(
                    f"{name} {format_decimal(weight, 4)} {unit}"
                    for name, weight in zip(names, weights)
                )
                print(f"{BLUE}{index}){RESET} {summary}")
            print()
            print(f"{BLUE}b){RESET} Back")
            while True:
                raw = styled_prompt("\nSelect a solution: ").strip().lower()
                if raw in {"", "b", "back"}:
                    break
                try:
                    index = int(raw)
                except ValueError:
                    print(f"{TITLE}Enter one of the listed numbers.{RESET}")
                    continue
                if 1 <= index <= len(solutions):
                    names, weights, final = solutions[index - 1]
                    spec = blend_report_spec(
                        target_name, target, total_amount, unit, names, weights, final, target_notes
                    )
                    display_report(spec)
                    result_actions(spec, store)
                    return
                print(f"{TITLE}Choose one of the listed numbers.{RESET}")
        elif choice in {"", "b", "back", "q"}:
            return


def new_custom_source(store: Dict[str, Any]) -> None:
    try:
        composition = enter_metal_composition("New Custom Source Alloy")
    except KeyboardInterrupt:
        return
    name = styled_prompt("Source alloy name: ").strip()
    if not name:
        print(f"{TITLE}A source alloy name is required.{RESET}")
        pause()
        return
    notes = styled_prompt("Optional notes: ").strip()
    sources = store.setdefault("source_alloys", {})
    existing = find_casefold_key(sources, name)
    if existing is not None and not yes_no(f'"{existing}" already exists. Overwrite it?', False):
        return
    if existing is not None and existing != name:
        del sources[existing]
    sources[name] = {
        "composition": {symbol: str(value) for symbol, value in composition.items()},
        "notes": notes,
        "preference": 8,
    }
    save_store(store)
    print(f"{ACCENT}Custom source alloy saved.{RESET}")
    pause()


def view_source_library(store: Dict[str, Any]) -> None:
    print_header("Source Alloy Library")
    sources = all_source_alloys(store)
    for name, data in sources.items():
        marker = " [custom]" if data.get("custom") else ""
        print(f"{ACCENT}{name}{marker}{RESET}")
        print(f"  {format_source_description(data)}")
        if data.get("notes"):
            print(f"  {data['notes']}")
        print()
    pause()


def delete_custom_source(store: Dict[str, Any]) -> None:
    sources = store.get("source_alloys", {})
    if not sources:
        print_header("Delete Custom Source Alloy")
        print("No custom source alloys were found.")
        pause()
        return
    name = choose_from_names("Delete Custom Source Alloy", sorted(sources, key=str.casefold))
    if name is None:
        return
    if yes_no(f'Delete "{name}"?', False):
        del sources[name]
        save_store(store)
        print(f"{ACCENT}Custom source alloy deleted.{RESET}")
        pause()


def source_alloy_menu(store: Dict[str, Any]) -> None:
    while True:
        print_header("Source Alloy Library")
        print(f"{BLUE}1){RESET} View all source alloys")
        print(f"{BLUE}2){RESET} Add a custom source alloy")
        print(f"{BLUE}3){RESET} Delete a custom source alloy")
        print()
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            view_source_library(store)
        elif choice == "2":
            new_custom_source(store)
        elif choice == "3":
            delete_custom_source(store)
        elif choice in {"", "b", "back", "q"}:
            return


def blend_menu(store: Dict[str, Any]) -> None:
    while True:
        print_header("Alloy Blend Calculator")
        print(f"{BLUE}1){RESET} Blend source alloys to a target composition")
        print(f"{BLUE}2){RESET} View / manage source alloy library")
        print()
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            selected = choose_target_alloy(store)
            if selected:
                execute_blend(*selected, store)
        elif choice == "2":
            source_alloy_menu(store)
        elif choice in {"", "b", "back", "q"}:
            return


# ---------------------------------------------------------------------------
# Printer settings, library summary, and about
# ---------------------------------------------------------------------------


def list_printers() -> None:
    print_header("Available CUPS Printers")
    if shutil.which("lpstat") is None:
        print("The 'lpstat' command is not installed or not in PATH.")
        print("On Debian/Ubuntu systems: sudo apt install cups-client")
        pause()
        return
    result = subprocess.run(["lpstat", "-p", "-d"], text=True, capture_output=True)
    output = (result.stdout or result.stderr or "No printers reported.").strip()
    print(output)
    pause()


def printer_settings_menu(store: Dict[str, Any]) -> None:
    while True:
        settings = store.setdefault("settings", {})
        queue = str(settings.get("printer_queue", "") or "")
        leading = int(settings.get("leading_blank_lines", DEFAULT_LEADING_BLANK_LINES))
        print_header("Printer Settings")
        print(f"Printer queue:      {ACCENT}{queue or 'System default'}{RESET}")
        print(f"Leading blank lines:{ACCENT} {leading}{RESET}")
        print()
        print(f"{BLUE}1){RESET} Set printer queue")
        print(f"{BLUE}2){RESET} List available CUPS printers")
        print(f"{BLUE}3){RESET} Set leading blank lines")
        print(f"{BLUE}4){RESET} Clear saved printer queue")
        print()
        print(f"{BLUE}b){RESET} Back")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            new_queue = styled_prompt("CUPS printer queue name: ").strip()
            if new_queue:
                settings["printer_queue"] = new_queue
                save_store(store)
                print(f"{ACCENT}Printer queue saved.{RESET}")
                pause()
        elif choice == "2":
            list_printers()
        elif choice == "3":
            value = decimal_input(
                "Leading blank lines [0-10]: ",
                minimum=Decimal("0"),
                maximum=Decimal("10"),
            )
            assert value is not None
            settings["leading_blank_lines"] = int(value)
            save_store(store)
        elif choice == "4":
            settings["printer_queue"] = ""
            save_store(store)
        elif choice in {"", "b", "back", "q"}:
            return


def library_summary(store: Dict[str, Any]) -> None:
    print_header("Workshop Recipe Library")
    lube = store.get("lube_recipes", {})
    alloys = store.get("alloy_recipes", {})
    sources = store.get("source_alloys", {})
    print(f"Built-in alloy recipes: {ACCENT}{len(BUILTIN_ALLOYS)}{RESET}")
    print(f"Built-in source alloys: {ACCENT}{len(BUILTIN_SOURCE_ALLOYS)}{RESET}")
    print(f"Saved lube recipes:     {ACCENT}{len(lube)}{RESET}")
    print(f"Saved custom alloys:    {ACCENT}{len(alloys)}{RESET}")
    print(f"Custom source alloys:   {ACCENT}{len(sources)}{RESET}")
    print()
    print(f"Data file: {STORE_FILE}")
    print()
    if lube:
        print(f"{ACCENT}Bullet lube recipes{RESET}")
        for name in sorted(lube, key=str.casefold):
            print(f"  - {name}")
        print()
    if alloys:
        print(f"{ACCENT}Custom alloy recipes{RESET}")
        for name in sorted(alloys, key=str.casefold):
            print(f"  - {name}")
        print()
    if sources:
        print(f"{ACCENT}Custom source alloys{RESET}")
        for name in sorted(sources, key=str.casefold):
            print(f"  - {name}")
        print()
    pause()


def about_and_safety() -> None:
    print_header("About and Workshop Safety")
    lines = [
        f"{APP_NAME} v{VERSION}",
        "",
        "This program performs weight-based recipe and mass-balance calculations. It does not validate a recipe for any particular firearm, pressure, velocity, or casting method.",
        "",
        "Alloy source compositions can vary. Confirm labels, certificates, or reliable measurements before relying on a blend calculation. Approximate BHN values are references, not guarantees.",
        "",
        "Lead and other metals require appropriate ventilation, hygiene, protective equipment, and workspace controls. Keep food and drink away, wash thoroughly after handling, and prevent all moisture from contacting molten metal.",
        "",
        "Printing uses the operating system's CUPS 'lp' command. Text reports are formatted to 76 columns and include two leading blank lines by default; both printer queue and top spacing are configurable.",
    ]
    for line in lines:
        if not line:
            print()
        else:
            for wrapped in wrap_text(line, HEADER_WIDTH):
                print(wrapped)
    pause()


# ---------------------------------------------------------------------------
# CLI and main menu
# ---------------------------------------------------------------------------


def set_printer_from_cli(queue: str) -> None:
    store = load_store()
    store.setdefault("settings", {})["printer_queue"] = queue
    save_store(store)
    print(f"Printer queue set to: {queue or 'System default'}")


def list_presets_cli() -> None:
    print("Built-in finished alloys:")
    for name in BUILTIN_ALLOYS:
        print(f"  {name}")
    print("\nBuilt-in source alloys:")
    for name in BUILTIN_SOURCE_ALLOYS:
        print(f"  {name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI terminal colors")
    parser.add_argument("--set-printer", metavar="QUEUE", help="save a CUPS printer queue and exit")
    parser.add_argument("--clear-printer", action="store_true", help="use the system default printer and exit")
    parser.add_argument("--list-presets", action="store_true", help="list built-in alloy presets and exit")
    parser.add_argument("--show-data-path", action="store_true", help="show the user data file path and exit")
    return parser


def main_menu(store: Dict[str, Any]) -> None:
    while True:
        print_header(APP_NAME)
        print(f"{BLUE}1){RESET} Bullet Lube Calculator")
        print(f"{BLUE}2){RESET} Cast Bullet Alloy Calculator")
        print(f"{BLUE}3){RESET} Alloy Blend Calculator")
        print(f"{BLUE}4){RESET} Workshop Recipe Library")
        print(f"{BLUE}5){RESET} Printer Settings")
        print(f"{BLUE}6){RESET} About / Safety")
        print()
        print(f"{BLUE}q){RESET} Quit")
        choice = styled_prompt("\nSelect: ").strip().lower()
        if choice == "1":
            lube_menu(store)
        elif choice == "2":
            alloy_menu(store)
        elif choice == "3":
            blend_menu(store)
        elif choice == "4":
            library_summary(store)
        elif choice == "5":
            printer_settings_menu(store)
        elif choice == "6":
            about_and_safety()
        elif choice in {"q", "quit", "exit"}:
            clear()
            return


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_theme(not args.no_color and not os.environ.get("NO_COLOR"))
    if args.set_printer is not None:
        set_printer_from_cli(args.set_printer)
        return 0
    if args.clear_printer:
        set_printer_from_cli("")
        return 0
    if args.list_presets:
        list_presets_cli()
        return 0
    if args.show_data_path:
        print(STORE_FILE)
        return 0
    store = load_store()
    imported, sources = migrate_legacy_lube_recipes(store)
    executable_name = Path(sys.argv[0]).name.casefold()
    if imported:
        print_header("Legacy Recipe Migration")
        print(f"Imported {ACCENT}{imported}{RESET} saved bullet lube recipe(s).")
        for source in sources:
            print(f"  {source}")
        pause()
    if executable_name == "bullet-lube":
        lube_menu(store)
    else:
        main_menu(store)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
