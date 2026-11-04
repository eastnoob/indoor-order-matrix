"""Fixed Matplotlib 3.11.0 samples and stdlib-only display color mapping.

Samples: colormaps[name](i / 15), i=0..15, RGB rounded to six decimals.
See PALETTE_LICENSE.txt for attribution and the retained Matplotlib license.
"""

import math

PALETTES = {
    "cividis": ((0., .135112, .304751), (0., .181610, .421859), (.117612, .225935, .434308),
        (.208926, .272546, .424809), (.279411, .318677, .423031), (.342246, .364939, .428559),
        (.401418, .411790, .440708), (.458366, .459552, .460457), (.517920, .508454, .472707),
        (.582087, .558670, .468118), (.648222, .610553, .454801), (.716177, .664384, .432386),
        (.785965, .720438, .399613), (.857809, .778969, .353259), (.932180, .840159, .285880),
        (.995737, .909344, .217772)),
    "viridis": ((.267004, .004874, .329415), (.282656, .100196, .422160), (.277134, .185228, .489898),
        (.253935, .265254, .529983), (.221989, .339161, .548752), (.190631, .407061, .556089),
        (.163625, .471133, .558148), (.139147, .533812, .555298), (.120565, .596422, .543611),
        (.134692, .658636, .517649), (.208030, .718701, .472873), (.327796, .773980, .406640),
        (.477504, .821444, .318195), (.647257, .858400, .209861), (.824940, .884720, .106217),
        (.993248, .906157, .143936)),
    "magma": ((.001462, .000466, .013866), (.043830, .033830, .141886), (.123833, .067295, .295879),
        (.232077, .059889, .437695), (.341482, .080564, .492631), (.445163, .122724, .506901),
        (.550287, .161158, .505719), (.658483, .196027, .490253), (.767398, .233705, .457755),
        (.868793, .287728, .409303), (.944006, .377643, .365136), (.981000, .498428, .369734),
        (.994738, .624350, .427397), (.997228, .747981, .516859), (.993170, .870024, .626189),
        (.987053, .991438, .749504)),
}

LEGEND = (("empty", "Known empty (False)"), ("occupied", "Occupied (True)"),
          ("conditional", "Conditional"), ("unknown", "Unknown"), ("outside", "Outside"),
          ("invalid", "Invalid"), ("not_available", "Not available"))
STATUS_COLORS = {"conditional": (.95, .45, .05), "unknown": (.6, .6, .6),
                 "outside": (.15, .2, .25), "invalid": (.9, .05, .1),
                 "not_available": (.75, .25, .8)}


def finite_number(value, name):
    """Reject bool and nonfinite scalars before normalization or native handoff."""
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(name + " must be a finite number")
    return float(value)


def validate_style(style):
    """Validate one complete style without changing caller-owned state."""
    if not isinstance(style["palette"], str) or style["palette"] not in PALETTES or type(style["reverse"]) is not bool:
        raise ValueError("invalid palette or reversal")
    opacity = finite_number(style["opacity"], "opacity")
    if not 0 <= opacity <= 1:
        raise ValueError("opacity must lie between zero and one")
    if not isinstance(style["range_mode"], str) or style["range_mode"] not in {"auto", "manual"}:
        raise ValueError("range mode must be auto or manual")
    lower, upper = (finite_number(style[name], name) for name in ("range_min", "range_max"))
    if lower >= upper:
        raise ValueError("range minimum must be below maximum")
    if finite_number(style["display_elevation_m"], "display elevation") < 0:
        raise ValueError("display elevation must be nonnegative")
    return style


def palette_color(position, *, palette="cividis", reverse=False, opacity=.5):
    """Interpolate the fixed palette, clipping normalized finite positions."""
    position = finite_number(position, "position")
    if not isinstance(palette, str) or palette not in PALETTES or type(reverse) is not bool:
        raise ValueError("invalid palette or reversal")
    opacity = finite_number(opacity, "opacity")
    if not 0 <= opacity <= 1:
        raise ValueError("opacity must lie between zero and one")
    position = min(1., max(0., position))
    if reverse:
        position = 1. - position
    samples = PALETTES[palette]
    coordinate = position * (len(samples) - 1)
    index = min(int(coordinate), len(samples) - 2)
    fraction = coordinate - index
    return (*tuple(a + (b - a) * fraction for a, b in zip(samples[index], samples[index + 1])), opacity)


def cell_color(value, status, *, palette="cividis", reverse=False, opacity=.5):
    """Keep Boolean endpoints fixed and uncertainty separate from known empty."""
    endpoint = palette_color(float(value is True), palette=palette, reverse=reverse, opacity=opacity)
    if status == "established":
        if type(value) is not bool:
            raise ValueError("established free-space value must be Boolean")
        return endpoint
    if status not in STATUS_COLORS:
        raise ValueError("unsupported sample status")
    return (*STATUS_COLORS[status], endpoint[3])


def map_numeric(values, *, palette="cividis", reverse=False, opacity=.5,
                range_mode="auto", range_min=0., range_max=1.):
    """Map finite scalar display data, placing a constant automatic range midway."""
    values = [finite_number(value, "value") for value in values]
    validate_style(dict(palette=palette, reverse=reverse, opacity=opacity, range_mode=range_mode,
                        range_min=range_min, range_max=range_max, display_elevation_m=0))
    if not values:
        return []
    lower, upper = (min(values), max(values)) if range_mode == "auto" else (range_min, range_max)
    if lower == upper:
        positions = [.5] * len(values)
    else:
        width = upper - lower
        # Only halve an overflowing range; subnormal ranges must retain their full width.
        divisor = 1. if math.isfinite(width) else 2.
        width = upper / divisor - lower / divisor
        positions = [(min(upper, max(lower, value)) / divisor - lower / divisor) / width for value in values]
    return [palette_color(position, palette=palette, reverse=reverse, opacity=opacity) for position in positions]
