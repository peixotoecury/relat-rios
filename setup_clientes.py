# -*- coding: utf-8 -*-
"""
setup_clientes.py — cadastra os clientes/modelos do piloto a partir da
inspeção real dos arquivos que a usuária mandou (colunas confirmadas nos
próprios .xlsx, não adivinhadas). Roda DEPOIS de create_tables.sql.

Cada "modelo" vira um cliente próprio em rel_clientes (Bridgestone e
Embraer têm 2 modelos cada — tratados como 2 entradas distintas por
enquanto, já que o schema atual é 1 config por cliente).

Uso:
    python setup_clientes.py
"""
import sys
import requests

sys.stdout.reconfigure(encoding="utf-8")

SUPABASE_URL = "https://rpibvjcnrseuugpkfmdj.supabase.co"
SUPABASE_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJwaWJ2amNucnNldXVncGtmbWRqIiwi"
                "cm9sZSI6ImFub24iLCJpYXQiOjE3ODE1NTc3MTcsImV4cCI6MjA5NzEzMzcxN30.ecihol8JESMH7cgFSvWKIzp-OwoPRFqdK3aCDwpCeg8")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}


def col(origem, label, tipo="texto", chave=False):
    d = {"origem": origem, "label": label}
    if tipo == "numero":
        d["tipo"] = "numero"
    if chave:
        d["chave"] = True
    return d


