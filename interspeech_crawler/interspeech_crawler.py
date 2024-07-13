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


def get_hits(driver: WebDriver) -> int:
    hits = driver.find_element(By.ID, 'paper_table_info').text

    # extract hits from string "Showing 1 to 50 of 103 entries (filtered from 37,279 total entries)"
    hits = re.search(r"of (\d+) entries", hits).group(1)
    hits = hits.replace(",", "")
    return int(hits)


def extract_paper_info(driver: WebDriver, paper_url: str) -> PaperInfo:
    title = driver.find_element(By.TAG_NAME, "h3").text

    abstract = driver.find_element(By.TAG_NAME, "p").text
    
    # extract doi ("yu06_iscslp") from string "./iscslp_2006/yu06_iscslp.html"
    doi = paper_url.split("/")[-1].replace(".html", "")

    citation = driver.find_element(By.TAG_NAME, "pre").text

    publication_date = re.search(r"year=(\d+)", citation).group(1)

    return PaperInfo(title, abstract, doi, publication_date)



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



def main():
    driver = get_chrome()
    url = "https://www.isca-archive.org/"
    # driver.get(url)

    queries = ["text to speech"]

    papers: dict[str, PaperInfo] = dict()

    for query in tqdm(queries, desc="search query"):
        driver.get(url)
        driver.find_element(By.XPATH, '/html/body/div[8]/div[5]/div/div/div[2]/div[2]/label/input').clear()
        driver.find_element(By.XPATH, '/html/body/div[8]/div[5]/div/div/div[2]/div[2]/label/input').send_keys(query)
        hits = get_hits(driver)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "paper_table"))
        )

        print("")
        print(f"Query: {query}, Hits: {hits}")

        time.sleep(5)

        paper_rows = get_rows(driver)

        has_next = True
        while has_next:
            paper_navigated = 0
            for paper_row in tqdm(paper_rows, desc="Papers"):
                contents = paper_row.contents
                year = int(contents[2].text)

                if year >= 2016:
                    paper_url = contents[0].find("a")["href"]
                    driver.get(f"{url}/{paper_url}")

                    # extract paper info
                    paper_info = extract_paper_info(driver, paper_url)

                    papers[paper_info.doi] = paper_info

                    paper_navigated += 1

            # for _ in range(paper_navigated + 1):
            #     driver.back()
            
            driver.get(url)
            driver.implicitly_wait(5)
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            next_activated = soup.find("a", attrs={"id": "paper_table_next"})["class"]
            has_next = "disabled" not in next_activated

            if has_next:
                driver.find_element(By.ID, "paper_table_next").click()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "paper_table"))
                )
                paper_rows = get_rows(driver)

    save(list(papers.values()), "interspeech_papers.json")

    filtered_papers = filter_papers(list(papers.values()))
    save(filtered_papers, "interspeech_filtered_papers.json")

    print("")
    print("Found", len(papers), "papers")
    print("Filtered", len(filtered_papers), "papers")


def get_rows(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    paper_table = soup.find("table", attrs={"id": "paper_table"})
    paper_table_src = BeautifulSoup(str(paper_table), "html.parser")
    paper_rows = paper_table_src.find_all("tr")
    # skip header row
    paper_rows = paper_rows[1:]
    print("")
    print("Found", len(paper_rows), "papers")
    return paper_rows


if __name__ == "__main__":
    main()
