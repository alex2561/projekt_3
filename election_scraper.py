"""
projekt_3.py: treti projekt do Engeto Online Python Akademie
author: Alexandr Sytko
email: sytko.alex@gmail.com
"""

import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd

def ziskej_vysledky_z_okrsku(okrsek_url):
    odpoved = requests.get(okrsek_url)
    odpoved.encoding = 'utf-8'
    soup = BeautifulSoup(odpoved.text, 'html.parser')
    tabulky = soup.find_all('table', {'class': 'table'})

    # Tabulka mala
    tabulka_mala = tabulky[0]
    radek_tabulka_mala = ""
    if 'xvyber' in okrsek_url and not 'xmc' in okrsek_url:
        radek_tabulka_mala = tabulka_mala.find_all("tr")[1]
    else:
        radek_tabulka_mala = tabulka_mala.find_all("tr")[2]
    # Ziskani druhe tabulky
    tabulky = tabulky[1:]

    return zpracuj_data_okrsku(radek_tabulka_mala, tabulky, okrsek_url)

def zpracuj_data_okrsku(radek_tabulka_mala, tabulky, okrsek_url):
    radky = []
    print(f"Zpracovavam okrsek {okrsek_url}")
    for tabulka in tabulky:
        nefiltrovane_radky = tabulka.find_all('tr')
        filtrovane_radky = [radek for radek in nefiltrovane_radky if not radek.find('th')]
        for radek in filtrovane_radky:
            radky.append(radek)
    # Extrahovat data z tabulky
    try:
        volici_v_seznamu = int(radek_tabulka_mala.find_all('td')[0].text.strip().replace('\xa0', '').replace(' ', ''))
        vydane_obalky = int(radek_tabulka_mala.find_all('td')[1].text.strip().replace('\xa0', '').replace(' ', ''))
        platne_hlasy = int(radek_tabulka_mala.find_all('td')[4].text.strip().replace('\xa0', '').replace(' ', ''))
    except ValueError:
        print(f"Neocekavany format tabulky v {okrsek_url}")
        return None

    data_stran = {}
    for radek in radky:
        sloupce = radek.find_all('td')
        strana = sloupce[1].text.strip()
        hlasy = 0
        if sloupce[2].text != "-":
            hlasy = int(sloupce[2].text.strip().replace('\xa0', '').replace(' ', ''))
        data_stran[strana] = hlasy

    return {
        'volici v seznamu': volici_v_seznamu,
        'vydane obalky': vydane_obalky,
        'platne hlasy': platne_hlasy,
        **data_stran
    }

def ziskej_vsechny_odkazy_na_okrsky(obec_url):
    odpoved = requests.get(obec_url)
    odpoved.encoding = 'utf-8'
    soup = BeautifulSoup(odpoved.text, 'html.parser')
    odkazy_na_okrsky = [a['href'] for a in soup.find_all('a') if 'ps311' in a['href']]
    return odkazy_na_okrsky

def ziskej_vsechny_odkazy_na_obce(pocatecni_url):
    odpoved = requests.get(pocatecni_url)
    odpoved.encoding = 'utf-8'
    soup = BeautifulSoup(odpoved.text, 'html.parser')
    vsechny_tabulky = soup.find_all('table')
    odkazy_na_obce = []
    for tabulka in vsechny_tabulky:
        nefiltrovane_radky = tabulka.find_all('tr')
        filtrovane_radky = [radek for radek in nefiltrovane_radky if not radek.find('th') and not radek.find('td', {"class": "hidden_td"})]
        for filtrovany_radek in filtrovane_radky:
            odkaz_na_obec = filtrovany_radek.find_all('a')[1]
            if(odkaz_na_obec != None):
                odkazy_na_obce.append(odkaz_na_obec['href'])

    zakladni_url = "https://volby.cz/pls/ps2017nss/"
    plne_odkazy = [zakladni_url + odkaz for odkaz in odkazy_na_obce]
    return plne_odkazy

