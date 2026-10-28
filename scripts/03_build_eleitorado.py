
from pathlib import Path
import duckdb, glob, os, time
ROOT = str(Path(__file__).resolve().parents[1]); OUT=f"{ROOT}/data/cache"
os.makedirs(f"{ROOT}/data/.tmp", exist_ok=True)
files = sorted(glob.glob(f"{ROOT}/data/source/perfil/*.csv"))
if not files:
    raise SystemExit(
        "No electorate files found in data/source/perfil/.\n"
        "Run Step 0 of 00_data_preprocessing_validation.ipynb (it downloads perfil_eleitorado_2026)."
    )
print(len(files), "files")
con = duckdb.connect(); con.execute(f"SET memory_limit='2.5GB'; SET threads=4; SET temp_directory='{ROOT}/data/.tmp'; SET preserve_insertion_order=false")
opts = "delim=';', header=true, encoding='latin-1', all_varchar=true, quote='\"'"
t=time.time()
con.execute(f"""
COPY (
 SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, CAST(CD_FAIXA_ETARIA AS INT) CD_FX,
        DS_FAIXA_ETARIA, CAST(CD_GENERO AS INT) CD_GEN, DS_GENERO,
        SUM(CAST(QT_ELEITORES AS BIGINT)) ELEITORES,
        SUM(CAST(QT_ELEITORES_BIOMETRIA AS BIGINT)) BIOMETRIA
 FROM read_csv({files}, {opts}, union_by_name=true)
 GROUP BY ALL
) TO '{OUT}/elei_idade.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)""")
print("idade", round(time.time()-t,1))
t=time.time()
con.execute(f"""
COPY (
 SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, DS_GRAU_ESCOLARIDADE, DS_RACA_COR, DS_ESTADO_CIVIL,
        SUM(CAST(QT_ELEITORES AS BIGINT)) ELEITORES
 FROM read_csv({files}, {opts}, union_by_name=true)
 GROUP BY ALL
) TO '{OUT}/elei_perfil.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)""")
print("perfil", round(time.time()-t,1))
print(con.execute(f"SELECT (SELECT count(*) FROM '{OUT}/elei_idade.parquet'), (SELECT sum(ELEITORES) FROM '{OUT}/elei_idade.parquet'), (SELECT count(*) FROM '{OUT}/elei_perfil.parquet')").fetchall())
