"""
projekt_3.py: třetí projekt do Engeto Online Python Akademie
author: Alexandr Sytko
email: sytko.alex@gmail.com
"""

import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_results_from_okrsek(okrsek_url):
    response = requests.get(okrsek_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table', {'class': 'table'})

    # Tabulka malá
    tabulka_mala = tables[0]
    row_tabulka_mala = tabulka_mala.find_all("tr")[1]
    # Získání druhé tabulky
    tables = tables[1:]

    rows = []

    for table in tables:
        unfiltered_rows = table.find_all('tr')
        filtered_rows = [row for row in unfiltered_rows if not row.find('th')]
        for row in filtered_rows:
            rows.append(row)

    # Extrahovat data z tabulky
    try:
        voliči_v_seznamu = int(row_tabulka_mala.find_all('td')[0].text.strip().replace('\xa0', '').replace(' ', ''))
        vydane_obalky = int(row_tabulka_mala.find_all('td')[1].text.strip().replace('\xa0', '').replace(' ', ''))
        platne_hlasy = int(row_tabulka_mala.find_all('td')[4].text.strip().replace('\xa0', '').replace(' ', ''))
    except ValueError:
        print(f"Unexpected table format at {okrsek_url}")
        return None


    strany_data = {}
    for row in rows:
        cols = row.find_all('td')
        strana = cols[1].text.strip()
        hlasy = int(cols[2].text.strip().replace('\xa0', '').replace(' ', ''))
        strany_data[strana] = hlasy

    return {
        'voliči v seznamu': voliči_v_seznamu,
        'vydané obálky': vydane_obalky,
        'platné hlasy': platne_hlasy,
        **strany_data
    }

def get_all_okrsek_links(obec_url):
    response = requests.get(obec_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    okrsek_links = [a['href'] for a in soup.find_all('a') if 'ps311' in a['href']]
    return okrsek_links

def get_all_obec_links(initial_url):
    response = requests.get(initial_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    obec_links = [a['href'] for a in soup.find_all('a') if 'ps33' in a['href']]
    base_url = "https://volby.cz/pls/ps2017nss/"
    full_links = [base_url + link for link in obec_links]
    return full_links

def get_kraj_nazev(initial_url):
    response = requests.get(initial_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    kraj_nazev = soup.find('h3').text.split(':')[1].strip()
    return kraj_nazev

def main():
    if len(sys.argv) != 3:
        print("Usage: python projekt_3.py <url> <output_csv>")
        sys.exit(1)

    initial_url = sys.argv[1]
    output_csv = sys.argv[2]

    if not initial_url.startswith("https://volby.cz/pls/ps2017nss/ps32"):
        print("Nesprávná URL.")
        sys.exit(1)

    all_obec_links = get_all_obec_links(initial_url)
    if not all_obec_links:
        print("Nenalezeny odkazy na obce.")
        sys.exit(1)

    base_url = "https://volby.cz/pls/ps2017nss/"
    all_data = []

    kraj_nazev = get_kraj_nazev(initial_url)

    for obec_url in all_obec_links:
        print(f"Zpracovávám obec {obec_url}")
        okrsek_links = get_all_okrsek_links(obec_url)
        if not okrsek_links:
            print(f"Nenalezeny odkazy pro okrsky na adrese: {obec_url}")
            continue

        for okrsek_link in okrsek_links:
            okrsek_url = base_url + okrsek_link
            print(f"Zpracovávám okrsek {okrsek_url}")
            result_data = get_results_from_okrsek(okrsek_url)
            if result_data:
                kod_obce = obec_url.split('=')[-1]
                html_obec = BeautifulSoup(requests.get(obec_url).text, 'html.parser').find_all('h3')[2]
                nazev_obce = html_obec.text.split(':')[1].strip()
                result_data.update({'kód obce': kod_obce, 'název obce': nazev_obce, 'kraj': kraj_nazev})
                all_data.append(result_data)

    if all_data:
        df = pd.DataFrame(all_data)

        # Seskupení podle 'název obce' a sečíst všechny ostatní sloupce
        numeric_columns = df.select_dtypes(include='number').columns
        df_grouped = df.groupby('název obce').sum(numeric_only=True).reset_index()

        # Nečiselné sloupce
        non_numeric_columns = df.select_dtypes(exclude='number').columns
        df_non_numeric = df[non_numeric_columns].drop_duplicates(subset=['název obce'])

        # Sloučení - číselná a nečíselná data
        df_final = pd.merge(df_grouped, df_non_numeric, on='název obce')

        df_final.to_csv(output_csv, index=False, encoding='utf-8-sig')  # Použití UTF-8 s BOM pro správné kódování
        print(f"Data byla úspěšně uložena do {output_csv}")
    else:
        print("Data nejsou k dispozici. Ukoncuji program.")

if __name__ == "__main__":
    main()
