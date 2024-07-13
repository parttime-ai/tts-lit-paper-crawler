import time
import arxiv
import re
from tqdm import tqdm

def save(results: list[arxiv.Result], filename="papers.json"):
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
            "pdf": result.pdf_url,
            "doi": result.doi,
            "summary": result.summary,
            "submitted": str(result.published),
        } for result in results], f, indent=4)

# Construct the default API client.
client = arxiv.Client(page_size=1000, delay_seconds=5)

abs_keywords = [
    "Emotion", "Emotional", "Prosody", "prosodic", "Paralinguistic",
    "Natural", "Naturalness", "Expressive", "Style", 
    "Human", "State-of-the-Art", "SOTA", "SOA", "State-of-Art", 
    "Voice", "Modulation", "Speech", "Pitch", "Rhythm", "Dynamic", 
    "Intonation", "Stress", "Affective", "Duration"
]

def escape_keyword(keyword):
    return re.escape(keyword).replace(r'\-', r'-')

# Combine keywords into a single regex pattern
pattern = "|".join([escape_keyword(keyword) for keyword in abs_keywords])

# Compile the regex pattern
regex = re.compile(pattern, re.IGNORECASE)

def compare(text: str):
    # check if one of the keywords is in the title
    return bool(regex.search(text))

def search(query):
    search = arxiv.Search(
      query = f"{query}",
      max_results = None,
      sort_by = arxiv.SortCriterion.SubmittedDate
    )
    return search

result: dict[str, arxiv.Result] = {}

for q in tqdm(["TTS", 'TTSOR"Text to speech"']):
    results = client.results(search(q))
    # save(results, f"arxiv_{q}_results.json")

    # check if the paper is relevant with the keywords
    for r in tqdm(results):
        if r.title not in result:
            if compare(r.summary):
                result[r.title] = r

print("Found", len(result), "papers")


save(list(result.values()), "arxiv_filtered_results.json")
