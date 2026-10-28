
from pathlib import Path
import duckdb
ROOT = str(Path(__file__).resolve().parents[1]); C=f"{ROOT}/data/cache"
con = duckdb.connect(); con.execute(f"SET memory_limit='3GB'; SET threads=4; SET temp_directory='{ROOT}/data/.tmp'")
con.execute(f"CREATE VIEW cw AS SELECT * FROM '{C}/crosswalk.parquet'")

for tbl in ["cand_mun","detalhe_mun","pres_munzona"]:
    con.execute(f"""
    COPY (
      SELECT t.*, w.CD_IBGE, w.NOME_IBGE
      FROM '{C}/{tbl}.parquet' t
      LEFT JOIN cw w ON t.SG_UF = w.SG_UF AND LPAD(t.CD_MUNICIPIO,5,'0') = w.CD_TSE
    ) TO '{C}/{tbl}_ibge.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)""")
    print(tbl, con.execute(f"SELECT count(*), count(CD_IBGE) FROM '{C}/{tbl}_ibge.parquet'").fetchone())
print(con.execute(f"SELECT count(*) FROM '{C}/cand_mun_ibge.parquet'").fetchone())
