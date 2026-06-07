#!/usr/bin/env python3
"""Download per-state population estimates from IBGE and save them as data/populacao_uf.csv.

This is reference data, not a downloaded dataset like SADIPEM/transferências —
it's small, changes once a year, and several analysis scripts need it (e.g. to
turn raw totals into per-capita figures so São Paulo doesn't dominate every
comparison just by being the most populous state). Saving it locally means the
analysis scripts have no runtime network dependency, and anyone cloning the repo
can regenerate it themselves by running this script again.

Source: IBGE's "Estimativas de População" (SIDRA aggregate 6579), via the
public Servico de Dados endpoint — no authentication required.
"""

import csv
import json
import os
import urllib.parse
import urllib.request

IBGE_API = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/{year}"
    "/variaveis/9324?localidades=N3[all]"
)
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "populacao_uf.csv")
HEADERS = {"User-Agent": "Mozilla/5.0"}
YEAR = 2025

# IBGE's API returns full state names; the rest of this project keys everything
# by the two-letter UF abbreviation (as used in the SADIPEM/transferências CSVs).
SIGLA_BY_NAME = {
    "Rondônia": "RO", "Acre": "AC", "Amazonas": "AM", "Roraima": "RR",
    "Pará": "PA", "Amapá": "AP", "Tocantins": "TO", "Maranhão": "MA",
    "Piauí": "PI", "Ceará": "CE", "Rio Grande do Norte": "RN", "Paraíba": "PB",
    "Pernambuco": "PE", "Alagoas": "AL", "Sergipe": "SE", "Bahia": "BA",
    "Minas Gerais": "MG", "Espírito Santo": "ES", "Rio de Janeiro": "RJ",
    "São Paulo": "SP", "Paraná": "PR", "Santa Catarina": "SC",
    "Rio Grande do Sul": "RS", "Mato Grosso do Sul": "MS", "Mato Grosso": "MT",
    "Goiás": "GO", "Distrito Federal": "DF",
}


def fetch_population(year):
    """Query IBGE for that year's population estimate per state, keyed by UF."""
    url = IBGE_API.format(year=year)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)

    by_uf = {}
    for series in data[0]["resultados"][0]["series"]:
        name = series["localidade"]["nome"]
        population = int(series["serie"][str(year)])
        by_uf[SIGLA_BY_NAME[name]] = population
    return by_uf


def main():
    population = fetch_population(YEAR)
    print(f"Fetched population estimates for {len(population)} states ({YEAR}).")

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["UF", f"populacao_{YEAR}"])
        for uf, count in sorted(population.items()):
            writer.writerow([uf, count])

    print(f"Saved to {os.path.abspath(OUTPUT_PATH)}")


if __name__ == "__main__":
    main()
