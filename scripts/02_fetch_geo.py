
from pathlib import Path
import json, os, requests, time
GEO = str(Path(__file__).resolve().parents[1] / "data" / "geo"); os.makedirs(GEO, exist_ok=True)
UFS = {"AC":12,"AL":27,"AP":16,"AM":13,"BA":29,"CE":23,"DF":53,"ES":32,"GO":52,"MA":21,"MT":51,
       "MS":50,"MG":31,"PA":15,"PB":25,"PR":41,"PE":26,"PI":22,"RJ":33,"RN":24,"RS":43,"RO":11,
       "RR":14,"SC":42,"SP":35,"SE":28,"TO":17}
S = requests.Session(); S.headers["User-Agent"]="Mozilla/5.0 election-analysis"
def get(url, **kw):
    for a in range(4):
        try:
            r = S.get(url, timeout=90, **kw)
            if r.status_code == 200: return r
        except Exception as e: print("retry", e)
        time.sleep(2)
    raise RuntimeError(url)

r = get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios")
open(f"{GEO}/municipios_ibge.json","wb").write(r.content)
muns = r.json(); print("municipios:", len(muns))

ufs = get("https://servicodados.ibge.gov.br/api/v4/malhas/paises/BR",
          params={"formato":"application/vnd.geo+json","qualidade":"intermediaria","intrarregiao":"UF"})
open(f"{GEO}/brasil_uf.geojson","wb").write(ufs.content); print("uf geojson KB", len(ufs.content)//1024)

for sigla, code in UFS.items():
    p = f"{GEO}/mun_{sigla}.geojson"
    if os.path.exists(p) and os.path.getsize(p) > 1000: continue
    rr = get(f"https://servicodados.ibge.gov.br/api/v4/malhas/estados/{code}",
             params={"formato":"application/vnd.geo+json","qualidade":"intermediaria","intrarregiao":"municipio"})
    open(p,"wb").write(rr.content)
    print(sigla, len(rr.content)//1024, "KB")
