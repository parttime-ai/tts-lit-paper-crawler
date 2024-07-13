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
    options.add_argument("--headless=new")
    options.add_argument("--disable-extensions")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(
        service=service,
        options=options
    )
    return driver


def get_hits(driver: WebDriver, query: str) -> int:
    driver.get(query)
    hits = driver.find_element(By.CLASS_NAME, 'hitsLength').text
    hits = hits.replace(",", "")
    return int(hits)


def login(driver: WebDriver):
    dotenv.load_dotenv()
    institute = os.getenv('ACM_INSTITUTE')
    password = os.getenv('ACM_PASSWORD')
    username = os.getenv('ACM_USERNAME')

    driver.get("https://dl.acm.org/")

    # sign_in_path = '//*[@id="pb-page-content"]/div/header/div[1]/div[1]/div[2]/div[2]/ul/li[4]/div/ul/li[1]'
    driver.find_element(By.CLASS_NAME, 'login-link').click()
    driver.find_element(By.ID, '#pane-0552177a-9137-4ca8-90d3-10b23a0c57c721con').click()

    dropdown_path = '//*[@id="pane-0552177a-9137-4ca8-90d3-10b23a0c57c721"]/section/div/div/div/a'
    driver.find_element(By.XPATH, dropdown_path).click()
    driver.find_element(By.CLASS_NAME, 'search-input').send_keys(institute)
    institute_dropdown_path = '//*[@id="pane-0552177a-9137-4ca8-90d3-10b23a0c57c721"]/section/div/div/div/ul/ul/li[157]'
    driver.find_element(By.XPATH, institute_dropdown_path).click()

    # login idp.htw-aalen.de
    driver.find_element(By.XPATH, '//*[@id="username"]').send_keys(username)
    driver.find_element(By.XPATH, '//*[@id="password"]').send_keys(password)
    driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/form/div[5]/button').click()


def get_papers(driver: WebDriver, query: str, hits: int) -> list[PaperInfo]:
    res: list[PaperInfo] = []

    if hits > 2000:
        print("Too many hits. Only first 2000 will be downloaded. Was ", hits, "hits.")
        hits = 2000

    max_page = (hits // 50)
    for page in tqdm(range(0, max_page), desc="Pages"):
        print("Page", page)
        url = query + f"&startPage={page}&pageSize=50"
        driver.get(url)
        WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, '//*[@id="skip-to-main-content"]/main/div[1]/div/div[2]/div/ul')))

        # fields = driver.find_elements(By.CLASS_NAME, 'hlFld-Title')

        page_source = BeautifulSoup(driver.page_source, 'html.parser')
        fields = page_source.find_all("a", class_="hlFld-Title")

        doi_links = page_source.find_all("a", class_="issue-item__doi dot-separator")

        dois = [doi_link["href"] for doi_link in doi_links]
        # strip "https://doi.org/" from the doi
        dois = [doi.replace("https://doi.org/", "") for doi in dois]

        incorrect_dois = []

        for doi in tqdm(dois, desc="Papers"):
            try:
                driver.get(f"https://dl.acm.org/doi/{doi}")

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                title = soup.find("h1", attrs={"property": "name"}).text
                abstract = soup.find("div", attrs={"role": "paragraph"}).text
                doi_elem = soup.find("meta", attrs={"name": "publication_doi"})
                doi = doi_elem["content"]
                publication_date = soup.find("span", class_="core-date-published").text

                res.append(PaperInfo(title, abstract, doi, publication_date))
            except Exception as e:
                print(e)
                print("Error while extracting paper info. Skipping paper. DOI:", doi)
                incorrect_dois.append(doi)
                # continue

        # for field in tqdm(fields, desc="Papers"):
        #     field.click()
        #
        #     soup = BeautifulSoup(driver.page_source, 'html.parser')
        #     title = soup.find("h1", attrs={"property": "name"}).text
        #     abstract = soup.find("div", attrs={"role": "paragraph"}).text
        #     doi_elem = soup.find("meta", attrs={"name": "publication_doi"})
        #     doi = doi_elem["content"]
        #     publication_date = soup.find("span", class_="core-date-published").text
        #
        #     res.append(PaperInfo(title, abstract, doi, publication_date))
        #
        #     driver.back()

    return res


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


def filter_papers(papers: list[PaperInfo]) -> list[PaperInfo]:
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

    # Combine keywords into a single regex pattern
    pattern = "|".join([escape_keyword(keyword) for keyword in abs_keywords])

    # Compile the regex pattern
    regex = re.compile(pattern, re.IGNORECASE)

    filtered_papers = []
    for paper in tqdm(papers):
        if compare(paper.title, regex):
            filtered_papers.append(paper)

    return filtered_papers


def main():
    driver = get_chrome()
    # login(driver)

    query = "(tts AND prosod*) OR (TTS AND emot*) OR (TTS AND style*)"
    transformed_query = query.replace("(", "%28").replace(")", "%29").replace(" ", "+")
    # print(transformed_query)

    content_types = ["research-article", "short-paper"]

    papers = []

    for content_type in tqdm(content_types, desc="Content Types"):
        url = f"https://dl.acm.org/action/doSearch?fillQuickSearch=false&target=advanced&expand=dl&AfterMonth=1&AfterYear=2016&field1=AllField&text1={transformed_query}&ContentItemType={content_type}"
        hits = get_hits(driver, url)
        print("Found", hits, "papers for content type", content_type)

        papers += get_papers(driver, url, hits)

    save(papers, "acm_papers.json")

    filtered_papers = filter_papers(papers)
    save(filtered_papers, "acm_filtered_papers.json")

    print("Downloaded", len(papers), "papers")
    print("Filtered", len(filtered_papers), "papers")
    driver.quit()


if __name__ == "__main__":
    main()