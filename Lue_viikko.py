# Copyright (c) 2025 Oma Nimi
# License: MIT



import csv
import datetime
from typing import List, Optional

WEEKDAYS_FI = ["maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai", "sunnuntai"]
EN_TO_FI = {
    "monday": "maanantai", "tuesday": "tiistai", "wednesday": "keskiviikko",
    "thursday": "torstai", "friday": "perjantai", "saturday": "lauantai", "sunday": "sunnuntai"
}

def lue_data(viikko42: str) -> List[List[str]]:
    with open(viikko42, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=';')
        return [[cell.strip() for cell in row] for row in reader]

def _parse_date(value: str) -> Optional[datetime.date]:
    if value is None:
        return None
    v = value.strip().lstrip("\ufeff")
    if not v:
        return None
    v = v.split("T")[0].split()[0]
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%y"):
        try:
            return datetime.datetime.strptime(v, fmt).date()
        except Exception:
            pass
    try:
        return datetime.date.fromisoformat(v)
    except Exception:
        return None

def _weekday_finnish_from_date(d: datetime.date) -> str:
    return WEEKDAYS_FI[d.weekday()]

def _weekday_finnish_from_text(value: str) -> str:
    v = value.strip()
    if not v:
        return ""
    d = _parse_date(v)
    if d:
        return _weekday_finnish_from_date(d)
    low = v.lower()
    if low in EN_TO_FI:
        return EN_TO_FI[low]
    if low in WEEKDAYS_FI:
        return low
    if low.isdigit():
        n = int(low)
        if 0 <= n <= 6:
            return WEEKDAYS_FI[n]
        if 1 <= n <= 7:
            return WEEKDAYS_FI[n-1]
    return v

def _format_date_fi(d: Optional[datetime.date]) -> str:
    return d.strftime("%d.%m.%Y") if d else ""

def _to_kwh_guess(s: str) -> Optional[float]:
    
    if s is None:
        return None
    v = s.strip().replace(" ", "").replace(",", ".")
    if v == "":
        return None
    try:
        num = float(v)
    except Exception:
        return None
    
    if abs(num) > 100:  
        num = num / 1000.0
    return num

def _fmt_num_kwh(n: Optional[float]) -> str:
    if n is None:
        return ""
    s = f"{n:6.2f}"
    return s.replace(".", ",")

def tulosta_taulukko(tiedosto: str):
    data = lue_data(tiedosto)
    if not data:
        return

    
    first = data[0]
    has_header = any(cell and any(ch.isalpha() for ch in cell) for cell in first)

    
    def default_indices():
        return {"date":0, "ck":1, "cv":2, "ct":3, "pk":4, "pv":5, "pt":6}

    indices = default_indices()

    if has_header:
        header = [c.lower() for c in first]
        # etsitään päivämäärä- ja kulutus/tuotanto-sarakkeet heuristiikalla
        for i, h in enumerate(header):
            if "pvm" in h or "päiv" in h or "date" in h:
                indices["date"] = i
            if "kulutus" in h and ("vaihe 1" in h or "v1" in h or "vaihe1" in h or "1" in h):
                indices["ck"] = i
            if "kulutus" in h and ("vaihe 2" in h or "v2" in h or "vaihe2" in h or "2" in h):
                indices["cv"] = i
            if "kulutus" in h and ("vaihe 3" in h or "v3" in h or "vaihe3" in h or "3" in h):
                indices["ct"] = i
            if "tuotanto" in h and ("vaihe 1" in h or "v1" in h or "vaihe1" in h or "1" in h):
                indices["pk"] = i
            if "tuotanto" in h and ("vaihe 2" in h or "v2" in h or "vaihe2" in h or "2" in h):
                indices["pv"] = i
            if "tuotanto" in h and ("vaihe 3" in h or "v3" in h or "vaihe3" in h or "3" in h):
                indices["pt"] = i
       
        if len(header) >= 7:
           
            d = indices.get("date", 0)
            if d + 6 < len(header):
                indices = {"date": d, "ck": d+1, "cv": d+2, "ct": d+3, "pk": d+4, "pv": d+5, "pt": d+6}

    
    # Tulostusotsikko
    print("Viikon 42 sähkönkulutus ja -tuotanto")
    print()
    print(f"{'Päivä':13} {'Pvm':12}   {'Kulutus [kWh]':27} {'Tuotanto [kWh]':23}")
    print(f"{'':13} {'(pv.kk.vvvv)':12}  {'v1':7}{'v2':8}{'v3':8}    {'v1':7}{'v2':8}{'v3':8}")
    print("-" * 75)

    start = 1 if has_header else 0
    for row in data[start:]:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        
        raw_date = row[indices["date"]] if indices["date"] < len(row) else ""
        d = _parse_date(raw_date)
        weekday = _weekday_finnish_from_text(raw_date) if not d else _weekday_finnish_from_date(d)
        date_str = _format_date_fi(d)

        
        def val(idx):
            if idx >= len(row):
                return None
            return _to_kwh_guess(row[idx])

        ck = val(indices["ck"])
        cv = val(indices["cv"])
        ct = val(indices["ct"])
        pk = val(indices["pk"])
        pv = val(indices["pv"])
        pt = val(indices["pt"])

        
        ck_s = _fmt_num_kwh(ck)
        cv_s = _fmt_num_kwh(cv)
        ct_s = _fmt_num_kwh(ct)
        pk_s = _fmt_num_kwh(pk)
        pv_s = _fmt_num_kwh(pv)
        pt_s = _fmt_num_kwh(pt)

        print(f"{weekday:13} {date_str:12}   {ck_s:7} {cv_s:7} {ct_s:7}    {pk_s:7} {pv_s:7} {pt_s:7}")

if __name__ == "__main__":
    tulosta_taulukko("viikko42.csv")



