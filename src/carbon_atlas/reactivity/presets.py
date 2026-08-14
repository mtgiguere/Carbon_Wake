"""Reactivity presets and the CO2 estimate they produce.

A *preset* is a named, citable bundle of the assumptions that one published
estimate makes about how much trawling-disturbed seafloor organic carbon actually
remineralizes to CO2. The presets disagree — that disagreement is the whole point
of the project — so they are first-class, comparable objects rather than a single
hardcoded constant.

The calculation itself is deliberately tiny and pure: the disputed science lives
in the *fraction* each preset carries, not in the arithmetic.
"""

from collections.abc import Sequence
from dataclasses import dataclass

#: Mass of CO2 produced per unit mass of carbon fully oxidized, from the molar
#: masses (CO2 = 44 g/mol, C = 12 g/mol). This is fixed chemistry, not a modelling
#: choice — the modelling choice is the remineralization fraction below.
CO2_PER_CARBON_MASS_RATIO = 44.0 / 12.0


@dataclass(frozen=True)
class ReactivityPreset:
    """One published set of assumptions for turning disturbed carbon into CO2.

    The model mirrors the two-stage structure of the literature (see
    docs/SCIENCE_BASIS.md): disturbed organic carbon remineralizes first to
    *aqueous* CO2 in the water column, and only a fraction of that reaches the
    *atmosphere*.

    - ``remineralization_fraction`` — the disputed parameter: the fraction of
      disturbed organic carbon that mineralizes to (aqueous) CO2. Competing
      presets differ here by up to two orders of magnitude.
    - ``atmospheric_fraction`` — the fraction of that aqueous CO2 that outgasses
      to the atmosphere. ``None`` when the source did not quantify it (e.g. Sala
      2021 called it "unknown"); the atmospheric estimate is then undefined rather
      than assumed.
    - ``accounts_for_additionality`` — whether the estimate nets out the carbon
      that would have remineralized naturally anyway. This is the crux of the
      Sala-vs-Hiddink dispute, so it is recorded explicitly per preset.
    - ``derivation`` — ``None`` when ``remineralization_fraction`` is quoted
      directly from the cited source; otherwise a note recording how the figure
      was derived (e.g. Hiddink 2023 published only an overestimate *factor*, so
      any absolute fraction for it is an inference and must say so). This is
      SCIENCE_BASIS.md's quoted-vs-derived rule enforced at the data level.
    """

    key: str
    label: str
    remineralization_fraction: float
    citation: str
    atmospheric_fraction: float | None = None
    accounts_for_additionality: bool = False
    derivation: str | None = None

    def __post_init__(self) -> None:
        # A fraction is a proportion; outside [0, 1] it is not a fraction. We
        # reject rather than clip — silently clipping is how a false number
        # reaches the map (see TDD_CONTRACT.md, "green ≠ verified").
        if not 0.0 <= self.remineralization_fraction <= 1.0:
            raise ValueError(
                f"remineralization_fraction must be in [0, 1]; "
                f"got {self.remineralization_fraction!r}"
            )
        if self.atmospheric_fraction is not None and not (0.0 <= self.atmospheric_fraction <= 1.0):
            raise ValueError(
                f"atmospheric_fraction must be in [0, 1] or None; got {self.atmospheric_fraction!r}"
            )


