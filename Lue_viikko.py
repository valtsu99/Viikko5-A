# Copyright (c) 2025 Oma Nimi
# License: MIT

import csv
import datetime
from typing import List, Optional, Dict

WEEKDAYS_FI = ["maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai", "sunnuntai"]
EN_TO_FI = {
    "monday": "maanantai", "tuesday": "tiistai", "wednesday": "keskiviikko",
    "thursday": "torstai", "friday": "perjantai", "saturday": "lauantai", "sunday": "sunnuntai"
}

def lue_data(viikko42: str) -> List[List[str]]:
    """Lukee CSV-tiedoston (puolipiste erottimella) ja palauttaa rivit listana."""
    with open(viikko42, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=';')
        return [[cell.strip() for cell in row] for row in reader]

def _parse_date(value: str) -> Optional[datetime.date]:
    """Parsii merkkijonon päivämääräksi. Tukee muodot: d.m.yyyy, yyyy-mm-dd, d/m/yyyy, d.m.yy."""
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
    """Palauttaa viikonpäivän suomeksi annetusta datetime.date-objektista."""
    return WEEKDAYS_FI[d.weekday()]

def _weekday_finnish_from_text(value: str) -> str:
    """Palauttaa viikonpäivän suomeksi merkkijonosta. Ymmärtää päivämäärät, 
    englanninkieliset päivät, suomenkieliset päivät ja numerot (0-6 tai 1-7)."""
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
    """Muotoilee päivämäärän suomalaiseksi muodoksi (pv.kk.vvvv). 
    Palauttaa tyhjän merkkijonon, jos päivämäärä on None."""
    return d.strftime("%d.%m.%Y") if d else ""

def _to_kwh_guess(s: str) -> Optional[float]:
    """Parsii numeroa merkkijonosta ja muuntaa Wh -> kWh 
    (jakaa 1000:lla). Palauttaa tuloksen kWh-yksikössä."""
    if s is None:
        return None
    v = s.strip().replace(" ", "").replace(",", ".")
    if v == "":
        return None
    try:
        num = float(v)
    except Exception:
        return None
    
    # Muuntaa Wh -> kWh (jaa 1000:lla)
    return num / 1000

def _fmt_num_kwh(n: Optional[float]) -> str:
    """Muotoilee kWh-arvon näytettäväksi muodoksi (6 merkkiä, 2 desimaalia, 
    desimaalin erottimena pilkku). Palauttaa tyhjän merkkijonon, jos arvo on None."""
    if n is None:
        return ""
    s = f"{n:6.2f}"
    return s.replace(".", ",")

def _etsi_sarakeindeksit(header: List[str]) -> dict:
    """Etsii sarakeindeksit otsikkoriviltä perinteisesti täsmällisellä osumahaulla.
    Palauttaa sanakirjan sarakeindekseistä (date, ck, cv, ct, pk, pv, pt)."""
    indices = {}
    for i, cell in enumerate(header):
        cell_lower = cell.lower().strip()
        if cell_lower == "päivä" or cell_lower == "day":
            indices["date"] = i
        elif cell_lower == "kulutus vaihe 1" or cell_lower == "kulutus v1":
            indices["ck"] = i
        elif cell_lower == "kulutus vaihe 2" or cell_lower == "kulutus v2":
            indices["cv"] = i
        elif cell_lower == "kulutus vaihe 3" or cell_lower == "kulutus v3":
            indices["ct"] = i
        elif cell_lower == "tuotanto vaihe 1" or cell_lower == "tuotanto v1":
            indices["pk"] = i
        elif cell_lower == "tuotanto vaihe 2" or cell_lower == "tuotanto v2":
            indices["pv"] = i
        elif cell_lower == "tuotanto vaihe 3" or cell_lower == "tuotanto v3":
            indices["pt"] = i
    return indices

def tulosta_taulukko(tiedosto: str):
    """Lukee CSV-tiedoston ja tulostaa käyttäjäystävällisen taulukon 
    sähkönkulutuksesta ja -tuotannosta vaiheittain (kWh), ryhmiteltynä viikonpäivittäin."""
    data = lue_data(tiedosto)
    if not data:
        return

    first = data[0]
    has_header = any(cell and any(ch.isalpha() for ch in cell) for cell in first)

    # Oletusindeksit
    indices = {"date": 0, "ck": 1, "cv": 2, "ct": 3, "pk": 4, "pv": 5, "pt": 6}

    # Jos otsikko löytyy, etsi sarakkeet perinteisesti
    if has_header:
        found_indices = _etsi_sarakeindeksit(first)
        indices.update(found_indices)

    # Ryhmittele päivittäin
    daily_data: Dict[str, Dict] = {}
    
    start = 1 if has_header else 0
    for row in data[start:]:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        
        raw_date = row[indices["date"]] if indices["date"] < len(row) else ""
        d = _parse_date(raw_date)
        weekday = _weekday_finnish_from_text(raw_date) if not d else _weekday_finnish_from_date(d)

        def val(idx):
            """Palauttaa kWh-arvon annetusta sarakeindeksistä."""
            if idx >= len(row):
                return None
            return _to_kwh_guess(row[idx])

        ck = val(indices.get("ck", 1)) or 0
        cv = val(indices.get("cv", 2)) or 0
        ct = val(indices.get("ct", 3)) or 0
        pk = val(indices.get("pk", 4)) or 0
        pv = val(indices.get("pv", 5)) or 0
        pt = val(indices.get("pt", 6)) or 0

        # Lisää viikonpäivälle
        if weekday not in daily_data:
            daily_data[weekday] = {
                "ck": 0, "cv": 0, "ct": 0,
                "pk": 0, "pv": 0, "pt": 0,
                "date": d
            }
        
        daily_data[weekday]["ck"] += ck
        daily_data[weekday]["cv"] += cv
        daily_data[weekday]["ct"] += ct
        daily_data[weekday]["pk"] += pk
        daily_data[weekday]["pv"] += pv
        daily_data[weekday]["pt"] += pt

    # Tulostusotsikko
    print("Viikon 42 sähkönkulutus ja -tuotanto")
    print()
    print(f"{'Päivä':13} {'Pvm':12}   {'Kulutus [kWh]':27} {'Tuotanto [kWh]':23}")
    print(f"{'':13} {'(pv.kk.vvvv)':12}  {'v1':7}{'v2':8}{'v3':8}    {'v1':7}{'v2':8}{'v3':8}")
    print("-" * 75)

    # Tulosta viikonpäivät järjestyksessä
    for weekday in WEEKDAYS_FI:
        if weekday in daily_data:
            data_entry = daily_data[weekday]
            date_str = _format_date_fi(data_entry["date"]) if data_entry["date"] else ""
            
            ck_s = _fmt_num_kwh(data_entry["ck"])
            cv_s = _fmt_num_kwh(data_entry["cv"])
            ct_s = _fmt_num_kwh(data_entry["ct"])
            pk_s = _fmt_num_kwh(data_entry["pk"])
            pv_s = _fmt_num_kwh(data_entry["pv"])
            pt_s = _fmt_num_kwh(data_entry["pt"])

            print(f"{weekday:13} {date_str:12}   {ck_s:7} {cv_s:7} {ct_s:7}    {pk_s:7} {pv_s:7} {pt_s:7}")

if __name__ == "__main__":
    tulosta_taulukko("viikko42.csv")



