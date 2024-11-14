import requests
from bs4 import BeautifulSoup


class Currency:
    YUAN_RUB = 'https://www.google.com/search?q=%D1%8E%D0%B0%D0%BD%D1%8C+%D0%BA%D1%83%D1%80%D1%81&oq=%D1%8E%D0%B0%D0%BD%D1%8C+&gs_lcrp=EgZjaHJvbWUqDwgBEAAYQxixAxiABBiKBTIGCAAQRRg5Mg8IARAAGEMYsQMYgAQYigUyDAgCEAAYQxiABBiKBTIPCAMQABhDGLEDGIAEGIoFMgwIBBAAGEMYgAQYigUyEggFEAAYQxiDARixAxiABBiKBTIPCAYQABhDGLEDGIAEGIoFMgwIBxAAGEMYgAQYigUyDwgIEAAYQxixAxiABBiKBTIMCAkQABhDGIAEGIoF0gEIMzMwNWowajeoAgCwAgA&sourceid=chrome&ie=UTF-8'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'}

    current_converted_price = 0
    difference = 5

    def __init__(self):
        self.current_converted_price = float(self.get_currency_price().replace(",", "."))

    def get_currency_price(self):
        full_page = requests.get(self.YUAN_RUB, headers=self.headers)
        soup = BeautifulSoup(full_page.content, 'html.parser')

        convert = soup.findAll("span", {"class": "DFlfde", "class": "SwHCTb", "data-precision": 2})
        return convert[0].text