#: The published estimates, encoded. Provenance for every figure is
#: docs/SCIENCE_BASIS.md; each preset is either a verified quoted value
#: (``derivation is None``) or explicitly flagged as derived. Epstein et al. 2022
#: (the middle-ground review) deliberately has no preset: it published no
#: competing point estimate, and a review's doubt must not be turned into a
#: number it never gave.
PUBLISHED_PRESETS: tuple[ReactivityPreset, ...] = (
    ReactivityPreset(
        key="sala_2021",
        label="Sala et al. 2021 — original high estimate (aqueous)",
        remineralization_fraction=0.297,
        citation=(
            "Sala, E., et al. (2021). Protecting the global ocean for biodiversity, "
            "food and climate. Nature 592, 397-402. DOI: 10.1038/s41586-021-03371-z"
        ),
        atmospheric_fraction=None,  # the paper calls this fraction "unknown"
        accounts_for_additionality=False,
    ),
    ReactivityPreset(
        key="atwood_2024_low",
        label="Atwood et al. 2024 — atmospheric follow-up (55% outgassing, low end)",
        remineralization_fraction=0.297,
        citation=(
            "Atwood, T.B., et al. (2024). Atmospheric CO2 emissions and ocean "
            "acidification from bottom-trawling. Frontiers in Marine Science "
            "10:1125137. DOI: 10.3389/fmars.2023.1125137"
        ),
        atmospheric_fraction=0.55,
        accounts_for_additionality=False,
    ),
    ReactivityPreset(
        key="atwood_2024_high",
        label="Atwood et al. 2024 — atmospheric follow-up (60% outgassing, high end)",
        remineralization_fraction=0.297,
        citation=(
            "Atwood, T.B., et al. (2024). Atmospheric CO2 emissions and ocean "
            "acidification from bottom-trawling. Frontiers in Marine Science "
            "10:1125137. DOI: 10.3389/fmars.2023.1125137"
        ),
        atmospheric_fraction=0.60,
        accounts_for_additionality=False,
    ),
    ReactivityPreset(
        key="hiddink_2023_high",
        label="Hiddink et al. 2023 — critique, milder end (100x below Sala, inferred)",
        remineralization_fraction=0.297 / 100,
        citation=(
            "Hiddink, J.G., et al. (2023). Quantifying the carbon benefits of ending "
            "bottom trawling. Nature 617, E1-E2. DOI: 10.1038/s41586-023-06014-7"
        ),
        atmospheric_fraction=None,
        accounts_for_additionality=True,
        derivation=(
            "Inferred: Sala 2021's 29.7% divided by the milder end of Hiddink 2023's "
            "100-1000x overestimate factor. Hiddink published no absolute figure."
        ),
    ),
    ReactivityPreset(
        key="hiddink_2023_low",
        label="Hiddink et al. 2023 — critique, strongest end (1000x below Sala, inferred)",
        remineralization_fraction=0.297 / 1000,
        citation=(
            "Hiddink, J.G., et al. (2023). Quantifying the carbon benefits of ending "
            "bottom trawling. Nature 617, E1-E2. DOI: 10.1038/s41586-023-06014-7"
        ),
        atmospheric_fraction=None,
        accounts_for_additionality=True,
        derivation=(
            "Inferred: Sala 2021's 29.7% divided by the strongest end of Hiddink 2023's "
            "100-1000x overestimate factor. Hiddink published no absolute figure."
        ),
    ),
)


def get_preset(key: str) -> ReactivityPreset:
    """The published preset registered under ``key``.

    Raises ``KeyError`` naming the available keys — a typo'd preset must fail
    loudly and helpfully, never fall back to some default estimate.
    """
    for preset in PUBLISHED_PRESETS:
        if preset.key == key:
            return preset
    available = ", ".join(p.key for p in PUBLISHED_PRESETS)
    raise KeyError(f"unknown preset key {key!r}; available: {available}")


def co2_from_disturbed_carbon(disturbed_carbon_mass: float, preset: ReactivityPreset) -> float:
    """CO2 mass produced when ``disturbed_carbon_mass`` of organic carbon is
    disturbed under ``preset``'s remineralization assumption.

    Output is in the same mass unit as the input (grams in → grams of CO2 out).
    """
    if disturbed_carbon_mass < 0.0:
        raise ValueError(
            f"disturbed_carbon_mass must be non-negative; got {disturbed_carbon_mass!r}"
        )
    return disturbed_carbon_mass * preset.remineralization_fraction * CO2_PER_CARBON_MASS_RATIO


@dataclass(frozen=True)
class CO2Estimate:
    """A preset's CO2 estimate for one disturbed-carbon quantity, on both bases.

    ``atmospheric`` is ``None`` when the preset does not quantify the
    aqueous-to-atmosphere fraction — the gap is reported, never filled in.
    """

    aqueous: float
    atmospheric: float | None


def estimate_co2(disturbed_carbon_mass: float, preset: ReactivityPreset) -> CO2Estimate:
    """The aqueous and atmospheric CO2 for ``disturbed_carbon_mass`` under ``preset``.

    Atmospheric CO2 is the aqueous CO2 scaled by the preset's atmospheric
    fraction, or ``None`` when that fraction is unspecified.
    """
    aqueous = co2_from_disturbed_carbon(disturbed_carbon_mass, preset)
    atmospheric = (
        None if preset.atmospheric_fraction is None else aqueous * preset.atmospheric_fraction
    )
    return CO2Estimate(aqueous=aqueous, atmospheric=atmospheric)


@dataclass(frozen=True)
class CO2EstimateRange:
    """The span of CO2 estimates for one disturbed-carbon quantity across the
    competing presets. Each end carries the preset that produced it so the value
    can be attributed to a specific published estimate rather than shown bare.
    """

    low: float
    high: float
    low_preset: ReactivityPreset
    high_preset: ReactivityPreset


def estimate_range(
    disturbed_carbon_mass: float, presets: Sequence[ReactivityPreset]
) -> CO2EstimateRange:
    """The range of CO2 estimates across ``presets`` for a disturbed-carbon mass.

    This is the project's core promise in code: a disputed quantity is reported as
    a span with attributed ends, never as a single figure.
    """
    if not presets:
        raise ValueError("estimate_range requires at least one preset; got none")

    estimates = [(co2_from_disturbed_carbon(disturbed_carbon_mass, p), p) for p in presets]
    low_value, low_preset = min(estimates, key=lambda pair: pair[0])
    high_value, high_preset = max(estimates, key=lambda pair: pair[0])
    return CO2EstimateRange(
        low=low_value,
        high=high_value,
        low_preset=low_preset,
        high_preset=high_preset,
    )
