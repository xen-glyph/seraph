# Built-in Alloy Sources and Conventions

The built-in library is intentionally small and limited to commonly published,
known-composition alloys. Users should still verify the composition of the
actual metal in their possession.

## Traditional lead/tin ratios

The calculator interprets names such as `20:1 Lead/Tin` literally as twenty
parts lead to one part tin. It therefore calculates the exact percentages:

- 40:1 = 97.5609756% Pb / 2.4390244% Sn
- 30:1 = 96.7741935% Pb / 3.2258065% Sn
- 25:1 = 96.1538462% Pb / 3.8461538% Sn
- 20:1 = 95.2380952% Pb / 4.7619048% Sn
- 16:1 = 94.1176471% Pb / 5.8823529% Sn

Commercial listings often round these to 97.5/2.5, 97/3, 96/4, 95/5, and
94/6. The rounded labels are shown as notes, but they are not used for the
calculator's parts-ratio math.

Reference alloy table:

- https://www.rotometals.com/bullet-casting-alloys/

Examples of published ratio descriptions:

- https://www.rotometals.com/1-to-20-bullet-alloy-ingot-95-lead-5-tin-5lb-ingot/
- https://www.rotometals.com/1-to-25-bullet-alloy-5-pound-ingot-96-lead-4-tin/
- https://www.rotometals.com/1-to-30-bullet-alloy-ingot-5-pounds-97-lead-3-tin/
- https://www.rotometals.com/1-to-40-bullet-alloy-ingot-5-pounds-97-5-lead-2-5-tin/

## Lead/tin/antimony alloys

Built-in compositions:

- Lyman No. 2: 90% Pb / 5% Sn / 5% Sb
- Hardball: 92% Pb / 2% Sn / 6% Sb
- Linotype 84/4/12: 84% Pb / 4% Sn / 12% Sb
- SuperHard: 70% Pb / 0% Sn / 30% Sb
- Foundry Type: 64.5% Pb / 12.5% Sn / 23% Sb
- Antimonial Lead 94/6: 94% Pb / 0% Sn / 6% Sb

References:

- https://www.rotometals.com/bullet-casting-alloys/
- https://www.rotometals.com/linotype-alloy-5-pounds-4-tin-12-antimony-and-84-lead/
- https://www.rotometals.com/roto-blog/rotometals-bullet-casting-alloys-a-little-insight/

## Hardness notes

BHN values in the application are approximate reference values. Actual hardness
can vary with composition, impurities, cooling method, heat treatment, age, and
measurement technique. The calculator does not predict final BHN.

Source review date: 2026-08-07.
