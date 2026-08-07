# Cast Bullet Workshop Calculator

A dependency-free terminal application for cast-bullet shops. It combines a
percentage-based **Bullet Lube Calculator**, a known and custom **Bullet Alloy
Calculator**, and an exact **Source Alloy Blend Calculator** in one script.

The program supports pounds, ounces, kilograms, and grams; saves reusable
recipes; exports clean 76-column text reports; and prints through CUPS on Linux
and macOS.

## Major features

### Bullet lube

- Enter any number of ingredients and percentages.
- Validate that the recipe totals exactly 100 percent.
- Calculate any desired batch weight.
- Save and reload recipe percentages.
- Recalculate a different batch size without re-entering the recipe.

### Cast-bullet alloys

- Calculate batches from built-in known-composition alloys.
- Create and save custom alloys.
- Treat traditional `Pb:Sn` names as exact parts ratios.
- Display the exact calculated composition and familiar rounded commercial
  label separately.
- Show approximate BHN reference notes where available.

### Source-alloy blending

- Choose a target from the built-in alloy library, a saved alloy, or a custom
  Pb/Sn/Sb target.
- Select two or three source alloys manually.
- Automatically search the source library for exact two- and three-source
  solutions.
- Reject impossible blends that require a negative source weight.
- Display both the requested target and mathematically calculated final
  composition.
- Add custom source alloys when the user knows their Pb/Sn/Sb percentages.

### Reports and printing

Every result screen includes:

```text
r) Recalculate batch size
e) Export current report as a text file
p) Print current report
b) Back
```

Reports are formatted to fit within 76 columns. Printed reports use two leading
blank lines by default so the top header is not lost on printers that begin near
a page edge. The printer queue and leading-line count are configurable.

## Built-in finished alloys

| Preset | Calculation used | Approx. BHN |
|---|---|---:|
| Pure Lead | 100% Pb | ~5 |
| 40:1 Lead/Tin | Exact 40 parts Pb : 1 part Sn | Not fixed |
| 30:1 Lead/Tin | Exact 30 parts Pb : 1 part Sn | ~9 |
| 25:1 Lead/Tin | Exact 25 parts Pb : 1 part Sn | ~9 |
| 20:1 Lead/Tin | Exact 20 parts Pb : 1 part Sn | ~10 |
| 16:1 Lead/Tin | Exact 16 parts Pb : 1 part Sn | ~11 |
| Lyman No. 2 | 90% Pb / 5% Sn / 5% Sb | ~16 |
| Hardball | 92% Pb / 2% Sn / 6% Sb | ~16 |
| Linotype 84/4/12 | 84% Pb / 4% Sn / 12% Sb | ~22 |

For example, a true 20:1 recipe uses 95.238095% lead and 4.761905% tin. A
21-pound batch therefore calls for exactly 20 pounds of lead and 1 pound of
tin. The familiar commercial `95/5` label is retained as a note but is not used
for the calculation.

## Built-in source alloys

- Pure Lead
- Pure Tin
- Pure Antimony
- Linotype 84/4/12
- SuperHard 70/30
- Foundry Type 64.5/12.5/23
- Antimonial Lead 94/6

The finished-alloy presets are also available as source materials. Custom
source alloys can be added to the local library.

See [SOURCES.md](SOURCES.md) for source links, exact ratio conventions, and
hardness caveats.

## Requirements

- Python 3.8 or newer
- No third-party Python packages
- A terminal
- Optional printing: CUPS client commands `lp` and `lpstat`

Check Python:

```bash
python3 --version
```

On Windows:

```powershell
py --version
```

## Quick installation on Linux or macOS

Clone the Seraph repository and enter this project folder:

```bash
git clone https://github.com/xen-glyph/seraph.git
cd seraph/cast-bullet-workshop-calculator
```

Install for the current user:

```bash
chmod +x install.sh
./install.sh
```

The installer creates:

```text
~/.local/bin/cast-bullet-workshop
~/.local/bin/cbwc
```

Launch either command:

```bash
cast-bullet-workshop
```

or:

```bash
cbwc
```

### Install with a preferred printer

```bash
./install.sh --printer MyPrinterQueue
```

### Preserve the earlier `bullet-lube` command

This optional compatibility command opens the new application's lube module:

```bash
./install.sh --compat-bullet-lube
```

Both options can be combined:

```bash
./install.sh --printer MyPrinterQueue --compat-bullet-lube
```

If an older non-symlink `~/.local/bin/bullet-lube` exists, the installer backs
it up with a timestamp before creating the compatibility link.

### PATH note

The installer adds `~/.local/bin` to the appropriate shell startup file when
needed. To update the current terminal immediately:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Run without installing

```bash
python3 cast_bullet_workshop_calculator.py
```

## Windows installation

From PowerShell in the project directory:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Open a new terminal and run:

```powershell
cast-bullet-workshop
```

The interactive calculator and text export work on Windows. The built-in print
command specifically uses CUPS and is therefore intended for Linux/macOS; on
Windows, export a text report and print it using the normal application or
print workflow.

## Main menu