def ziskej_nazev_kraje(pocatecni_url):
    odpoved = requests.get(pocatecni_url)
    odpoved.encoding = 'utf-8'
    soup = BeautifulSoup(odpoved.text, 'html.parser')
    nazev_kraje = soup.find('h3').text.split(':')[1].strip()
    return nazev_kraje

def zpracuj_odkazy_na_okrsky(odkazy_na_okrsky, obec_url, nazev_kraje, vsechna_data):
    zakladni_url = "https://volby.cz/pls/ps2017nss/"
    for odkaz_na_okrsek in odkazy_na_okrsky:
        okrsek_url = zakladni_url + odkaz_na_okrsek
        print(f"Zpracovavam okrsek {okrsek_url}")
        data_vysledku = ziskej_vysledky_z_okrsku(okrsek_url)
        if data_vysledku:
            kod_obce = obec_url.split('=')[-1]
            html_obec = BeautifulSoup(requests.get(obec_url).text, 'html.parser').find('h3', string=lambda text: 'Obec' in text if text else False)

            nazev_obce = html_obec.text.split(':')[1].strip()
            data_vysledku.update({'kod obce': kod_obce, 'nazev obce': nazev_obce, 'kraj': nazev_kraje})
            vsechna_data.append(data_vysledku)

def zpracuj_vsechny_odkazy_na_obce(vsechny_odkazy_na_obce, nazev_kraje, vsechna_data):
    for obec_url in vsechny_odkazy_na_obce:
        print(f"Zpracovavam obec {obec_url}")
        odkazy_na_okrsky = ziskej_vsechny_odkazy_na_okrsky(obec_url)
        if not odkazy_na_okrsky:
            print(f"Nenalezeny odkazy pro okrsky na adrese: {obec_url}")
            continue
        zpracuj_odkazy_na_okrsky(odkazy_na_okrsky, obec_url, nazev_kraje, vsechna_data)

def uloz_data_do_csv(vsechna_data, vystupni_csv):
    if vsechna_data:
        df = pd.DataFrame(vsechna_data)

        # Seskupeni podle 'nazev obce' a secte vsechny ostatni sloupce
        numericke_sloupce = df.select_dtypes(include='number').columns
        df_seskupeno = df.groupby('nazev obce').sum(numeric_only=True).reset_index()

        # Neciselne sloupce
        nenumericke_sloupce = df.select_dtypes(exclude='number').columns
        df_nenumericke = df[nenumericke_sloupce].drop_duplicates(subset=['nazev obce'])

        # Slouceni - ciselna a neciselna data
        df_konecny = pd.merge(df_seskupeno, df_nenumericke, on='nazev obce')

        df_konecny.to_csv(vystupni_csv, index=False, encoding='utf-8-sig')
        print(f"Data byla uspesne ulozena do {vystupni_csv}")
    else:
        print("Data nejsou k dispozici. Ukoncuji program.")

def zpracuj_vysledky_voleb():
    if len(sys.argv) != 3:
        print("Pouziti: python projekt_3.py <url> <vystupni_csv>")
        sys.exit(1)

    pocatecni_url = sys.argv[1]
    vystupni_csv = sys.argv[2]

    if not pocatecni_url.startswith("https://volby.cz/pls/ps2017nss/ps32"):
        print("Nespravna URL.")
        sys.exit(1)

    vsechny_odkazy_na_obce = ziskej_vsechny_odkazy_na_obce(pocatecni_url)
    if not vsechny_odkazy_na_obce:
        print("Nenalezeny odkazy na obce.")
        sys.exit(1)

    nazev_kraje = ziskej_nazev_kraje(pocatecni_url)

    vsechna_data = []
    zpracuj_vsechny_odkazy_na_obce(vsechny_odkazy_na_obce, nazev_kraje, vsechna_data)
    uloz_data_do_csv(vsechna_data, vystupni_csv)

def main():
    zpracuj_vysledky_voleb()

if __name__ == "__main__":
    main()
