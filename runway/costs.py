"""Upfront costs and loan instalments for one resale flat (Python reference; index.html mirrors it).

Every figure is from a document in data/corpus, named next to it. Legal fees are left out:
hdb-mode-of-financing-resale.md says only that they "depend on the solicitor you appoint".
"""

from __future__ import annotations

from runway.cpf_rules import ASSUMED_HDB_RATE, MIN_LEASE, monthly_instalment

# iras-buyers-stamp-duty.md: residential rates on or after 15 Feb 2023 (band width, rate)
BSD_BANDS = [(180_000, 0.01), (180_000, 0.02), (640_000, 0.03), (500_000, 0.04), (1_500_000, 0.05), (float("inf"), 0.06)]

# hdb-mode-of-financing-resale.md: Request for Value $120; resale application fee $80, or $40 for 1- and 2-room flats
RFV_FEE = 120
RESALE_FEE, RESALE_FEE_SMALL = 80, 40

MSR = 0.30  # hdb-housing-loan-from-hdb.md, cpf-guide-buying-financing.md: instalments up to 30% of monthly income
HDB_RATE_FLOOR = 0.03  # hdb-housing-loan-from-hdb.md: eligible HDB loan worked out at the higher of 3.0% and the HDB rate
HDB_INCOME_CEILING = {"family": 16_000, "single": 8_000}  # hdb-housing-loan-from-hdb.md (extended families $24,000 not offered)
FI_MIN_CASH = 0.05  # hdb-housing-loan-from-fi.md: at least 5% of the price or value in cash with a bank loan

SMALL_FLATS = ("2-room", "3-room", "4-room")


def stamp_duty(price: float) -> float:
    """Buyer's Stamp Duty on a residential purchase (IRAS bands from 15 Feb 2023)."""
    duty, left = 0.0, max(0.0, price)
    for width, rate in BSD_BANDS:
        part = min(left, width)
        duty += part * rate
        left -= part
    return round(duty, 2)


def hdb_fees(flat_type: str) -> int:
    return RFV_FEE + (RESALE_FEE_SMALL if flat_type in ("1-room", "2-room") else RESALE_FEE)


def grants(flat_type: str, remaining_lease: float, income: float, household: str, first: str,
           citizens: str = "sc", parents: str = "no") -> dict:
    """Resale grants: CPF Housing Grant and Proximity Housing Grant in dollars; the Enhanced grant as a ceiling only.

    household: "family" | "single". first: "first" (all first-timers), "mixed" (first-timer + second-timer
    couple), "no". citizens: "sc" (all Singapore Citizens) | "spr" (a citizen and a PR). parents: "no" | "with" | "near".
    The corpus gives the EHG's income tiers and its lease pro-rating only as "up to", so ehg_max is a ceiling.
    """
    out = {"chg": 0, "ehg_max": 0, "phg": 0}
    if remaining_lease <= MIN_LEASE:  # every grant needs more than 20 years left
        return out
    small, five = flat_type in SMALL_FLATS, flat_type == "5-room"
    if household == "family":
        # hdb-cpf-housing-grant-families-resale.md: income ceiling $16,000, 2-room or bigger
        if first != "no" and income <= 16_000 and flat_type != "1-room":
            if first == "first":
                out["chg"] = (80_000 if citizens == "sc" else 70_000) if small else (50_000 if citizens == "sc" else 40_000)
            else:
                out["chg"] = 40_000 if small else 25_000
            # hdb-enhanced-cpf-housing-grant-families.md: needs the CPF Housing Grant first
            if first == "first" and income <= 9_000:
                out["ehg_max"] = 120_000
            elif first == "mixed" and income / 2 <= 4_500:
                out["ehg_max"] = 60_000
        # hdb-proximity-housing-grant-families.md: $30,000 with, $20,000 within 4 km
        out["phg"] = {"with": 30_000, "near": 20_000}.get(parents, 0)
    elif household == "single" and first == "first":
        # mynicehome-grants-guide.md, first-timer singles: income ceiling $8,000; up to 5-room
        if income <= 8_000 and (small or five):
            out["chg"] = 40_000 if small else 25_000
            if income <= 4_500:
                out["ehg_max"] = 60_000
        out["phg"] = {"with": 15_000, "near": 10_000}.get(parents, 0)
    return out


def loan_for_instalment(monthly: float, years: float, rate: float) -> float:
    """Largest loan whose instalment over `years` at `rate` is `monthly` (inverse of monthly_instalment)."""
    if monthly <= 0 or years <= 0:
        return 0.0
    i, n = rate / 12, years * 12
    return monthly * (1 - (1 + i) ** -n) / i


def loan_options(price: float, loan_max: float, tenure: float, income: float | None = None,
                 household: str = "family", bank_rate: float | None = None) -> dict:
    """HDB loan against a bank loan of the same length, each capped at 30% of income when income is known."""
    cap = MSR * income if income else None
    hdb_ok = loan_max > 0 and not (income and household in HDB_INCOME_CEILING and income > HDB_INCOME_CEILING[household])
    hdb = loan_max if hdb_ok else 0.0
    if hdb and cap is not None:
        hdb = min(hdb, loan_for_instalment(cap, tenure, max(HDB_RATE_FLOOR, ASSUMED_HDB_RATE)))
    out = {"msr_cap": cap, "hdb_ok": hdb_ok, "hdb_loan": hdb, "hdb_monthly": monthly_instalment(hdb, tenure),
           "bank_loan": None, "bank_monthly": None, "bank_cash_min": FI_MIN_CASH * price}
    if bank_rate and loan_max > 0:
        bank = loan_max if cap is None else min(loan_max, loan_for_instalment(cap, tenure, bank_rate))
        out["bank_loan"], out["bank_monthly"] = bank, monthly_instalment(bank, tenure, bank_rate)
    return out
