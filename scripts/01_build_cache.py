
"""Build compact parquet caches from the raw TSE 2026 datasets."""
from pathlib import Path
import duckdb, os, time, glob

ROOT = str(Path(__file__).resolve().parents[1])
OUT = f"{ROOT}/data/cache"
os.makedirs(OUT, exist_ok=True)
os.makedirs(f"{ROOT}/data/.tmp", exist_ok=True)

con = duckdb.connect()
con.execute(f"SET memory_limit='3GB'; SET threads=5; SET temp_directory='{ROOT}/data/.tmp'; SET preserve_insertion_order=false;")

cand_files = sorted(f for f in glob.glob(f"{ROOT}/data/raw/votacao_candidato_munzona_2026/*.csv")
                    if not f.endswith(("_BR.csv", "_BRASIL.csv")))
det_files = sorted(f for f in glob.glob(f"{ROOT}/data/raw/detalhe_votacao_munzona_2026/*.csv")
                   if not f.endswith(("_BR.csv", "_BRASIL.csv")))
if not cand_files or not det_files:
    raise SystemExit(
        "No TSE result files found under data/raw/.\n"
        "Run Step 0 of 00_data_preprocessing_validation.ipynb (it downloads them), or put the\n"
        "votacao_candidato_munzona_2026/ and detalhe_votacao_munzona_2026/ folders in data/raw/."
    )
print(len(cand_files), "candidate files;", len(det_files), "detail files")

opts = "delim=';', header=true, encoding='latin-1', all_varchar=true, quote='\"'"

t = time.time()
con.execute(f"""
COPY (
  SELECT SG_UF, SG_UE, NM_UE, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA,
         CAST(CD_CARGO AS INT) AS CD_CARGO, DS_CARGO, CAST(NR_TURNO AS INT) AS NR_TURNO,
         SQ_CANDIDATO, NR_CANDIDATO, NM_CANDIDATO, NM_URNA_CANDIDATO,
         NR_PARTIDO, SG_PARTIDO, NM_PARTIDO, TP_AGREMIACAO,
         NR_FEDERACAO, SG_FEDERACAO, NM_FEDERACAO, DS_COMPOSICAO_FEDERACAO,
         SQ_COLIGACAO, NM_COLIGACAO,
         DS_SITUACAO_CANDIDATURA, DS_SITUACAO_JULGAMENTO, DS_SIT_TOT_TURNO,
         NM_TIPO_DESTINACAO_VOTOS, ST_VOTO_EM_TRANSITO,
         SUM(CAST(QT_VOTOS_NOMINAIS AS BIGINT)) AS VOTOS
  FROM read_csv({cand_files}, {opts}, union_by_name=true)
  WHERE SG_UF NOT IN ('BR','BRASIL')
  GROUP BY ALL
) TO '{OUT}/cand_mun.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
""")
print("cand_mun", round(time.time()-t,1), "s")

t = time.time()
con.execute(f"""
COPY (
  SELECT SG_UF, SG_UE, NM_UE, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA,
         CAST(CD_CARGO AS INT) CD_CARGO, DS_CARGO, CAST(NR_TURNO AS INT) NR_TURNO,
         SUM(CAST(QT_APTOS AS BIGINT)) QT_APTOS,
         SUM(CAST(QT_COMPARECIMENTO AS BIGINT)) QT_COMPARECIMENTO,
         SUM(CAST(QT_ABSTENCOES AS BIGINT)) QT_ABSTENCOES,
         SUM(CAST(QT_TOTAL_SECOES AS BIGINT)) QT_TOTAL_SECOES,
         SUM(CAST(QT_ELEITORES_SECOES_NAO_INSTALADAS AS BIGINT)) QT_ELEITORES_SECOES_NAO_INSTALADAS,
         SUM(CAST(QT_VOTOS AS BIGINT)) QT_VOTOS,
         SUM(CAST(QT_TOTAL_VOTOS_VALIDOS AS BIGINT)) QT_TOTAL_VOTOS_VALIDOS,
         SUM(CAST(QT_VOTOS_NOMINAIS_VALIDOS AS BIGINT)) QT_VOTOS_NOMINAIS_VALIDOS,
         SUM(CAST(QT_TOTAL_VOTOS_LEG_VALIDOS AS BIGINT)) QT_TOTAL_VOTOS_LEG_VALIDOS,
         SUM(CAST(QT_VOTOS_LEG_VALIDOS AS BIGINT)) QT_VOTOS_LEG_VALIDOS,
         SUM(CAST(QT_VOTOS_BRANCOS AS BIGINT)) QT_VOTOS_BRANCOS,
         SUM(CAST(QT_TOTAL_VOTOS_NULOS AS BIGINT)) QT_TOTAL_VOTOS_NULOS,
         SUM(CAST(QT_TOTAL_VOTOS_ANULADOS AS BIGINT)) QT_TOTAL_VOTOS_ANULADOS
  FROM read_csv({det_files}, {opts}, union_by_name=true)
  WHERE SG_UF NOT IN ('BR','BRASIL')
  GROUP BY ALL
) TO '{OUT}/detalhe_mun.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
""")
print("detalhe", round(time.time()-t,1), "s")

t = time.time()
con.execute(f"""
COPY (
  SELECT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, CAST(NR_TURNO AS INT) NR_TURNO,
         CAST(NR_VOTAVEL AS INT) NR_VOTAVEL, NM_VOTAVEL, SQ_CANDIDATO,
         SUM(CAST(QT_VOTOS AS BIGINT)) VOTOS
  FROM read_csv('{ROOT}/data/raw/votacao_secao_2026_BR/votacao_secao_2026_BR.csv', {opts})
  GROUP BY ALL
) TO '{OUT}/pres_munzona.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
""")
print("pres", round(time.time()-t,1), "s")
print(con.execute(f"SELECT (SELECT count(*) FROM '{OUT}/cand_mun.parquet') a, (SELECT count(*) FROM '{OUT}/detalhe_mun.parquet') b, (SELECT count(*) FROM '{OUT}/pres_munzona.parquet') c").df())
