# Bullet Lube Calculator

A small, dependency-free terminal program for calculating weight-based bullet
lube recipes. Enter a desired batch weight, ingredient names, and percentages;
the calculator gives the exact weight of every ingredient in the selected unit,
ounces, and grams.

It is designed for black-powder shooters, cast-bullet hobbyists, handloaders,
and anyone who mixes wax-and-grease recipes by weight.

## Features

- Calculates any batch size from percentage-based recipes.
- Supports pounds, ounces, kilograms, and grams.
- Accepts any number of ingredients.
- Validates that ingredient percentages total exactly 100 percent.
- Shows every result in the selected unit, ounces, and grams.
- Saves named recipe percentages for later reuse.
- Recalculates a saved recipe at a different batch size without re-entering it.
- Exports clean, 76-column plain-text batch sheets.
- Uses only the Python standard library—no packages to install.
- Runs on Linux, macOS, and Windows with Python 3.8 or newer.

## Example

For a 2 lb batch containing 60% beeswax and 40% lard:

```text
INGREDIENT                PERCENT       PRIMARY      OUNCES         GRAMS
------------------------  --------  ------------  ----------  ------------
Beeswax                        60%        1.2 lb     19.2 oz      544.31 g
Lard                            40%        0.8 lb     12.8 oz      362.87 g
------------------------  --------  ------------  ----------  ------------
TOTAL                          100%          2 lb       32 oz      907.18 g
```

The calculation is:

```text
ingredient weight = total batch weight x ingredient percentage / 100
```

## Requirements

- Python 3.8 or newer
- A terminal or command prompt
- No third-party Python packages

Check your Python version with:

```bash
python3 --version
```

On Windows, use:

```powershell
py --version
```

## Quick installation on Linux or macOS

Clone the repository:

```bash
git clone https://github.com/xen-glyph/seraph.git
cd seraph/bullet-lube-calculator
```

Run the installer:

```bash
chmod +x install.sh
./install.sh
```

The installer copies the program to:

```text
~/.local/bin/bullet-lube
```

Launch it with:

```bash
bullet-lube
```

If your shell says `bullet-lube: command not found`, add the local binary
directory to your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Zsh users should add the same line to `~/.zshrc` instead.

## Run without installing

From the repository directory:

```bash
python3 bullet_lube_calculator.py
```

On Windows:

```powershell
py bullet_lube_calculator.py
```

## Main menu

```text
1) Calculate a new recipe
2) Load a saved recipe
3) View saved recipes
4) Delete a saved recipe

q) Quit
```

## Creating a new recipe

1. Choose **Calculate a new recipe**.
2. Enter an optional recipe name.
3. Enter the total amount of lube you want to make.
4. Select pounds, ounces, kilograms, or grams.
5. Enter each ingredient name and its percentage.
6. Continue until the running percentage reaches 100 percent.

Example entry:

```text
Recipe name: Standard Bullet Lube
Desired total batch weight: 2
Unit: 1
Ingredient name: Beeswax
Percentage for Beeswax: 60
Ingredient name: Lard
Percentage for Lard: 40
```

The program will reject a percentage that causes the total to exceed 100
percent. It will also prevent duplicate ingredient names.

## Actions after calculation

After a batch is calculated, the following actions are available:

```text
r) Recalculate batch size
e) Export current batch as a text file
s) Save recipe percentages
b) Back to main menu
```

The save option stores the ingredient names and percentages, not one fixed
batch size. This lets the same recipe be reused for a 4 oz test batch, a 2 lb
shop batch, or any other amount.

## Exporting a recipe sheet

Choose `e` from the results screen. The program suggests a filename in the
current directory, such as:

```text
standard-bullet-lube-2-lb.txt
```

Press Enter to accept the default, or type another path:

```text
~/Documents/lube-recipes/standard-lube.txt
```

The exported file contains:

- Recipe name
- Batch size
- Metric and imperial totals
- Date and time prepared
- Ingredient percentages
- Required weight of each ingredient
- Calculation formula

Exported files contain no terminal color codes and are formatted to fit within
76 columns.

## Saved recipe data

The program stores reusable recipes in a JSON file under the current user's
profile.

Linux and macOS default:

```text
~/.local/share/bullet-lube-calculator/recipes.json
```

If `XDG_DATA_HOME` is set, that location is used instead.

Windows default:

```text
%LOCALAPPDATA%\BulletLubeCalculator\recipes.json
```

The recipe file is ordinary JSON and can be backed up or copied to another
computer. Avoid editing it while the calculator is running.

## Command-line options

Show the installed version:

```bash
bullet-lube --version
```

Disable ANSI terminal colors:

```bash
bullet-lube --no-color
```

The widely supported `NO_COLOR` environment variable also disables colors:

```bash
NO_COLOR=1 bullet-lube
```

## Updating

Pull the newest files and rerun the installer:

```bash
cd seraph/bullet-lube-calculator
git pull
./install.sh
```

Saved recipes are stored outside the program directory and are not replaced by
an update.

## Uninstalling

Remove the installed command while keeping saved recipes:

```bash
./uninstall.sh
```

Remove the command and saved recipe data:

```bash
./uninstall.sh --purge
```

## Running the tests

From the repository directory:

```bash
python3 -m unittest discover -s tests -v
```

## Troubleshooting

### `python3: command not found`

Install Python 3 through your operating system's package manager or from the
official Python distribution for your platform.

### `bullet-lube: command not found`

Run the program directly:

```bash
~/.local/bin/bullet-lube
```

Then add `~/.local/bin` to your PATH as shown in the installation section.

### Terminal borders or colors look unusual

Run:

```bash
bullet-lube --no-color
```

The calculator uses Unicode em-dash borders. A UTF-8 terminal is recommended.
Text exports are UTF-8 files.

### A three-part recipe will not total 100 percent

Decimal percentages must add to exactly 100. For three equal parts, enter a
final adjusted value such as:

```text
33.3333
33.3333
33.3334
```

## Scope and safety

This program performs weight and percentage calculations only. It does not
provide firearm load data, pressure data, material-suitability guidance, or a
warranty that a particular lube formula is appropriate for a firearm,
projectile, velocity, climate, or loading method. Verify recipes independently
and follow safe handling practices when heating waxes, oils, and greases.

## Contributing

Bug reports, suggestions, documentation improvements, and pull requests are
welcome. Please include the operating system, Python version, and steps needed
to reproduce a problem.

## License

Released under the MIT License. See [LICENSE](LICENSE).
