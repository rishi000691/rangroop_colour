# Reference Dataset: Clothing Colour Preferences

## Source
Perrett, D. I., & Sprengelmeyer, R. (2021). Clothing colour choices to
match fair and tanned skin types of White women [Dataset]. Figshare.
https://doi.org/10.6084/m9.figshare.14596905.v1

Associated paper: Perrett, D. I., & Sprengelmeyer, R. (2021). Clothing
Aesthetics: Consistent Colour Choices to Match Fair and Tanned Skin
Tones. i-Perception, 12(6).
https://doi.org/10.1177/20416695211053361

## License
CC BY 4.0 — reuse permitted with attribution (see citation above).

## What it contains
Two experiments (N=96 and N=75 participants) where observers selected
clothing hue/saturation/value that best suited 12 women's faces (6 fair
skin, 6 tanned skin, all White women). Skin colour of stimulus faces is
provided in CIE L*a*b* colour space.

## Important limitation
Sample is White women only — fair vs. tanned skin, not a diverse range
of skin tones or ethnicities, and doesn't cover undertone (warm/cool/
neutral) as a separate variable the way our Phase 1 pipeline does.

## How we use it in rangroop
NOT used to train any model. Used only as a validation reference for
Phase 2 palette_lookup.json — spot-checking whether our rule-based
palette choices for lighter vs. tanned/darker skin broadly align with
this real experimental finding (participants preferred cool blue hues
for fair skin, warm orange/red hues for tanned skin).