```text
1) Bullet Lube Calculator
2) Cast Bullet Alloy Calculator
3) Alloy Blend Calculator
4) Workshop Recipe Library
5) Printer Settings
6) About / Safety

q) Quit
```

## Example: bullet lube

For a 2 lb batch containing 60% beeswax and 40% lard:

```text
COMPONENT                  PERCENT       PRIMARY      OUNCES         GRAMS
------------------------  --------  ------------  ----------  ------------
Beeswax                        60%        1.2 lb     19.2 oz      544.31 g
Lard                            40%        0.8 lb     12.8 oz      362.87 g
------------------------  --------  ------------  ----------  ------------
TOTAL                          100%          2 lb       32 oz      907.18 g
```

## Example: known alloy

A 21 lb batch of exact 20:1 lead/tin produces:

```text
Lead     95.238095%     20 lb
Tin       4.761905%      1 lb
```

## Example: alloy blending

Equal weights of pure lead and Linotype 84/4/12 produce Hardball:

```text
10 lb Pure Lead
10 lb Linotype 84/4/12
-----------------------
20 lb final Hardball
92% Pb / 2% Sn / 6% Sb
```

The calculator can find that solution automatically or verify it through manual
source selection.

## Blend-calculator limits

The exact blend solver is deliberately constrained to known Pb/Sn/Sb
compositions and two or three source alloys. This keeps the result transparent
and mathematically auditable.

The calculation assumes:

- Each source composition is accurate.
- Pb, Sn, and Sb account for the full source mass.
- There is no selective oxidation, dross loss, contamination, or evaporation.
- No unlisted elements materially affect the balance.

Unknown wheel weights, range scrap, shot, solder, or mystery ingots should not
be entered as known sources unless the user has a defensible composition.

## Text export

Select `e` from any result screen. Press Enter to accept the suggested filename
or provide another path, for example:

```text
~/Documents/casting-recipes/20-to-1-21-lb.txt
```

Text files contain:

- Recipe or target name
- Total batch weight
- Metric and imperial totals
- Date and time
- Exact percentages
- Required weight of every component or source alloy
- Target and calculated final composition for blend plans
- Notes and assumptions

No ANSI terminal colors are written to the file.

## Printing

Printing uses the CUPS `lp` command. On Debian or Ubuntu systems:

```bash
sudo apt install cups-client
```

List printer queues:

```bash
lpstat -p -d
```

Set a queue from the command line:

```bash
cast-bullet-workshop --set-printer MyPrinterQueue
```

Return to the system default printer:

```bash
cast-bullet-workshop --clear-printer
```

The same settings are available under **Printer Settings** in the main menu.
Every print job is also saved at:

```text
~/.local/share/cast-bullet-workshop-calculator/last_print_report.txt
```

## Saved recipes and settings

Linux/macOS default:

```text
~/.local/share/cast-bullet-workshop-calculator/workshop.json
```

When `XDG_DATA_HOME` is set, it is used instead.

Windows default:

```text
%LOCALAPPDATA%\CastBulletWorkshopCalculator\workshop.json
```

Show the exact path used by the current installation:

```bash
cast-bullet-workshop --show-data-path
```

## Migration from Bullet Lube Calculator

On first interactive launch, the application checks these earlier locations:

```text
~/.local/share/bullet-lube-calculator/recipes.json
~/.local/share/seraph/bullet_lube_recipes.json
```

Valid 100-percent lube recipes are imported into the new workshop library.
Original files are left untouched. Duplicate names already present in the new
library are skipped.

## Command-line options

```text
--version             Show version
--no-color            Disable ANSI terminal colors
--set-printer QUEUE   Save a CUPS printer queue
--clear-printer       Use the system default printer
--list-presets        List built-in alloy presets
--show-data-path      Show the workshop data file path
```

The standard `NO_COLOR` environment variable is also honored:

```bash
NO_COLOR=1 cast-bullet-workshop
```

## Updating

From the project folder:

```bash
git pull
./install.sh
```

Rerunning the installer replaces the program but does not replace saved
recipes or settings.

## Uninstalling

Remove the installed commands while retaining workshop data:

```bash
./uninstall.sh
```

Remove commands and new workshop data:

```bash
./uninstall.sh --purge
```

Legacy Bullet Lube Calculator data is not deleted by this uninstaller.

On Windows:

```powershell
.\uninstall.ps1
```

or:

```powershell
.\uninstall.ps1 -Purge
```

## Tests

Run the complete test suite:

```bash
python3 -m unittest discover -s tests -v
```

The tests cover exact ratio arithmetic, built-in composition totals,
two-source and three-source blending, impossible blend rejection, 76-column
reports, and leading print lines.

## Safety and scope

This is a mathematical workshop calculator. It does not determine whether an
alloy or lube is appropriate for a firearm, load, pressure, velocity, or
casting process.

Lead and other metals require suitable ventilation, hygiene, protective
equipment, and workspace controls. Keep food and drink away from the casting
area, wash thoroughly after handling, and keep all moisture away from molten
metal.

## License

MIT License. See [LICENSE](LICENSE).
