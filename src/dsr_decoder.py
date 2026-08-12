"""Decodifica o DSR comprimido do Power BI (formato delta com dicionarios de valores).

Formato reverse-engineered a partir das respostas reais da API querydata.
Cada entrada de PH[0].DM0 e uma linha: "R" (bitmask) marca colunas que repetem
o valor da linha anterior, "O" marca colunas nulas nesta linha, e "C" fornece
os valores (indice no dicionario da coluna, ou literal quando o dicionario
ainda nao contem o valor) para as colunas restantes, na ordem das colunas.
"""
import json
import sys


def decode_dsr(response_json):
    data = response_json["results"][0]["result"]["data"]
    ds0 = data["dsr"]["DS"][0]
    select = data["descriptor"]["Select"]
    dicts = ds0["ValueDicts"]
    dm0 = ds0["PH"][0]["DM0"]

    cols = [f"D{i}" for i in range(len(select))]
    names = [s["Name"] for s in select]
    col_dicts = [list(dicts[dn]) for dn in cols]

    n = len(cols)
    current = [None] * n

    rows = []
    for entry in dm0:
        null_mask = entry.get("Ø", 0)
        repeat_mask = entry.get("R", 0)
        c_queue = list(entry.get("C", []))
        for i in range(n):
            if repeat_mask & (1 << i):
                continue
            if null_mask & (1 << i):
                current[i] = None
                continue
            v = c_queue.pop(0)
            if isinstance(v, int):
                current[i] = col_dicts[i][v]
            else:
                current[i] = v
                col_dicts[i].append(v)
        rows.append(dict(zip(names, current)))
    return rows


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "test_response.json"
    rows = decode_dsr(json.load(open(path, encoding="utf-8")))
    print(f"{len(rows)} linhas decodificadas")
    print(json.dumps(rows[:3], ensure_ascii=False, indent=2))
