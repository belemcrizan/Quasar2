"""Frozen indicator and entity sampling lists. Chosen before method results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    indicator_id: str
    family: str
    topic: str
    unit: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntitySpec:
    entity_code: str
    expected_type: str
    region_stratum: str
    income_stratum: str


CI_INDICATORS: tuple[IndicatorSpec, ...] = (
    IndicatorSpec("NY.GDP.PCAP.CD", "national_accounts", "GDP and national accounts", "current_USD", ("gdp per capita", "income per person")),
    IndicatorSpec("NY.GDP.MKTP.CD", "national_accounts", "GDP and national accounts", "current_USD", ("gdp", "economic size", "total gdp")),
    IndicatorSpec("SP.POP.TOTL", "demographics", "population and demographics", "people", ("population", "inhabitants")),
    IndicatorSpec("SI.POV.DDAY", "poverty", "income and poverty", "percent", ("extreme poverty", "poverty headcount")),
    IndicatorSpec("FP.CPI.TOTL.ZG", "prices", "inflation and prices", "percent", ("inflation", "consumer prices")),
    IndicatorSpec("SL.UEM.TOTL.ZS", "labor", "employment and labor", "percent", ("unemployment", "jobless rate")),
    IndicatorSpec("SP.DYN.LE00.IN", "health", "health", "years", ("life expectancy",)),
    IndicatorSpec("SE.ADT.LITR.ZS", "education", "education", "percent", ("literacy", "adult literacy")),
    IndicatorSpec("EG.ELC.ACCS.ZS", "energy", "energy", "percent", ("electricity access",)),
    IndicatorSpec("EN.GHG.CO2.PC.CE.AR5", "environment", "emissions and environment", "t_co2e_per_capita", ("co2 per capita", "carbon emissions")),
    IndicatorSpec("IT.NET.USER.ZS", "technology", "technology and connectivity", "percent", ("internet users", "internet access")),
    IndicatorSpec("SH.XPD.CHEX.GD.ZS", "health", "health", "percent_of_gdp", ("health expenditure", "health spending")),
)

PILOT_EXTRA_INDICATORS: tuple[IndicatorSpec, ...] = (
    IndicatorSpec("NY.GDP.PCAP.PP.CD", "national_accounts", "GDP and national accounts", "current_PPP_USD", ("gdp per capita ppp", "purchasing power")),
    IndicatorSpec("NY.GNP.PCAP.CD", "national_accounts", "income and poverty", "current_USD", ("gni per capita", "gross national income")),
    IndicatorSpec("SP.URB.TOTL.IN.ZS", "demographics", "population and demographics", "percent", ("urban population",)),
    IndicatorSpec("SP.DYN.TFRT.IN", "demographics", "population and demographics", "births_per_woman", ("fertility", "total fertility rate")),
    IndicatorSpec("SH.DYN.MORT", "health", "health", "per_1000", ("under five mortality", "child mortality")),
    IndicatorSpec("SE.PRM.NENR", "education", "education", "percent", ("primary enrollment",)),
    IndicatorSpec("SE.SEC.NENR", "education", "education", "percent", ("secondary enrollment",)),
    IndicatorSpec("EG.FEC.RNEW.ZS", "energy", "energy", "percent", ("renewable energy",)),
    IndicatorSpec("EN.GHG.CO2.MT.CE.AR5", "environment", "emissions and environment", "mt_co2e", ("co2 emissions", "total carbon")),
    IndicatorSpec("NE.TRD.GNFS.ZS", "trade", "trade", "percent_of_gdp", ("trade openness", "trade share of gdp")),
    IndicatorSpec("IT.CEL.SETS.P2", "technology", "technology and connectivity", "per_100_people", ("mobile subscriptions",)),
    IndicatorSpec("IT.NET.BBND.P2", "infrastructure", "infrastructure", "per_100_people", ("broadband", "fixed broadband")),
    IndicatorSpec("GC.DOD.TOTL.GD.ZS", "finance", "finance and debt", "percent_of_gdp", ("government debt", "public debt")),
    IndicatorSpec("FS.AST.DOMS.GD.ZS", "finance", "finance and debt", "percent_of_gdp", ("domestic credit",)),
    IndicatorSpec("SG.GEN.PARL.ZS", "gender", "gender and social indicators", "percent", ("women in parliament",)),
    IndicatorSpec("SL.TLF.CACT.FE.ZS", "gender", "gender and social indicators", "percent", ("female labor force",)),
    IndicatorSpec("IQ.CPA.PUBS.XQ", "institutions", "development and institutions", "index", ("public sector cpiA",)),
    IndicatorSpec("SP.POP.GROW", "demographics", "population and demographics", "percent", ("population growth",)),
)

CI_ENTITIES: tuple[EntitySpec, ...] = (
    EntitySpec("BRA", "COUNTRY", "LCN", "UMC"),
    EntitySpec("USA", "COUNTRY", "NAC", "HIC"),
    EntitySpec("CHN", "COUNTRY", "EAS", "UMC"),
    EntitySpec("IND", "COUNTRY", "SAS", "LMC"),
    EntitySpec("DEU", "COUNTRY", "ECS", "HIC"),
    EntitySpec("NGA", "COUNTRY", "SSF", "LMC"),
    EntitySpec("JPN", "COUNTRY", "EAS", "HIC"),
    EntitySpec("ARG", "COUNTRY", "LCN", "UMC"),
)

CI_AGGREGATES: tuple[EntitySpec, ...] = (
    EntitySpec("LCN", "REGION", "LCN", "AGG"),
)

PILOT_EXTRA_ENTITIES: tuple[EntitySpec, ...] = (
    EntitySpec("MEX", "COUNTRY", "LCN", "UMC"),
    EntitySpec("ZAF", "COUNTRY", "SSF", "UMC"),
    EntitySpec("FRA", "COUNTRY", "ECS", "HIC"),
    EntitySpec("GBR", "COUNTRY", "ECS", "HIC"),
    EntitySpec("IDN", "COUNTRY", "EAS", "UMC"),
    EntitySpec("PAK", "COUNTRY", "SAS", "LMC"),
    EntitySpec("EGY", "COUNTRY", "MEA", "LMC"),
    EntitySpec("VNM", "COUNTRY", "EAS", "LMC"),
    EntitySpec("KEN", "COUNTRY", "SSF", "LMC"),
    EntitySpec("COL", "COUNTRY", "LCN", "UMC"),
    EntitySpec("BGD", "COUNTRY", "SAS", "LMC"),
    EntitySpec("TUR", "COUNTRY", "ECS", "UMC"),
)

CI_YEARS: tuple[str, ...] = ("2018", "2019", "2020", "2021", "2022", "2023")
PILOT_YEARS: tuple[str, ...] = ("2000", "2010", "2015", "2018", "2019", "2020", "2021", "2022", "2023")

OPEN_SET_CONCEPTS: tuple[tuple[str, str], ...] = (
    ("Apple Inc. closing stock price yesterday", "company_market"),
    ("current temperature in Brasília", "weather"),
    ("FIFA world ranking of Brazil", "sports"),
    ("Bitcoin market cap this hour", "realtime_market"),
    ("private household income of a named person", "personal"),
    ("World Bank staff headcount in 2022", "near_domain"),
)


def indicators_for_stage(stage: str) -> tuple[IndicatorSpec, ...]:
    if stage == "ci":
        return CI_INDICATORS
    if stage in {"pilot", "full"}:
        return CI_INDICATORS + PILOT_EXTRA_INDICATORS
    if stage == "expanded":
        return CI_INDICATORS + PILOT_EXTRA_INDICATORS
    raise ValueError(f"Unknown stage {stage!r}")


def entities_for_stage(stage: str) -> tuple[EntitySpec, ...]:
    if stage == "ci":
        return CI_ENTITIES
    if stage in {"pilot", "full"}:
        return CI_ENTITIES + PILOT_EXTRA_ENTITIES
    if stage == "expanded":
        return CI_ENTITIES + PILOT_EXTRA_ENTITIES
    raise ValueError(f"Unknown stage {stage!r}")
