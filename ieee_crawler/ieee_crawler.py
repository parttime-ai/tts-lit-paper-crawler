import os
import random
import re
import time

import dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import selenium.webdriver.support.expected_conditions as EC
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager


class PaperInfo:
    def __init__(self, title, abstract, doi, publication_date):
        self.title = title
        self.abstract = abstract
        self.doi = doi
        self.publication_date = publication_date


def get_chrome():
    options = Options()
    # options.add_argument("--headless=new")
    options.add_argument("--disable-extensions")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(
        service=service,
        options=options
    )
    return driver


def login(driver: WebDriver):
    dotenv.load_dotenv()
    institute = os.getenv('IEEE_INSTITUTE')
    password = os.getenv('IEEE_PASSWORD')
    username = os.getenv('IEEE_USERNAME')


    driver.find_element(By.CLASS_NAME, 'inst-sign-in').click()
    # driver.find_element(By.XPATH, '//*[@id="LayoutWrapper"]/div/div/div[3]/div/xpl-root/header/xpl-header/div/xpl-navbar/div/div[1]/div[3]/xpl-login-modal-trigger/a').click()
    driver.find_element(By.XPATH, '/html/body/ngb-modal-window/div/div/div/xpl-login-modal/div[1]/div[2]/div/div/xpl-login/div/section/div/div/xpl-seamless-access/div/div[1]/button/div').click()
    driver.find_element(By.XPATH, '/html/body/ngb-modal-window/div/div/div/xpl-login-modal/div[1]/div[2]/div/div/xpl-login/div/section/div/div/div[2]/div[2]/xpl-inst-typeahead/div/div/input').send_keys(institute)

    driver.find_element(By.XPATH, '//*[@id="Hochschule Aalen - Technik und Wirtschaft"]').click()

    driver.find_element(By.XPATH, '//*[@id="username"]').send_keys(username)
    driver.find_element(By.XPATH, '//*[@id="password"]').send_keys(password)
    driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/form/div[5]/button').click()


def get_num_pages(driver: WebDriver) -> int:
    try:
        xpath = '//*[@id="xplMainContent"]/div[1]/div[2]/xpl-search-dashboard/section/div/h1/span[1]/span[2]'
        WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, xpath)))

        num_hits_ieee = driver.find_elements(
            By.XPATH,
            xpath
        )[0].text

        pages = int(num_hits_ieee) // 100

        return pages
    except Exception as e:
        print(e)
        return 0


def extract_date(publication_info: str) -> str:
    match = re.search(r'Date of [\w\s]*: {2}(.*)', publication_info)
    if match:
        return match.group(1).strip()
    return ""


def navigate_to_paper(driver: WebDriver, paper_url: str) -> None:
    try:
        driver.get(paper_url)
        WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.XPATH, '//*[@id="xplMainContentLandmark"]/div/xpl-document-details/div/div[1]/section[2]/div/xpl-document-header/section/div[2]/div/div/div[1]/div/div[1]/h1')))
    except Exception as e:
        print(e)


def extract_paper_info(driver: WebDriver, paper_url: str) -> PaperInfo:
    base_iee_url = "https://ieeexplore.ieee.org"
    print(f"Extracting paper info from {base_iee_url}{paper_url}")

    navigate_to_paper(driver, f"{base_iee_url}{paper_url}")

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    try:
        title = soup.find("h1", class_='document-title').text
    except Exception as e:
        print("Error extracting title", e)

    try:
        abstract_container = soup.find("div", class_='abstract-text').div.div.div.text
    except Exception as e:
        print("Error extracting abstract", e)

    try:
        doi_container = soup.find("div", class_='stats-document-abstract-doi')
        if doi_container is not None:
            doi = doi_container.a.text
        else:
            doi = ""
    except Exception as e:
        print("Error extracting doi", e)

    try:
        publication_date = soup.find("div", class_='doc-abstract-confdate')

        if publication_date is None:
            publication_date = soup.find("div", class_='doc-abstract-pubdate')

        publication_date = publication_date.text
    except Exception as e:
        print("Error extracting publication date", e)

    try:
        date = extract_date(publication_date)
    except Exception as e:
        print("Error extracting date", e)

    return PaperInfo(title, abstract_container, doi, date)