CLIENTES = [
    {
        "nome": "Bridgestone - Contingência",
        "slug": "bridgestone-contingencia",
        # Confirmado ao vivo em "Labor - August 2026 - Vfinal.xlsx", aba
        # "Ago.2026" (nome da aba muda todo mês, cabeçalho na linha 3).
        "config": {
            "colunas_processos": [
                col("Process", "Processo", chave=True),
                col("Plaintiff", "Reclamante"),
                col("Escritório", "Escritório"),
                col("Status", "Status"),
                col("Current Phase", "Fase Atual"),
                col("Previous Phase", "Fase Anterior"),
                col("Root Cause 1", "Causa Raiz 1"),
                col("Root Cause 2", "Causa Raiz 2"),
                col("Root Cause 3", "Causa Raiz 3"),
                col("Adjustment", "Tipo de Movimento"),
                col("Historical Amount - Probable", "Histórico (Provável)", "numero"),
                col("Monetary Adjustment - Probable", "Correção Monetária", "numero"),
                col("Interest - Probable", "Juros", "numero"),
                col("Total Amount - Probable", "Total Provável", "numero"),
                col("Total Amount - Possible", "Total Possível", "numero"),
                col("Total Amount - Remote", "Total Remoto", "numero"),
                col("Accrual", "Accrual", "numero"),
                col("Difference Amount (Accrual)", "Δ Accrual", "numero"),
                col("Diferenças histórico - Mês anterior x Mês atual", "Δ Histórico", "numero"),
            ],
            "colunas_pagamentos": [],
            "encerrado": {"fonte": "comparacao_mes_anterior"},
            "campo_base_correcao": "Accrual",
            "grafico1": {"campo": "Current Phase", "valor": "Accrual", "label": "Carteira por Fase"},
            "grafico2": {"campo": "Root Cause 1", "valor": "Total Amount - Probable", "label": "Carteira por Causa Raiz"},
            "ponte": {
                "campo_tipo": "Adjustment",
                "campo_delta1": {"origem": "Difference Amount (Accrual)", "label": "Δ Accrual"},
                "campo_delta2": {"origem": "Diferenças histórico - Mês anterior x Mês atual", "label": "Δ Histórico"},
            },
            "transicao": {"campo_de": "Previous Phase", "campo_para": "Current Phase"},
            "movimentacoes_campos": ["Current Phase", "Total Amount - Probable"],
        },
    },
    {
        "nome": "Bridgestone - Forecast",
        "slug": "bridgestone-forecast",
        # Confirmado em "Forecast - Jul.2026 - Vfinal i.xlsx", aba "Jun.2026"
        # — cabeçalho na linha 5 (não 3, esse arquivo tem mais linhas de topo).
        "config": {
            "colunas_processos": [
                col("Process", "Processo", chave=True),
                col("Escritório", "Escritório"),
                col("Status", "Status"),
                col("Type of Case", "Tipo de Ação"),
                col("City", "Cidade"),
                col("Forecast", "Forecast"),
            ],
            "colunas_pagamentos": [],
            "encerrado": {"fonte": "comparacao_mes_anterior"},
        },
    },
    {
        "nome": "CBC",
        "slug": "cbc",
        # Confirmado em "CBC - Relatório Contingência Trabalhista - Julho
        # 2026 (1).xlsx", aba "Base P&C - <Mês>. 2026 - CBC" (cabeçalho
        # linha 3 — reparar no espaço depois do mês, ex: "Jul. 2026").
        "config": {
            "colunas_processos": [
                col("Processo", "Processo", chave=True),
                col("Código P&C", "Código P&C"),
                col("Reclamante", "Reclamante"),
                col("Reclamada", "Reclamada"),
                col("Status", "Status"),
                col("Tipo de Ação", "Tipo de Ação"),
                col("Objeto", "Objeto"),
                col("Comarca", "Comarca"),
                col("UF", "UF"),
                col("Data da Distribuição", "Data da Distribuição"),
                col("Fase Mês Anterior", "Fase Mês Anterior"),
                col("Fase Mês Atual", "Fase Mês Atual"),
                col("Risco Mês Anterior", "Risco Mês Anterior"),
                col("Risco Mês Atual", "Risco Mês Atual"),
                col("Remoto", "Remoto", "numero"),
                col("Possível", "Possível", "numero"),
                col("Provável", "Provável", "numero"),
                col("Total - Mês atual", "Total do Mês", "numero"),
                col("Data do Encerramento", "Data do Encerramento"),
                col("Motivo do Encerramento", "Motivo do Encerramento"),
            ],
            "colunas_pagamentos": [],
            # Confirmado ao vivo: valores reais da coluna Status são
            # "Ativo", "Ativo - Novo", "Encerrado - Mês".
            "encerrado": {"fonte": "campo_status", "campo": "Status",
                          "valores_encerrado": ["Encerrado - Mês", "Encerrado"],
                          "valores_novo": ["Ativo - Novo"]},
            "campo_base_correcao": "Provável",
            "grafico1": {"campo": "Fase Mês Atual", "valor": "Provável", "label": "Carteira por Fase"},
            "grafico2": {"campo": "Risco Mês Atual", "valor": "Total do Mês", "label": "Carteira por Risco"},
            "transicao": {"campo_de": "Fase Mês Anterior", "campo_para": "Fase Mês Atual"},
            "movimentacoes_campos": ["Fase Mês Atual", "Risco Mês Atual", "Provável"],
        },
    },
    {
        "nome": "Embraer - Reintegrados",
        "slug": "embraer-reintegrados",
        # Confirmado em "Planilha de Reintegrados e Estratégicos...xlsx",
        # aba "Reintegrados" — cabeçalho na linha 2 (não 3!).
        "config": {
            "colunas_processos": [
                col("Processso nº", "Processo", chave=True),
                col("Nome do reclamante", "Reclamante"),
                col("Comarca", "Comarca"),
                col("Advogado reclamante", "Advogado"),
                col("Diretoria", "Diretoria"),
                col("Gerência", "Gerência"),
                col("Status", "Status"),
                col("Fase processual", "Fase Processual"),
                col("Risco do elaw (possível, provável, remoto)", "Risco (eLaw)"),
                col("Valor do risco [ELAW]", "Valor do Risco", "numero"),
                col("Valor da provisão [ELAW]", "Valor da Provisão", "numero"),
                col("Última decisão (reintegração deferida ou indeferida)", "Última Decisão"),
                col("Probabilidade de reintegração", "Probabilidade de Reintegração"),
            ],
            "colunas_pagamentos": [],
            "encerrado": {"fonte": "comparacao_mes_anterior"},
            "campo_base_correcao": "Valor da provisão [ELAW]",
            "grafico1": {"campo": "Fase processual", "valor": "Valor do risco [ELAW]", "label": "Carteira por Fase"},
            "grafico2": {"campo": "Risco do elaw (possível, provável, remoto)", "valor": "Valor da provisão [ELAW]", "label": "Carteira por Risco"},
            "movimentacoes_campos": ["Fase processual", "Risco do elaw (possível, provável, remoto)", "Valor da provisão [ELAW]"],
        },
    },
    {
        "nome": "Embraer - Estratégicos",
        "slug": "embraer-estrategicos",
        # Confirmado na aba "Estratégicos " — cabeçalho na linha 1 (dado
        # começa direto na linha 2, diferente da aba Reintegrados).
        "config": {
            "colunas_processos": [
                col("Processso nº", "Processo", chave=True),
                col("Nome do reclamante", "Reclamante"),
                col("Comarca", "Comarca"),
                col("Diretoria", "Diretoria"),
                col("Gerência", "Gerência"),
                col("Grupo de Objetos", "Grupo de Objetos"),
                col("Objetos", "Objetos"),
                col("Status", "Status"),
                col("Fase processual", "Fase Processual"),
                col("Risco (possível, provável, remoto)", "Risco (eLaw)"),
                col("Valor do risco [ELAW]", "Valor do Risco", "numero"),
                col("Valor da provisão [ELAW]", "Valor da Provisão", "numero"),
            ],
            "colunas_pagamentos": [],
            "encerrado": {"fonte": "comparacao_mes_anterior"},
            "campo_base_correcao": "Valor da provisão [ELAW]",
            "grafico1": {"campo": "Fase processual", "valor": "Valor do risco [ELAW]", "label": "Carteira por Fase"},
            "grafico2": {"campo": "Grupo de Objetos", "valor": "Valor da provisão [ELAW]", "label": "Carteira por Grupo de Objeto"},
            "movimentacoes_campos": ["Fase processual", "Risco (possível, provável, remoto)", "Valor da provisão [ELAW]"],
        },
    },
    {
        "nome": "Ferrero",
        "slug": "ferrero",
        # Confirmado em "Relatório Contingências Trabalhistas - Ferrero -
        # Agosto.xlsx", aba "Base P&C - Agosto.2026" — cabeçalho linha 3.
        "config": {
            "colunas_processos": [
                col("Processo", "Processo", chave=True),
                col("Código P&C", "Código P&C"),
                col("Status", "Status"),
                col("Reclamante", "Reclamante"),
                col("Reclamada", "Reclamada"),
                col("Área", "Área"),
                col("Diretoria", "Diretoria"),
                col("Comarca", "Comarca"),
                col("UF", "UF"),
                col("Root Cause", "Causa Raiz"),
                col("Data de Encerramento", "Data de Encerramento"),
                col("Tipo de Encerramento", "Tipo de Encerramento"),
                col("Fase Mês Anterior", "Fase Mês Anterior"),
                col("Fase Mês Atual", "Fase Mês Atual"),
                col("Risco Mês Anterior", "Risco Mês Anterior"),
                col("Risco Mês Atual", "Risco Mês Atual"),
                col("Remoto", "Remoto", "numero"),
                col("Possível", "Possível", "numero"),
                col("Provável", "Provável", "numero"),
                col("Total", "Total", "numero"),
            ],
            "colunas_pagamentos": [],
            # Só vi "Novo"/"Em Processo" nos dados de um mês só — não achei
            # o valor exato de "encerrado" no Status pra confirmar com
            # segurança. Usando o fallback universal (comparação com mês
            # anterior) até a usuária confirmar o valor real e trocar pra
            # campo_status na tela de Configurar Cliente.
            "encerrado": {"fonte": "comparacao_mes_anterior"},
            "campo_base_correcao": "Provável",
            "grafico1": {"campo": "Fase Mês Atual", "valor": "Provável", "label": "Carteira por Fase"},
            "grafico2": {"campo": "Risco Mês Atual", "valor": "Total", "label": "Carteira por Risco"},
            "transicao": {"campo_de": "Fase Mês Anterior", "campo_para": "Fase Mês Atual"},
            "movimentacoes_campos": ["Fase Mês Atual", "Risco Mês Atual", "Provável"],
        },
    },
    {
        "nome": "T4F",
        "slug": "t4f",
        # Confirmado em "PC - Relatório de Provisões Trabalhista - T4F -
        # 2Q2026 - VFinal II.xlsx", aba "2Q2026" — cabeçalho linha 3.
        "config": {
            "colunas_processos": [
                col("Nº do Processo", "Processo", chave=True),
                col("Empresa", "Empresa"),
                col("Polo", "Polo"),
                col("Parte Contrária", "Parte Contrária"),
                col("Tipo de Contratação", "Tipo de Contratação"),
                col("Comarca", "Comarca"),
                col("UF", "UF"),
                col("Foro/Tribunal", "Foro/Tribunal"),
                col("Data Distribuição", "Data Distribuição"),
                col("Tipo Ação", "Tipo de Ação"),
                col("Objeto", "Objeto"),
                col("Instância", "Instância"),
                col("Prognóstico 2Q26", "Prognóstico"),
                col("Valor Original da Causa", "Valor Original da Causa", "numero"),
                col("Valor Estimado da Causa", "Valor Estimado da Causa", "numero"),
            ],
            "colunas_pagamentos": [],
            "encerrado": {"fonte": "comparacao_mes_anterior"},
            "campo_base_correcao": "Valor Estimado da Causa",
            "grafico1": {"campo": "Instância", "valor": "Valor Estimado da Causa", "label": "Carteira por Instância"},
            "grafico2": {"campo": "Prognóstico 2Q26", "valor": "Valor Estimado da Causa", "label": "Carteira por Prognóstico"},
        },
    },
]


def get_or_create_cliente(nome, slug):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/rel_clientes", headers=HEADERS,
                      params={"slug": f"eq.{slug}", "select": "id"}, timeout=30)
    r.raise_for_status()
    existentes = r.json()
    if existentes:
        return existentes[0]["id"], False
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rel_clientes", headers={**HEADERS, "Prefer": "return=representation"},
                       json={"nome": nome, "slug": slug}, timeout=30)
    r.raise_for_status()
    return r.json()[0]["id"], True


def main():
    for c in CLIENTES:
        cliente_id, criado = get_or_create_cliente(c["nome"], c["slug"])
        r = requests.post(f"{SUPABASE_URL}/rest/v1/rel_config_cliente",
                           headers={**HEADERS, "Prefer": "return=representation"},
                           json={"cliente_id": cliente_id, "config": c["config"]}, timeout=30)
        r.raise_for_status()
        print(f"{'[novo]' if criado else '[já existia]'} {c['nome']} (id={cliente_id}) — config gravada.")
    print("\nConcluído.")


if __name__ == "__main__":
    main()
