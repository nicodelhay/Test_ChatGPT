from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time

app = Flask(__name__)

class CompanyDataExtractor:
    def __init__(self, url):
        self.url = url

    def get_company_details(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}
        labels = soup.find_all('label')
        for label in labels:
            key = label.text.strip()
            value = label.find_next_sibling('div').text.strip()
            details[key] = value
        return details

    def get_data(self):
        next_page = True
        data = []
        
        while next_page:
            response = requests.get(self.url)
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            for row in rows:
                details = row.find_all('td')
                if len(details) > 0:
                    company_name = details[0].text.strip()
                    company_link = details[0].find('a').get('href') if details[0].find('a') else None
                    full_company_link = "https://manage.stepmarket.org/show_accepted_label_details2.php?" + company_link.split('?')[-1] if company_link else None
                    if full_company_link:
                        company_details = self.get_company_details(full_company_link)
                    else:
                        company_details = {}
                    row_data = {
                        "Company Name": company_name,
                        "Company Link": company_link,
                        "Full Company Link": full_company_link,
                        "Programme Type": details[1].text.strip(),
                        "Start Date": details[2].text.strip(),
                        "End Date": details[3].text.strip(),
                        "ID": details[4].text.strip(),
                        **company_details
                    }
                    data.append(row_data)
            
            next_page_elem = soup.find('a', text='Next')
            if next_page_elem:
                self.url = next_page_elem.get('href')
            else:
                next_page = False
                
            time.sleep(1)
            
        df = pd.DataFrame(data)
        df['Last programme update'] = pd.to_datetime(df.get('Last programme update'), errors='coerce')
        df['Remaining Days'] = ((df['Last programme update'] + timedelta(days=3*365+90)) - datetime.now()).dt.days
        df['Programme ceiling Currency'] = df['Programme ceiling'].str[-3:]
        df['Programme ceiling'] = pd.to_numeric(df['Programme ceiling'].str[:-4].str.replace(' ', ''), errors='coerce') / 1000000000

        # Réorganisez les colonnes selon l'ordre souhaité
        desired_columns = [
            "issuer", "Remaining Days", "Last programme update", "Programme Type", 
            "Start Date", "info memo doc date", "prog guarantee", "Credit rating level", 
            "Programme ceiling", "Programme ceiling Currency", "IPA/PA", "dealer", "Company Name", "Company Link", "Full Company Link", "End Date", "ID", "type code", "documents"
        ]
        
        # Réordonnez les colonnes du DataFrame
        df = df[desired_columns]
        
        # Triez le DataFrame par 'Remaining Days' en ordre croissant
        df.sort_values(by="Remaining Days", inplace=True)
        
        return df


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    print("Traitement de la demande en cours...")  # Log dans la console du serveur
    extractor = CompanyDataExtractor("https://manage.stepmarket.org/step_directory_2.php")
    df = extractor.get_data()
    print("Traitement terminé.")  # Log dans la console du serveur
    return df.to_html(classes='table table-hover table-condensed table-striped', escape=False)

@app.route('/export_excel', methods=['POST'])
def export_excel():
    # ... Générez le DataFrame ...
    excel_file = 'data.xlsx'
    df.to_excel(excel_file, index=False)
    return send_file(excel_file, as_attachment=True)

@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    # ... Générez le PDF avec un tableau et un graphique ...
    pdf_file = 'report.pdf'
    # Utilisez une bibliothèque comme ReportLab ou WeasyPrint pour générer le PDF
    # ...
    return send_file(pdf_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
