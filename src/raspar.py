"""Raspa tabelas do painel Power BI da Anvisa (Constituintes IN 28) via API querydata.

Uso: python src/raspar.py
Roda a partir de qualquer diretorio; salva sempre em ./data/ na raiz do repo.
"""
import csv
import re
from pathlib import Path

import requests

from dsr_decoder import decode_dsr

URL = "https://wabi-brazil-south-api.analysis.windows.net/public/reports/querydata?synchronous=true"
RESOURCE_KEY = "458ce16a-f74b-4e92-977a-e12e2927d746"
DATASET_ID = "1ea16037-e72d-4950-bdf2-11f2035c6340"
REPORT_ID = "7c135d66-9ea8-4dfc-bd0e-d7b0b78b1b7c"
MODEL_ID = 2075532

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TABELAS = {
    "constituintes_suplementos.csv": {
        "order_by": "Constituintes Autorizados",
        "visual_id": "7318f33b0879d102f57e",
        "colunas": [
            "Constituintes Autorizados",
            "CAS",
            "Especificações",
            "Função",
            "Alegações autorizadas e requisitos para uso da alegação",
            "Requisitos de Rotulagem Complementar e outros",
            "Outras Informações",
        ],
    },
    "limites_por_faixa_etaria.csv": {
        "order_by": "Nutriente/Substância Bioativa/Enzima",
        "visual_id": "a5961cd5a3a7abff0103",
        "colunas": [
            "Categoria",
            "Nutriente/Substância Bioativa/Enzima",
            "0 a 6 meses",
            "7 a 11 meses",
            "1 a 3 anos",
            "4 a 8 anos ",
            "9 a 18 anos",
            "Maiores 19 anos ",
            "Lactantes",
            "Gestantes ",
            "Observações",
        ],
    },
}

# Erros de digitação confirmados no painel da Anvisa (verificados contra o texto
# oficial da IN 28/2018 e da IN 102/2021 no DOU). O painel raspado tem esses valores
# errados na origem; corrigimos aqui para que toda atualização automática já saia certa,
# em vez de precisar de correção manual a cada raspagem.
CORRECOES_CONSTITUINTES = {
    # (nome exato do constituinte): {coluna: valor_correto}
    "Succinato ácido de D-alfa-tocoferila": {"CAS": "4345-03-3"},  # painel trazia "893081", não é CAS válido
}

CORRECOES_LIMITES = {
    # (nome exato do nutriente, coluna de faixa etária): valor_correto
    ("Ácido Clorogênico", "Maiores 19 anos "): "Mínimo: Não estabelecido\n\nMáximo: 400 mg",
}


def build_body(colunas, order_by, visual_id):
    select = [
        {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": col},
         "Name": f"Consulta1.{col}"}
        for col in colunas
    ]
    return {
        "version": "1.0.0",
        "queries": [{
            "Query": {"Commands": [{
                "SemanticQueryDataShapeCommand": {
                    "Query": {
                        "Version": 2,
                        "From": [{"Name": "c", "Entity": "Contituintes IN 28", "Type": 0}],
                        "Select": select,
                        "OrderBy": [{"Direction": 1, "Expression": {
                            "Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": order_by}
                        }}]
                    },
                    "Binding": {
                        "Primary": {"Groupings": [{"Projections": list(range(len(colunas)))}]},
                        "DataReduction": {"DataVolume": 3, "Primary": {"Window": {"Count": 1000}}},
                        "Version": 1
                    },
                    "ExecutionMetricsKind": 1
                }
            }]},
            "QueryId": "",
            "ApplicationContext": {
                "DatasetId": DATASET_ID,
                "Sources": [{"ReportId": REPORT_ID, "VisualId": visual_id}]
            }
        }],
        "cancelQueries": [],
        "modelId": MODEL_ID,
    }


def fetch(colunas, order_by, visual_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:153.0) Gecko/20100101 Firefox/153.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "X-PowerBI-ResourceKey": RESOURCE_KEY,
        "Origin": "https://app.powerbi.com",
        "Referer": "https://app.powerbi.com/",
    }
    r = requests.post(URL, headers=headers, json=build_body(colunas, order_by, visual_id), timeout=30)
    r.raise_for_status()
    return r.json()


def linha_para_csv(row, colunas):
    return [row.get(f"Consulta1.{c}") or "" for c in colunas]


def aplicar_correcoes_constituintes(linhas, colunas):
    idx_nome = colunas.index("Constituintes Autorizados")
    for linha in linhas:
        correcao = CORRECOES_CONSTITUINTES.get(linha[idx_nome].strip())
        if correcao:
            for col, valor in correcao.items():
                linha[colunas.index(col)] = valor
    return linhas


def aplicar_correcoes_limites(linhas, colunas):
    idx_nome = colunas.index("Nutriente/Substância Bioativa/Enzima")
    for linha in linhas:
        nome = linha[idx_nome].strip()
        for (nome_alvo, col), valor in CORRECOES_LIMITES.items():
            if nome == nome_alvo:
                linha[colunas.index(col)] = valor
    return linhas


CORRECOES_POR_ARQUIVO = {
    "constituintes_suplementos.csv": aplicar_correcoes_constituintes,
    "limites_por_faixa_etaria.csv": aplicar_correcoes_limites,
}


def main():
    DATA_DIR.mkdir(exist_ok=True)
    for nome_arquivo, cfg in TABELAS.items():
        colunas = cfg["colunas"]
        rows = decode_dsr(fetch(colunas, cfg["order_by"], cfg["visual_id"]))
        linhas = [linha_para_csv(row, colunas) for row in rows]
        linhas = CORRECOES_POR_ARQUIVO[nome_arquivo](linhas, colunas)

        out_path = DATA_DIR / nome_arquivo
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(colunas)
            writer.writerows(linhas)
        print(f"{len(linhas)} linhas salvas em {out_path}")


if __name__ == "__main__":
    main()
