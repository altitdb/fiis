import pandas as pd
import requests
import datetime
import logging
from logging import config
import os.path
from babel.numbers import format_currency


LIQUIDEZ_DIARIA = 'liquidezmediadiaria'
P_VP = 'pvp'
ULTIMO_DIVIDENDO = 'dividendo'
PRECO_ATUAL = 'valor'
RENTABILIDADE_ACUMULADA = 'rentabilidade'
DV_12M_ACUMULADO = 'soma_yield_12m'
P_VPA = 'p_vpa'
QUANTIDADE_ATIVOS = 'ativos'
SETOR = 'setor'
FUNDOS = 'ticker'
NUM_COTISTAS = 'numero_cotista'
DIVIDEND_YIELD = 'yeld'

config.fileConfig('log.conf')


def download_ranking():
    url = "https://www.fundsexplorer.com.br/wp-admin/admin-ajax.php"

    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": "https://www.fundsexplorer.com.br",
        "referer": "https://www.fundsexplorer.com.br/ranking",
        "x-csrf-token": "a31dc7ac8b",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    }

    data = {
        "action": "funds-get-ranking"
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        json_data = response.json()
        df = pd.DataFrame(json_data['data'])
        return df
    except Exception as e:
        print(f"Erro ao processar dados: {e}")
        return None


def format_money(value):
    return format_currency(value, 'BRL', locale='pt_BR')


def format_without_symbol(value):
    return "{:,.2f}".format(value)


def format_percent(value):
    return "{:,.2f}%".format(value)


def process_ranking():
    df = download_ranking()
    df.info()

    df.pop('post_id')
    df.pop('media_yield_3m')
    df.pop('soma_yield_3m')
    df.pop('media_yield_6m')
    df.pop('soma_yield_6m')
    df.pop('media_yield_12m')
    df.pop('variacao_cotacao_mes')
    df.pop('rentabilidade_mes')
    df.pop('cotacao_fechamento')
    df.pop('soma_yield_ano_corrente')
    df.pop('ano')
    df.pop('vpa_yield')
    df.pop('vpa')
    df.pop('vpa_change')
    df.pop('pl')
    df.pop('vpa_rent')
    df.pop('vpa_rent_m')
    df.pop('yield_vpa_3m_sum')
    df.pop('yield_vpa_3m')
    df.pop('yield_vpa_6m_sum')
    df.pop('yield_vpa_6m')
    df.pop('yield_vpa_12m_sum')
    df.pop('yield_vpa_12m')
    df.pop('setor_slug')
    df.pop('patrimonio')
    df.pop('post_title')
    df.pop('volatility')
    df.pop('tx_gestao')
    df.pop('tx_admin')
    df.pop('tx_performance')
    df.info()

    logging.info('Normalizing numbers')
    df[QUANTIDADE_ATIVOS] = pd.to_numeric(df[QUANTIDADE_ATIVOS]).fillna(0).astype(int)
    df[DV_12M_ACUMULADO] = pd.to_numeric(df[DV_12M_ACUMULADO]).fillna(0.0).astype(float)
    df[RENTABILIDADE_ACUMULADA] = pd.to_numeric(df[RENTABILIDADE_ACUMULADA]).fillna(0.0).astype(float)
    df[NUM_COTISTAS] = pd.to_numeric(df[NUM_COTISTAS]).fillna(0).astype(int)
    df[LIQUIDEZ_DIARIA] = pd.to_numeric(df[LIQUIDEZ_DIARIA]).astype(float)
    df[PRECO_ATUAL] = pd.to_numeric(df[PRECO_ATUAL]).astype(float)
    df[ULTIMO_DIVIDENDO] = pd.to_numeric(df[ULTIMO_DIVIDENDO]).astype(float)
    df[P_VP] = pd.to_numeric(df[P_VP]).astype(float)
    df[DIVIDEND_YIELD] = pd.to_numeric(df[DIVIDEND_YIELD]).astype(float)
    # df['Vacância Financeira'] = df['Vacância Financeira'].apply(format_type)
    # df['Vacância Física'] = df['Vacância Física'].apply(format_type)
    df.info()

    df.to_csv('archive/ranking.csv')

    logging.info("Initial funds size %s", len(df))

    logging.info("Excluding funds without diversity")
    df = df.loc[df[QUANTIDADE_ATIVOS] > 2]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with P/VPA")
    df = df.loc[(df[P_VPA] > 0.74) & (df[P_VPA] < 1.26)]
    logging.info("Funds size %s", len(df))

    # logging.info("Excluding funds with Vacância Financeira")
    # df = df.loc[df['Vacância Financeira'] < 16]
    # logging.info("Funds size %s", len(df))

    # logging.info("Excluding funds with Vacância Física")
    # df = df.loc[df['Vacância Física'] < 16]
    # logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with DY Acumulado")
    df = df.loc[df[DV_12M_ACUMULADO] > 10]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with Rentabilidade Acumulada")
    df = df.loc[df[RENTABILIDADE_ACUMULADA] > -10]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with Setor Indefinido")
    df = df.loc[df[SETOR] != 'Indefinido']
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds ARCT11")
    df = df.loc[~df[FUNDOS].isin(['ARCT11'])]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with Num Cotistas less than 1000")
    df = df.loc[df[NUM_COTISTAS] > 10000]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with Liquidez Diaria R% less than 1000")
    df = df.loc[df[LIQUIDEZ_DIARIA] > 1000000]
    logging.info("Funds size %s", len(df))

    logging.info("Sorting ranking")
    df = df.sort_values([DV_12M_ACUMULADO], ascending=[False])

    logging.info("Selecting Top 15")
    df = df.head(15)

    price = df[PRECO_ATUAL].sum()
    dividend = df[ULTIMO_DIVIDENDO].sum()
    percent = (dividend * 100) / price

    logging.info('Formatting results')
    df[PRECO_ATUAL] = df[PRECO_ATUAL].apply(format_money)
    df[LIQUIDEZ_DIARIA] = df[LIQUIDEZ_DIARIA].apply(format_money)
    df[P_VP] = df[P_VP].apply(format_without_symbol)
    df[ULTIMO_DIVIDENDO] = df[ULTIMO_DIVIDENDO].apply(format_money)
    df[DV_12M_ACUMULADO] = df[DV_12M_ACUMULADO].apply(format_percent)
    df[RENTABILIDADE_ACUMULADA] = df[RENTABILIDADE_ACUMULADA].apply(format_percent)
    df[P_VPA] = df[P_VPA].apply(format_without_symbol)
    df[DIVIDEND_YIELD] = df[DIVIDEND_YIELD].apply(format_percent)
    # df['Vacância Financeira'] = df['Vacância Financeira'].apply(format_percent)
    # df['Vacância Física'] = df['Vacância Física'].apply(format_percent)

    df.info()

    df = df.rename(columns={
        FUNDOS: 'Fundos',
        SETOR: 'Setor',
        PRECO_ATUAL: 'Preço Atual (R$)',
        LIQUIDEZ_DIARIA: 'Liquidez Diária (R$)',
        P_VP: 'P/VP',
        P_VPA: 'P/VPA',
        ULTIMO_DIVIDENDO: 'Último Dividendo',
        DV_12M_ACUMULADO: 'DY (12M) Acumulado',
        RENTABILIDADE_ACUMULADA: 'Rentab. Acumulada',
        QUANTIDADE_ATIVOS: 'Quant. Ativos',
        NUM_COTISTAS: 'Num. Cotistas',
        DIVIDEND_YIELD: 'Dividend Yield'
    })

    write_header_in_file(df.columns)
    write_result_in_file(df)

    investiment_total = f'Total de Investimento {format_money(price)}'
    dividend_total = f'Total de Dividendos {format_money(dividend)}'
    gain_month = f'Percentual de Ganhos por Mês {format_percent(percent)}'
    gain_year = f'Percentual de Ganhos por Ano {format_percent(percent * 12)}'

    logging.info(investiment_total)
    logging.info(dividend_total)
    logging.info(gain_month)
    logging.info(gain_year)

    write_footer_in_file(investiment_total, dividend_total, gain_month, gain_year)


def get_file():
    return f'{os.path.dirname(__file__)}/README.md'


def write_header_in_file(titles):
    file = get_file()
    with open(file, 'w') as writer:
        writer.write('# FIIS - Top 15\n')
        writer.write(f'>IMPORTANTE: Este Top 15 não é uma recomendação de investimentos.\n\n')
        header = '|'
        above_header = '|'
        for title in titles:
            header += title + '|'
            above_header += ' :---: |'
        header += '\n'
        above_header += '\n'
        writer.write(header)
        writer.write(above_header)


def write_result_in_file(results):
    for index, values in results.iterrows():
        line = '|'
        for value in values:
            line += str(value) + '|'
        line += '\n'
        file = get_file()
        with open(file, 'a') as a_writer:
            a_writer.write(line)


def write_footer_in_file(investiment_total, dividend_total, gain_month, gain_year):
    file = get_file()
    with open(file, 'a') as a_writer:
        a_writer.write('# Estatísticas\n')
        a_writer.write(f'**{investiment_total}**\n\n')
        a_writer.write(f'**{dividend_total}**\n\n')
        a_writer.write(f'**{gain_month}**\n\n')
        a_writer.write(f'**{gain_year}**\n\n')
        a_writer.write('\n')
        today = datetime.datetime.today()
        a_writer.write(f'>Last updated at {today.ctime()}\n')


if __name__ == "__main__":
    process_ranking()
