import time
from paperswithcode import PapersWithCodeClient
from paperswithcode.models import Paper
import re

def save(results: list[Paper], filename="papers.json"):
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
            "arxiv_id": result.arxiv_id if result.arxiv_id is not None else "",
            "pdf": result.url_pdf,
            "summary": result.abstract,
            "submitted": str(result.published),
        } for result in results], f, indent=4)

client = PapersWithCodeClient()

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



tasks = ["emotional-speech-synthesis", "expressive-speech-synthesis", "speech-synthesis", "text-to-speech-synthesis"]

original_results = {}

def get_count(task):
    search = client.task_paper_list(task, items_per_page=1)
    return search.count

def get_results(task, count):
    from tqdm import tqdm
    results = []

    for p in tqdm(range(0, count)):
        try:
            search = client.task_paper_list(task, page=p+1, items_per_page=1)
            results.extend(search.results)
        except Exception as e:
            print(e)
    return results
    

            
results = []
for task in tasks:
    count = get_count(task)
    results = get_results(task, count)

    original_results.update({result.id: result for result in results})

# for task in tasks:
#     # time.sleep(3)
#     results = get_results(task, 1)
#
#     # add the results to the dictionary
#     original_results.update({result.id: result for result in results})
    


filtered_results = [paper for paper in original_results.values() if compare(paper.abstract)]

save(original_results.values(), "paperswithcode_results.json")
print(len(original_results))
save(filtered_results, "paperswithcode_filtered_results.json")
print(len(filtered_results))