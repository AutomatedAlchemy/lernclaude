"""Detect the host's Claude subscription tier and map it to a model + effort.

Standalone, stdlib-only. Vendored from the author's `_shared/claude_tier.py` so
lernclaude has no import dependency on the monorepo it grew up in.

    Max  -> opus   + effort medium
    Pro  -> sonnet + effort medium
    (unknown -> sonnet + medium, the safe/cheaper default)

Source of truth is ``~/.claude.json`` -> ``.oauthAccount.organizationType``
(``"claude_max"`` / ``"claude_pro"``), **not** the localized startup banner,
which is unstable across locales and releases. Falls back to
``.oauthAccount.organizationRateLimitTier`` when the type field is absent.

The config is read on every call (cheap, stdlib-only), so the answer follows the
host — the same synced checkout gives opus on a Max box and sonnet on a Pro box
without any per-host configuration.

Overrides, in precedence order:
    LERNCLAUDE_MODEL / LERNCLAUDE_EFFORT  pin the launch directly (skip detection)
    CLAUDE_TIER_OVERRIDE                  force a tier ("max" / "pro")
    CLAUDE_CONFIG_FILE                    read a different config path

Example:
    >>> import os
    >>> os.environ["CLAUDE_TIER_OVERRIDE"] = "max"
    >>> model_effort()
    ('opus', 'medium')
    >>> os.environ["CLAUDE_TIER_OVERRIDE"] = "pro"
    >>> model_effort()
    ('sonnet', 'medium')
    >>> del os.environ["CLAUDE_TIER_OVERRIDE"]
"""

from __future__ import annotations

import json
import os

# tier -> (model alias, effort level).
#
# Max drives opus, but at *medium* effort: the Lern-Loop is interactive
# tutoring, not a heavy one-shot job, and the extra depth of `high` costs
# latency the loop feels. Pro (and any unknown) get sonnet at medium — the
# cost-conscious default for the smaller plan.
#
# Change these two lines if you want a different policy; nothing else reads them.
_TIER_POLICY = {
    "max": ("opus", "medium"),
    "pro": ("sonnet", "medium"),
}
_DEFAULT = ("sonnet", "medium")

_EFFORT_ORDER = ("low", "medium", "high", "xhigh", "max")
# On Max, floor and ceiling coincide at medium: every launch lands on medium
# however a caller pins its own effort. Cheaper tiers keep what they ask for, so
# a Pro host can still pin `low` to stretch its quota.
_TIER_EFFORT_FLOOR = {"max": "medium"}
_TIER_EFFORT_CEILING = {"max": "medium"}


def _config_path(config_path: "str | None" = None) -> str:
    if config_path:
        return os.path.expanduser(config_path)
    return os.path.expanduser(os.environ.get("CLAUDE_CONFIG_FILE", "~/.claude.json"))


def detect_tier(config_path: "str | None" = None) -> str:
    """Return this host's tier: ``"max"``, ``"pro"`` or ``"unknown"``.

    ``CLAUDE_TIER_OVERRIDE`` short-circuits the lookup (tests, or forcing a tier).
    A missing or unreadable config is not an error — it yields ``"unknown"``,
    which maps to the safe cheaper default.
    """
    override = os.environ.get("CLAUDE_TIER_OVERRIDE")
    if override:
        return override.strip().lower()
    try:
        with open(_config_path(config_path), encoding="utf-8") as fh:
            account = json.load(fh).get("oauthAccount") or {}
    except (OSError, ValueError):
        return "unknown"
    blob = "{}{}".format(
        account.get("organizationType") or "",
        account.get("organizationRateLimitTier") or "",
    ).lower()
    if "max" in blob:
        return "max"
    if "pro" in blob:
        return "pro"
    return "unknown"


def model_effort(tier: "str | None" = None) -> "tuple[str, str]":
    """Return ``(model, effort)`` for the given (or detected) tier."""
    tier = (tier or detect_tier()).lower()
    return _TIER_POLICY.get(tier, _DEFAULT)


def tier_effort(effort: str, tier: "str | None" = None) -> str:
    """Clamp ``effort`` into the floor/ceiling band for the (or detected) tier.

    Efforts already inside the band, tiers without a band, and effort strings
    outside ``_EFFORT_ORDER`` are all returned unchanged.

    >>> tier_effort("low", tier="max")
    'medium'
    >>> tier_effort("high", tier="max")
    'medium'
    >>> tier_effort("low", tier="pro")
    'low'
    >>> tier_effort("high", tier="pro")
    'high'
    """
    tier = (tier or detect_tier()).lower()
    floor = _TIER_EFFORT_FLOOR.get(tier)
    ceiling = _TIER_EFFORT_CEILING.get(tier)
    if effort not in _EFFORT_ORDER:
        return effort
    i = _EFFORT_ORDER.index(effort)
    if floor in _EFFORT_ORDER:
        i = max(i, _EFFORT_ORDER.index(floor))
    if ceiling in _EFFORT_ORDER:
        i = min(i, _EFFORT_ORDER.index(ceiling))
    return _EFFORT_ORDER[i]


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=False)
    model, effort = model_effort()
    print(f"tier={detect_tier()}  model={model}  effort={effort}")
