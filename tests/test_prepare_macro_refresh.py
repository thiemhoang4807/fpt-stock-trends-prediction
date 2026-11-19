import io
from pathlib import Path
import sys
from zipfile import ZipFile

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from prepare_macro_refresh import normalize_annual_cpi, normalize_gold


def test_gold_export_parses_day_first_and_cuts_before_future_prices():
    content = (
        "Ngày,Lần cuối,Mở,Cao,Thấp\n"
        "1/10/2025,4000,4000,4001,3999\n"
        '30/09/2025,"3,858.51",3850,3860,3840\n'
        "2/1/2007,640.15,636.65,641.25,636.55\n"
        "1/1/2007,636.25,636.25,636.65,636.25\n"
    ).encode("utf-8-sig")
    gold, audit = normalize_gold(content)
    assert (
        gold.time.tolist()
        == pd.to_datetime(["2007-01-01", "2007-01-02", "2025-09-30"]).tolist()
    )
    assert gold.close.tolist() == [636.25, 640.15, 3858.51]
    assert audit["rows_after_cutoff_removed"] == 1


@pytest.mark.parametrize("missing_year", [False, True])
def test_world_bank_cpi_covers_all_required_years(missing_year):
    years = list(range(2005, 2026))
    values = ["3.5" if not (missing_year and year == 2006) else "" for year in years]
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "API_FP.CPI.TOTL.ZG_DS2_en_csv_v2_1.csv",
            "Data Source,World Development Indicators\n\nLast Updated Date,2026-11-11\n\n"
            "Country Name,Country Code,Indicator Name,Indicator Code,"
            + ",".join(map(str, years))
            + "\nViet Nam,VNM,Inflation,FP.CPI.TOTL.ZG,"
            + ",".join(values),
        )
    if missing_year:
        with pytest.raises(ValueError, match="missing or nonfinite"):
            normalize_annual_cpi(buffer.getvalue())
    else:
        cpi = normalize_annual_cpi(buffer.getvalue())
        assert cpi.year.tolist() == list(range(2005, 2025))
        assert cpi.cpi_annual_inflation_pct.eq(3.5).all()
        assert cpi.publication_date.isna().all()