def access_page(driver: WebDriver, page_num: int) -> list[PaperInfo]:
    papers = []
    try:
        driver.get(f'{base_search_url}&pageNumber={page_num}')
        WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'List-results-items')))

        # results = driver.find_elements(By.XPATH, xpath)
        # parse with beautifulsoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        results = soup.find_all("div", class_='List-results-items')

        for idx, result in tqdm(enumerate(results)):
            paper_url = result.find("a", class_='fw-bold')['href']
            paper_info = extract_paper_info(driver, paper_url)
            papers.append(paper_info)

            # sleep for a random time between 1 and 2 seconds
            time.sleep(random.uniform(1, 2))

        return papers

    except Exception as e:
        print(e)

def escape_keyword(keyword):
    return re.escape(keyword).replace(r'\-', r'-')


def compare(text: str, regex: re.Pattern[str]) -> bool:
    # check if one of the keywords is in the title
    return bool(regex.search(text))


def save(results: list[PaperInfo], filename="papers.json"):
    # save the papers to a file for later use in json
    # structure of the json file:
    #
    # {
    #     "title": "Title of the paper",
    #     "pdf": "URL to the pdf",
    #     "doi": "DOI of the paper",
    #     "summary": "Summary of the paper",
    # }
    #
    # the file will be named papers.json

    import json
    with open(filename, "w") as f:
        json.dump([{
            "title": result.title,
            # "pdf": result.pdf_url,
            "doi": result.doi,
            "summary": result.abstract,
            "submitted": str(result.publication_date),
        } for result in results], f, indent=4)


base_search_url = 'https://ieeexplore.ieee.org/search/searchresult.jsp?action=search&newsearch=true&matchBoolean=true&queryText=(%22All%20Metadata%22:tts)%20AND%20(%22All%20Metadata%22:prosod*)%20OR%20(%22All%20Metadata%22:tts)%20AND%20(%22All%20Metadata%22:emot*)%20OR%20(%22All%20Metadata%22:tts)%20AND%20(%22All%20Metadata%22:style)&rowsPerPage=100'


abs_keywords = [
    "Emotion", "Emotional", "Prosody", "prosodic", "Paralinguistic",
    "Natural", "Naturalness", "Expressive", "Style",
    "Human", "State-of-the-Art", "SOTA", "SOA", "State-of-Art",
    "Voice", "Modulation", "Speech", "Pitch", "Rhythm", "Dynamic",
    "Intonation", "Stress", "Affective", "Duration"
]


def escape_keyword(keyword):
    return re.escape(keyword).replace(r'\-', r'-')


def compare(text: str, regex: re.Pattern[str]) -> bool:
    # check if one of the keywords is in the title
    return bool(regex.search(text))


def main():
    driver = get_chrome()
    driver.get(base_search_url)
    driver.implicitly_wait(10)
    # login(driver)
    num_pages = get_num_pages(driver)
    print(num_pages)

    papers = []

    for page in tqdm(range(1, num_pages + 1)):
        papers.extend(access_page(driver, page))
        # driver.close()
        # driver = get_chrome()
        # driver.get(base_search_url)
        # driver.implicitly_wait(10)
        # login(driver)

    save(papers, "ieee_papers.json")

    # Combine keywords into a single regex pattern
    pattern = "|".join([escape_keyword(keyword) for keyword in abs_keywords])

    # Compile the regex pattern
    regex = re.compile(pattern, re.IGNORECASE)

    filtered_papers = []
    for paper in tqdm(papers):
        if compare(paper.title, regex):
            filtered_papers.append(paper)

    save(filtered_papers, "ieee_filtered_papers.json")


if __name__ == '__main__':
    main()
