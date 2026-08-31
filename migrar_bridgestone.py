# -*- coding: utf-8 -*-
"""
migrar_bridgestone.py — migra bs_contingencia_snapshot/bs_pagamentos (schema
fixo, só Bridgestone) pro schema genérico multi-cliente (rel_clientes /
rel_config_cliente / rel_processos_snapshot / rel_pagamentos_snapshot).

Não apaga as tabelas antigas. Idempotente: pode rodar de novo (usa upsert
por on_conflict, e o cliente/config são get-or-create por slug).

Uso:
    python migrar_bridgestone.py
"""
import sys
from datetime import date, datetime

import requests

sys.stdout.reconfigure(encoding="utf-8")

SUPABASE_URL = "https://rpibvjcnrseuugpkfmdj.supabase.co"
SUPABASE_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJwaWJ2amNucnNldXVncGtmbWRqIiwi"
                "cm9sZSI6ImFub24iLCJpYXQiOjE3ODE1NTc3MTcsImV4cCI6MjA5NzEzMzcxN30.ecihol8JESMH7cgFSvWKIzp-OwoPRFqdK3aCDwpCeg8")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

# Colunas fixas do schema antigo que NÃO fazem parte de "dados" (viram
# colunas/chaves próprias no schema novo).
CAMPOS_FORA_DE_DADOS_PROC = {"id", "mes_referencia", "processo", "criado_em"}
CAMPOS_FORA_DE_DADOS_PAG = {"id", "mes_referencia", "processo", "criado_em"}

CONFIG_BRIDGESTONE = {
    "colunas_processos": [
        {"origem": "processo", "label": "Processo", "chave": True},
        {"origem": "reclamante", "label": "Reclamante"},
        {"origem": "escritorio", "label": "Escritório"},
        {"origem": "status", "label": "Status"},
        {"origem": "current_phase", "label": "Fase Atual"},
        {"origem": "previous_phase", "label": "Fase Anterior"},
        {"origem": "objeto", "label": "Objeto"},
        {"origem": "root_cause_1", "label": "Causa Raiz 1"},
        {"origem": "root_cause_2", "label": "Causa Raiz 2"},
        {"origem": "root_cause_3", "label": "Causa Raiz 3"},
        {"origem": "adjustment_tipo", "label": "Tipo de Movimento"},
        {"origem": "historical_probable", "label": "Histórico (Original)", "tipo": "numero"},
        {"origem": "monetary_adjustment_probable", "label": "Correção Monetária (eLaw)", "tipo": "numero"},
        {"origem": "interest_probable", "label": "Juros (eLaw)", "tipo": "numero"},
        {"origem": "total_probable", "label": "Total Provável", "tipo": "numero"},
        {"origem": "total_possible", "label": "Total Possível", "tipo": "numero"},
        {"origem": "total_remote", "label": "Total Remoto", "tipo": "numero"},
        {"origem": "accrual", "label": "Accrual", "tipo": "numero"},
        {"origem": "difference_accrual", "label": "Δ Accrual", "tipo": "numero"},
        {"origem": "difference_historico", "label": "Δ Histórico", "tipo": "numero"},
    ],
    "colunas_pagamentos": [
        {"origem": "processo", "label": "Processo", "chave": True},
        {"origem": "reclamante", "label": "Reclamante"},
        {"origem": "garantia_execucao", "label": "Garantia da Execução", "tipo": "numero"},
        {"origem": "acordo_total", "label": "Acordo Total", "tipo": "numero"},
        {"origem": "pagamento_execucao_total", "label": "Pagamento da Execução", "tipo": "numero"},
        {"origem": "inss_total", "label": "INSS", "tipo": "numero"},
        {"origem": "irrf", "label": "IRRF", "tipo": "numero"},
        {"origem": "honorarios_periciais", "label": "Honorários Periciais", "tipo": "numero"},
        {"origem": "deposito_recursal", "label": "Depósito Recursal", "tipo": "numero"},
        {"origem": "valor_pago_mes", "label": "Pago no Mês", "tipo": "numero"},
        {"origem": "valor_garantia_mes", "label": "Garantia no Mês", "tipo": "numero"},
        {"origem": "provisao_baixada", "label": "Provisão Baixada"},
        {"origem": "responsavel", "label": "Responsável"},
        {"origem": "observacoes", "label": "Observações"},
    ],
    # Bridgestone não tem hoje um campo de status "Encerrado" confiável no
    # export — detecta por comparação com o mês anterior (quem some da
    # planilha vira "encerrado" no mês em que sumiu).
    "encerrado": {"fonte": "comparacao_mes_anterior"},
    "campo_base_correcao": "accrual",
    # Seções opcionais — só existem/renderizam se o cliente tiver os campos
    # necessários. Bridgestone tem todos, mantendo paridade com a versão antiga.
    "grafico1": {"campo": "current_phase", "valor": "accrual", "label": "Carteira por Fase"},
    "grafico2": {"campo": "objeto", "valor": "total_probable", "label": "Carteira por Objeto"},
    "ponte": {
        "campo_tipo": "adjustment_tipo",
        "campo_delta1": {"origem": "difference_accrual", "label": "Δ Accrual"},
        "campo_delta2": {"origem": "difference_historico", "label": "Δ Histórico"},
    },
    "transicao": {"campo_de": "previous_phase", "campo_para": "current_phase"},
    "pagamentos_campo_pago": "valor_pago_mes",
    "pagamentos_campo_garantia": "valor_garantia_mes",
}


