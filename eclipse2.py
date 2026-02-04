import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Dict, List

import requests

HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"

PLANET_IDS = {
    "Mercury": "199",
    "Venus": "299",
    "Mars": "499",
    "Jupiter": "599",
    "Saturn": "699",
    "Uranus": "799",
    "Neptune": "899",
}

MU_SUN = 132712440041.93938  # km^3/s^2
AU_KM = 149597870.700

@dataclass
class Elements:
    epoch_jd: float
    a_km: float
    Omega_deg: float
    w_deg: float
    M_deg: float

def jd_from_datetime(dt: datetime) -> float:
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute/60)/24
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + (A // 4)
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + B - 1524.5

def circular_span_deg(angles: List[float]) -> float:
    a = sorted([x % 360 for x in angles])
    gaps = [a[i+1]-a[i] for i in range(len(a)-1)]
    gaps.append(a[0]+360-a[-1])
    return 360 - max(gaps)

def fetch_elements(body_id: str, epoch_dt: datetime, sess) -> Elements:
    epoch = epoch_dt.strftime("%Y-%m-%d %H:%M")
    epoch_jd = jd_from_datetime(epoch_dt)

    params = {
        "format":"json",
        "COMMAND":f"'{body_id}'",
        "EPHEM_TYPE":"ELEMENTS",
        "CENTER":"'500@10'",
        "START_TIME":f"'{epoch}'",
        "STOP_TIME":f"'{epoch}'",
        "STEP_SIZE":"'1 d'",
        "CSV_FORMAT":"YES"
    }

    r = sess.get(HORIZONS_API, params=params)
    txt = r.json()["result"]

    def f(p): 
        return float(re.search(p, txt).group(1))

    # Try to get semimajor axis A (in AU) in a format‑tolerant way
    m_au = re.search(r"(?i)\bA\s*=\s*([0-9Ee\+\-\.]+)\s*[Aa][Uu]\b", txt)

    if m_au:
        a_km = float(m_au.group(1)) * AU_KM
    else:
        # Fallback: parse from the CSV block between $$SOE / $$EOE
        m_block = re.search(r"\$\$SOE(.*?)\$\$EOE", txt, re.S)
        if not m_block:
            raise ValueError("Could not find semimajor axis (A) in Horizons output.")

        lines = [ln.strip() for ln in m_block.group(1).strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            raise ValueError("Unexpected Horizons CSV format (not enough lines).")

        header = [h.strip() for h in lines[0].split(",")]
        data = [d.strip() for d in lines[1].split(",")]

        a_index = None
        for i, h in enumerate(header):
            name = h.upper()
            if name == "A" or name.startswith("A(") or name.startswith("A "):
                a_index = i
                break

        if a_index is None or a_index >= len(data):
            raise ValueError("Could not locate semimajor axis column 'A' in Horizons CSV.")

        a_km = float(data[a_index]) * AU_KM

    return Elements(
        epoch_jd,
        a_km,
        f(r"OM\s*=\s*([0-9Ee\+\-\.]+)"),
        f(r"W\s*=\s*([0-9Ee\+\-\.]+)"),
        f(r"MA\s*=\s*([0-9Ee\+\-\.]+)")
    )

def mean_motion(a_km):
    return math.sqrt(MU_SUN/(a_km**3))*86400

def mean_longitude(el):
    return math.radians((el.Omega_deg+el.w_deg+el.M_deg)%360)

def fetch_lon(body_id, jd, sess):
    params={
        "format":"json",
        "COMMAND":f"'{body_id}'",
        "EPHEM_TYPE":"OBSERVER",
        "CENTER":"'500@399'",
        "TLIST":str(jd),
        "QUANTITIES":"'31'",
        "CSV_FORMAT":"YES"
    }
    r=sess.get(HORIZONS_API,params=params)
    txt=r.json()["result"]
    m=re.search(r"\$\$SOE(.*?)\$\$EOE",txt,re.S)
    line=m.group(1).strip().splitlines()[0]
    vals=[float(v) for v in line.split(",") if re.match(r"^-?\d",v)]
    return vals[-2]%360

def main():
    start=date(2026,1,1)
    end=date(2028,12,31)
    span_thresh=10
    planets=list(PLANET_IDS.keys())
    ref="Jupiter"

    mid=datetime(2027,1,1)

    with requests.Session() as sess:
        elems={}
        for p in planets:
            elems[p]=fetch_elements(PLANET_IDS[p],mid,sess)

        lam={p:mean_longitude(elems[p]) for p in planets}
        n={p:mean_motion(elems[p].a_km) for p in planets}
        t0=elems[ref].epoch_jd

        # 候補生成（Mars基準）
        seed="Mars"
        cand=[]
        for k in range(-200,200):
            t=t0+(lam[ref]-lam[seed]+2*math.pi*k)/(n[seed]-n[ref])
            if jd_from_datetime(datetime(start.year,start.month,start.day))<=t<=jd_from_datetime(datetime(end.year,end.month,end.day)):
                cand.append(t)

        print("Analytic candidates:",len(cand))

        hits=[]
        for jd in cand:
            lons=[fetch_lon(PLANET_IDS[p],jd,sess) for p in planets]
            span=circular_span_deg(lons)
            if span<=span_thresh:
                hits.append((jd,span))

    print("Hits:",len(hits))
    for jd,span in hits:
        dt=datetime(2000,1,1,12)+timedelta(days=(jd-2451545))
        print(dt,span)

if __name__=="__main__":
    main()
