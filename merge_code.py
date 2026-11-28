import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
GHG_FILE = BASE_DIR / "GHG.xlsx"
GDP_FILE = BASE_DIR / "GPD.xlsx"
OUTPUT_FILE = BASE_DIR / "Merged_files.xlsx"

ghg = pd.read_excel(GHG_FILE, sheet_name=0)
gdp = pd.read_excel(GDP_FILE, sheet_name=0)

ghg.columns = ghg.columns.astype(str).str.strip()
gdp.columns = gdp.columns.astype(str).str.strip()
ghg = ghg.rename(columns={"Party": "Country"})

country_mapping = {
    "United States of America": "United States",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom"
}

ghg["Country"] = ghg["Country"].str.strip().replace(country_mapping)
gdp["Country"] = gdp["Country"].str.strip().replace(country_mapping)

years = [str(year) for year in range(1990, 2021)]

unmatched_ghg = ghg[~ghg["Country"].isin(gdp["Country"])].copy()
ghg = ghg[ghg["Country"] != "European Union (Convention)"].copy()

ghg_long = ghg.melt(
    id_vars=["Country"],
    value_vars=years,
    var_name="Year",
    value_name="GHG_kt_CO2e"
)

if "IndicatorName" in gdp.columns:
    gdp = gdp[gdp["IndicatorName"] == "Gross Domestic Product (GDP)"].copy()

gdp_ids = ["Country"]
if "CountryID" in gdp.columns:
    gdp_ids.insert(0, "CountryID")

gdp_long = gdp.melt(
    id_vars=gdp_ids,
    value_vars=years,
    var_name="Year",
    value_name="GDP_constant_2020_USD"
)

ghg_long["Year"] = ghg_long["Year"].astype(int)
gdp_long["Year"] = gdp_long["Year"].astype(int)
ghg_long["GHG_kt_CO2e"] = pd.to_numeric(ghg_long["GHG_kt_CO2e"], errors="raise")
gdp_long["GDP_constant_2020_USD"] = pd.to_numeric(gdp_long["GDP_constant_2020_USD"], errors="raise")

merged = pd.merge(
    gdp_long, ghg_long,
    on=["Country", "Year"],
    how="inner",
    validate="one_to_one"
)

columns = ["Country", "Year", "GDP_constant_2020_USD", "GHG_kt_CO2e"]
if "CountryID" in merged.columns:
    columns.insert(0, "CountryID")
merged = merged[columns]
merged = merged.sort_values(by=["Country", "Year"]).reset_index(drop=True)

matched_countries = merged["Country"].nunique()
number_of_years = merged["Year"].nunique()
total_rows = len(merged)
missing_values = merged.isnull().sum().sum()
duplicate_rows = merged.duplicated(subset=["Country", "Year"]).sum()

merge_notes = pd.DataFrame({
    "Description": [
        "Project", "GHG source", "GDP source", "GHG measurement",
        "GDP measurement", "Analysis period", "Merge method",
        "Matching variables", "Matched countries", "Number of years",
        "Total merged rows", "Missing values", "Duplicate rows",
        "Unmatched GHG entities", "Excluded regional aggregate"
    ],
    "Details": [
        "Climate Change & Economic Decoupling", "UNFCCC",
        "UNSD National Accounts Main Aggregates",
        "Total GHG excluding LULUCF (kt CO2e)",
        "GDP at constant 2020 prices (USD)", "1990-2020", "Inner join",
        "Country and Year", matched_countries, number_of_years,
        total_rows, missing_values, duplicate_rows, len(unmatched_ghg),
        "European Union (Convention)"
    ]
})

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    merged.to_excel(writer, sheet_name="Merged Data", index=False)
    merge_notes.to_excel(writer, sheet_name="Merge Notes", index=False)
    unmatched_ghg.to_excel(writer, sheet_name="Unmatched GHG", index=False)

print("Merge completed successfully!")
print(f"Output: {OUTPUT_FILE}")
print(f"Matched countries: {matched_countries}")
print(f"Years: {number_of_years}")
print(f"Merged rows: {total_rows}")
print(f"Missing values: {missing_values}")
print(f"Duplicate rows: {duplicate_rows}")
print(f"Unmatched GHG entities: {len(unmatched_ghg)}")
print("\nFirst 10 rows:")
print(merged.head(10))