def get_paginado(tabela, params=None):
    todos = []
    offset = 0
    tamanho = 1000
    params = dict(params or {})
    while True:
        params["offset"] = offset
        params["limit"] = tamanho
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{tabela}", headers=HEADERS, params=params, timeout=60)
        r.raise_for_status()
        pagina = r.json()
        todos.extend(pagina)
        if len(pagina) < tamanho:
            break
        offset += tamanho
    return todos


def upsert_lote(tabela, registros, on_conflict, lote=300):
    for i in range(0, len(registros), lote):
        chunk = registros[i:i + lote]
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{tabela}?on_conflict={on_conflict}",
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
            json=chunk, timeout=60,
        )
        if not r.ok:
            print(f"[ERRO] {tabela} lote {i}-{i+len(chunk)}: {r.status_code} {r.text[:500]}")
            r.raise_for_status()
        print(f"  {tabela}: upsert {i + len(chunk)}/{len(registros)}")


def get_or_create_cliente(nome, slug):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/rel_clientes", headers=HEADERS,
                      params={"slug": f"eq.{slug}", "select": "id"}, timeout=30)
    r.raise_for_status()
    existentes = r.json()
    if existentes:
        return existentes[0]["id"]
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rel_clientes", headers={**HEADERS, "Prefer": "return=representation"},
                       json={"nome": nome, "slug": slug}, timeout=30)
    r.raise_for_status()
    return r.json()[0]["id"]


def salvar_config(cliente_id, config):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rel_config_cliente",
                       headers={**HEADERS, "Prefer": "return=representation"},
                       json={"cliente_id": cliente_id, "config": config}, timeout=30)
    r.raise_for_status()
    print(f"Config gravada (id={r.json()[0]['id']}).")


def para_dados(row, fora):
    return {k: v for k, v in row.items() if k not in fora and k != "cliente_id"}


def calcular_status(linhas_por_mes):
    """linhas_por_mes: dict mes_referencia (str) -> {processo: dados}, em ordem
    cronológica. Retorna lista de (mes, processo, dados, status), incluindo
    linhas sintéticas de 'encerrado' carregadas do mês anterior pros
    processos que sumiram da planilha."""
    meses = sorted(linhas_por_mes.keys())
    saida = []
    processos_mes_anterior = {}
    for mes in meses:
        atuais = linhas_por_mes[mes]
        for processo, dados in atuais.items():
            status = "novo" if processo not in processos_mes_anterior else "ativo"
            saida.append((mes, processo, dados, status))
        for processo, dados_ant in processos_mes_anterior.items():
            if processo not in atuais:
                saida.append((mes, processo, dados_ant, "encerrado"))
        # base pro próximo mês: quem está ativo/novo neste mês (não carrega
        # os "encerrado" sintéticos adiante, senão nunca some de vez)
        processos_mes_anterior = dict(atuais)
    return saida


def main():
    print("Lendo bs_contingencia_snapshot...")
    snap = get_paginado("bs_contingencia_snapshot")
    print(f"  {len(snap)} linhas.")
    print("Lendo bs_pagamentos...")
    pag = get_paginado("bs_pagamentos")
    print(f"  {len(pag)} linhas.")

    cliente_id = get_or_create_cliente("Bridgestone", "bridgestone")
    print(f"Cliente Bridgestone: id={cliente_id}")
    salvar_config(cliente_id, CONFIG_BRIDGESTONE)

    # ── Processos: agrupa por mês, calcula novo/ativo/encerrado ──
    por_mes = {}
    for row in snap:
        mes = row["mes_referencia"]
        processo = row["processo"]
        dados = para_dados(row, CAMPOS_FORA_DE_DADOS_PROC)
        por_mes.setdefault(mes, {})[processo] = dados

    calculado = calcular_status(por_mes)
    registros_proc = [{
        "cliente_id": cliente_id, "mes_referencia": mes, "processo": processo,
        "dados": dados, "status_calculado": status,
    } for mes, processo, dados, status in calculado]
    print(f"Processos a migrar (com sintéticos de encerrado): {len(registros_proc)}")
    upsert_lote("rel_processos_snapshot", registros_proc, "cliente_id,mes_referencia,processo")

    # ── Pagamentos: cópia direta, sem cálculo de status ──
    registros_pag = [{
        "cliente_id": cliente_id, "mes_referencia": row["mes_referencia"], "processo": row["processo"],
        "dados": para_dados(row, CAMPOS_FORA_DE_DADOS_PAG),
    } for row in pag]
    print(f"Pagamentos a migrar: {len(registros_pag)}")
    upsert_lote("rel_pagamentos_snapshot", registros_pag, "cliente_id,mes_referencia,processo")

    print("Concluído.")


if __name__ == "__main__":
    main()
