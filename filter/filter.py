import os
import json
from datetime import datetime


class PaperInfo:
    def __init__(self, title, abstract, submitted):
        self.source = None
        self.title = title
        self.abstract = abstract
        self.submitted = submitted

    def add_source(self, source: str) -> None:
        self.source = source

    def update_submitted(self, new_date: datetime) -> None:
        self.submitted = new_date


def get_files() -> list[str]:
    # recursively search for .json files in the parent directory
    files = []
    for root, dirs, filenames in os.walk(os.path.join(os.getcwd(), "..")):
        for filename in filenames:
            if filename.endswith(".json") and "filtered" in filename:
                files.append(os.path.join(root, filename))

    return files


def load_json(file: str) -> list[PaperInfo]:
    with open(file, "r") as f:
        data = json.load(f)

    papers = []
    for paper in data:
        papers.append(PaperInfo(paper["title"], paper["summary"], paper["submitted"]))

    return papers


def parse_date(date_str: str) -> datetime or None:
    # List of date formats to try
    date_formats = [
        "%d %B %Y",  # 30 April 2021
        "%Y-%m-%d %H:%M:%S%z",  # 2000-12-20 10:54:00+00:00
        "%Y",  # 2024
        "%Y-%m-%d",  # 2018-06-26
        "%Y-%m-%d %H:%M:%S"  # 2023-07-06 00:00:00
    ]

    if date_str is None or date_str == "" or date_str == "None":
        return None

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def parse_ieee_date(date_str: str) -> datetime or None:
    if date_str is None or date_str == "" or date_str == "None":
        return None

    try:
        date_splitted = date_str.split(" ")
        days = date_splitted[0]
        months = date_splitted[1]
        year = date_splitted[2]
        return datetime.strptime(f"{days[0]} {months} {year}", "%d %B %Y")
    except ValueError:
        return None


def filter_papers(papers: list[PaperInfo]) -> list[PaperInfo]:
    result = []
    for paper in papers:
        if "None" in paper.submitted:
            continue

        if paper.source == "ieee":
            date = parse_ieee_date(paper.submitted)
        else:
            date = parse_date(paper.submitted)
        if date is None:
            continue

        # Update the date format to YYYY-MM-DD
        if date is not None and date.year >= 2017:
            paper.update_submitted(date.strftime("%Y-%m-%d"))
            result.append(paper)
    return result


def main():
    files = get_files()

    papers: dict[str, list[PaperInfo]] = dict()
    for file in files:
        jsons = load_json(file)
        print(f"Loaded {len(jsons)} papers from {file}")

        # get filename from path
        source = file.split("/")[-1].split(".")[0].split("_")[0]
        papers[source] = jsons
    print("Total papers:", sum(len(jsons) for jsons in papers.values()))

    # update the source of each paper
    for source, jsons in papers.items():
        for paper in jsons:
            paper.add_source(source)

    filtered_papers: list[PaperInfo] = []
    for source, jsons in papers.items():
        filtered = filter_papers(jsons)
        filtered_papers.extend(filtered)
    print(f"Filtered {len(filtered_papers)} papers")

    # remove duplicates
    filtered_papers = list({paper.title: paper for paper in filtered_papers}.values())
    print(f"Remove duplicates {len(filtered_papers)} papers")

    # group by source
    grouped_papers = dict()
    for paper in filtered_papers:
        if paper.source not in grouped_papers:
            grouped_papers[paper.source] = []
        grouped_papers[paper.source].append(paper)

    # print statistics
    for source, filtered_papers in grouped_papers.items():
        new_len = len(filtered_papers)
        old_len = len(papers[source])
        print(f"{source}: {old_len} -> {new_len}")

    # Save filtered papers to a new json file
    with open("filtered_papers.json", "w", encoding='utf8') as f:
        json.dump([paper.__dict__ for paper in filtered_papers], f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
