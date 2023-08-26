import pandas as pd
import requests
import datetime
import logging
from logging import config
import os.path
from babel.numbers import format_currency
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

config.fileConfig('log.conf')


def get_filename(filename):
    today = datetime.date.today()
    return f"{os.path.dirname(__file__)}/archive/{today}-{filename}.html"


def verify_if_ranking_exists():
    filename = get_filename('ranking')
    logging.info('Verifing if %s exists', filename)
    file_exists = os.path.exists(filename)
    logging.info('File %s exists %s', filename, file_exists)
    return file_exists


def download_ranking():
    logging.info('Downloading ranking')
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")

    service = Service('/work/fiis/webdriver/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://www.fundsexplorer.com.br/ranking")
    wait = WebDriverWait(driver, 30)

    elements = wait.until(
        EC.presence_of_all_elements_located((By.ID, 'upTo--default-fiis-table'))
    )
    logging.info(f'Elements available {len(elements)}')

    web_content = driver.page_source

    filename = get_filename('ranking')
    f = open(filename, 'wb')
    f.write(web_content.encode())
    f.close


def format_type(value):
    if value != value:
        return 0
    new_value = value.replace('%', '').replace('R', '').replace('$', '').replace('.', '').replace(',', '.')
    return float(new_value)


def format_money(value):
    return format_currency(value, 'BRL', locale='pt_BR')


def format_percent(value):
    return "{:,.2f}%".format(value)


def process_ranking():
    filename = get_filename('ranking')
    df = pd.read_html(filename, encoding='utf-8')[0]
    df.info()
    
    logging.info('Cleaning unused columns')
    df.pop('DY (3M) Acumulado')
    df.pop('DY (6M) Acumulado')
    df.pop('DY (3M) média')
    df.pop('DY (6M) média')
    df.pop('DY Ano')
    df.pop('DY Patrimonial')
    df.pop('Variação Preço')
    df.pop('Rentab. Período')
    df.pop('VPA')
    df.pop('Variação Patrimonial')
    df.pop('Rentab. Patr. Período')
    df.pop('Rentab. Patr. Acumulada')

    df.info()

    logging.info('Normalizing numbers')
    df['Preço Atual (R$)'] = df['Preço Atual (R$)'].apply(format_type)
    df['Liquidez Diária (R$)'] = df['Liquidez Diária (R$)'].apply(format_type)
    df['Último Dividendo'] = df['Último Dividendo'].apply(format_type)
    df['DY (12M) Acumulado'] = df['DY (12M) Acumulado'].apply(format_type)
    df['Rentab. Acumulada'] = df['Rentab. Acumulada'].apply(format_type)
    df['Patrimônio Líquido'] = df['Patrimônio Líquido'].apply(format_type)
    df['Vacância Financeira'] = df['Vacância Financeira'].apply(format_type)
    df['Vacância Física'] = df['Vacância Física'].apply(format_type)

    logging.info("Initial funds size %s", len(df))

    logging.info("Excluding funds without diversity")
    df = df.loc[df['Quant. Ativos'] > 2]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with P/VPA")
    df = df.loc[(df['P/VPA'] > 74) & (df['P/VPA'] < 126)]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with Vacância Financeira")
    df = df.loc[df['Vacância Financeira'] < 16]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with Vacância Física")
    df = df.loc[df['Vacância Física'] < 16]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with DY Acumulado")
    df = df.loc[df['DY (12M) Acumulado'] > 6]
    logging.info("Funds size %s", len(df))

    logging.info("Excluding funds with Rentabilidade Acumulada")
    df = df.loc[df['Rentab. Acumulada'] > -10]
    logging.info("Funds size %s", len(df))

    logging.info("Sorting ranking")
    df = df.sort_values(['DY (12M) Acumulado'], ascending=[False])

    logging.info("Selecting Top 15")
    df = df.head(15)

    price = df['Preço Atual (R$)'].sum()
    dividend = df['Último Dividendo'].sum()
    percent = (dividend * 100) / price

    logging.info('Formatting results')
    df['Preço Atual (R$)'] = df['Preço Atual (R$)'].apply(format_money)
    df['Liquidez Diária (R$)'] = df['Liquidez Diária (R$)'].apply(format_money)
    df['Último Dividendo'] = df['Último Dividendo'].apply(format_money)
    df['DY (12M) Acumulado'] = df['DY (12M) Acumulado'].apply(format_percent)
    df['Rentab. Acumulada'] = df['Rentab. Acumulada'].apply(format_percent)
    df['Patrimônio Líquido'] = df['Patrimônio Líquido'].apply(format_money)
    df['Vacância Financeira'] = df['Vacância Financeira'].apply(format_percent)
    df['Vacância Física'] = df['Vacância Física'].apply(format_percent)

    df.info()

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
    return f'{os.path.dirname(__file__)}/fiis-top15.md'


def write_header_in_file(titles):
    file = get_file()
    with open(file, 'w') as writer:
        writer.write('# FIIS - Top 15\n')
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


def main():
    ranking_exists = verify_if_ranking_exists()
    if not ranking_exists:
        download_ranking()
    process_ranking()


if __name__ == "__main__":
    main()
