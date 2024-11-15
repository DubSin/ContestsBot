import requests
from bs4 import BeautifulSoup


class Currency:
    DOLLAR_RUB = 'https://www.google.com/search?q=%D1%8E%D0%B0%D0%BD%D1%8F+%D0%BA+%D1%80%D1%83%D0%B1%D0%BB%D1%8E&sca_esv=884896eda14e76c3&sxsrf=ADLYWIJdQLJgMSiRugdcijbDfrdVCAHkPw%3A1731687405304&ei=7XM3Z_6eEr-bwPAPyMaUsQE&oq=%D1%8E%D0%B0%D0%BD%D1%8F+&gs_lp=Egxnd3Mtd2l6LXNlcnAiCdGO0LDQvdGPICoCCAAyChAAGIAEGEMYigUyChAAGIAEGEMYigUyBRAAGIAEMgUQABiABDIHEAAYgAQYCjIHEAAYgAQYCjIHEAAYgAQYCjIKEAAYgAQYQxiKBTIFEAAYgAQyChAAGIAEGBQYhwJIpE1Q7i9Y6UdwAXgBkAEAmAF5oAGnBKoBAzEuNLgBAcgBAPgBAZgCBqACyQTCAgcQIxiwAxgnwgIKEAAYsAMY1gQYR8ICDRAAGIAEGLADGEMYigXCAgoQIxiABBgnGIoFwgINEAAYgAQYsQMYFBiHAsICERAuGIAEGLEDGNEDGIMBGMcBwgIIEAAYgAQYsQPCAgsQLhiABBjRAxjHAcICDhAAGIAEGLEDGIMBGIoFwgIPECMYgAQYJxiKBRhGGIICwgINEAAYgAQYsQMYQxiKBcICGRAAGIAEGIoFGEYYggIYlwUYjAUY3QTYAQGYAwCIBgGQBgq6BgYIARABGBOSBwMyLjSgB6sr&sclient=gws-wiz-serp'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'}


    def __init__(self):
        self.current_converted_price = float(self.get_currency_price().replace(",", ".")) + 1

    def get_currency_price(self):
        full_page = requests.get(self.DOLLAR_RUB, headers=self.headers)

        soup = BeautifulSoup(full_page.content, 'html.parser')
        convert = soup.findAll("span", {"class": "DFlfde SwHCTb", "data-precision": 2})
        return convert[0].text
