import json


def load_json(path: str):
    with open(path, "r", encoding="utf8") as f:
        return json.load(f)


def remove_duplicates(papers):
    # Create a dictionary to map lowercase papers to their original versions
    paper_map = {str.lower(paper): paper for paper in papers}

    # Get the unique lowercase papers
    unique_papers = list(set(paper_map.keys()))

    # Retrieve the original versions of the unique papers
    res = [paper_map[paper] for paper in unique_papers]

    return res


def get_added_papers(papers):
    res = papers['added_papers']
    return res


class Paper:
    def __init__(self, paper):
        self.paper = paper
        self.year = paper.split('-')[0]
        self.title = str.join('-', paper.split('-')[1:])
        self.title2 = paper[5:]
        self.correct = self.title2 == self.title


class OriginalPaper:
    def __init__(self, paper):
        self.title = paper["title"]
        self.abstract = paper["abstract"]
        self.submitted = paper["submitted"]
        self.source = paper["source"]
        self.year = self.submitted.split("-")[0]

    def to_dict(self):
        return {
            "title": self.title,
            "abstract": self.abstract,
            "submitted": self.submitted,
            "source": self.source,
        }


def match_with_original(filtered, original):
    filtered_paper = {paper: Paper(paper) for paper in filtered}
    original_paper = [OriginalPaper(paper) for paper in original]
    orig_paper = {f"{paper.year}-{paper.title}": paper for paper in original_paper}

    res = []

    for k, v in filtered_paper.items():
        if k in orig_paper:
            res.append(orig_paper[k])

    return res


def write_to_file(papers, write_path):
    with open(write_path, "w", encoding="utf8") as f:
        json.dump(papers, f, indent=4)


if __name__ == "__main__":
    file_path = "progress_first_iteration.json"
    data = load_json(file_path)
    added_papers = get_added_papers(data)

    unfiltered_data = load_json("filter/filtered_papers_total.json")

    print('Before', len(added_papers))
    res = remove_duplicates(added_papers)
    print('After', len(res))

    print("Write removed_duplicates")
    write_to_file(sorted(res), "removed_duplicates.json")

    matched = match_with_original(res, unfiltered_data)
    if len(matched) == len(res):
        print("Write matches")
        write_to_file([paper.to_dict() for paper in sorted(matched, key=lambda x: x.submitted)], "matched_papers.json")
    else:
        raise Exception("Papers are unmatched")


