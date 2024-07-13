import re

from semanticscholar import SemanticScholar
from semanticscholar.SemanticScholarException import NoMorePagesException
from tqdm import tqdm


class PaperInfo:
    def __init__(self, title, abstract, doi, publication_date):
        self.title = title
        self.abstract = abstract
        self.doi = doi
        self.publication_date = publication_date


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


def process_papers(papers) -> dict[str, PaperInfo]:
    results: dict[str, PaperInfo] = dict()
    for paper in papers:
        if paper.paperId not in results:
            doi = paper.externalIds["DOI"] if "DOI" in paper.externalIds else None

            results[paper.paperId] = PaperInfo(
                title=paper.title,
                abstract=paper.abstract,
                doi=doi,
                publication_date=paper.publicationDate
            )
    return results


def main():
    sch = SemanticScholar()

    search_keys = [
        "TTS",
        "Text to speech",
    ]

    results: dict[str, PaperInfo] = dict()
    for search_key in search_keys:
        papers = sch.search_paper(search_key, bulk=True)
        res = process_papers(papers)
        results.update(res)

        has_next_page = True

        while has_next_page:
            try:
                papers.next_page()
                # print(f"Title of the paper: {papers[0].title}")
                res = process_papers(papers)
                results.update(res)
            except NoMorePagesException:
                has_next_page = False

    print(f"Found {len(results)} papers")
    save(list(results.values()), "semanticscholar_results.json")

    filtered = filter_papers(list(results.values()))
    print(f"Filtered {len(filtered)} papers")
    save(filtered, "semanticscholar_filtered_results.json")


if __name__ == "__main__":
    main()


