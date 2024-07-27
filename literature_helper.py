import json
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

progress_file_path = "progress.json"


class PaperInfo(BaseModel):
    title: str
    abstract: str
    submitted: str
    source: str
    id: str


class InternalPaperInfo(BaseModel):
    title: str
    abstract: str
    submitted: str
    source: str


class Progress(BaseModel):
    added_papers: List[str]
    deleted_papers: List[str]


def load_papers(path: str) -> list[PaperInfo]:
    # Load papers from JSON file
    with open(path, "r") as f:
        papers = json.load(f)

    # Convert to PaperInfo objects
    internal = []

    for paper in papers:
        try:
            internal.append(InternalPaperInfo(**paper))
        except Exception as e:
            print(f"Error loading paper: {e} {paper['title']}")

    # sort by date and source
    internal.sort(key=lambda x: (x.submitted, x.source))

    result = []

    # Add an ID to each paper
    for i, paper in enumerate(internal):
        year = paper.submitted.split("-")[0]
        # hash the title to get a unique ID
        paper_id = f"{year}-{paper.title}"

        result.append(PaperInfo(id=paper_id, title=paper.title, abstract=paper.abstract, submitted=paper.submitted,
                                source=paper.source))

    return result


def save_progress(progress: Progress):
    with open(progress_file_path, "w", encoding="utf8") as f:
        json.dump({"added_papers": [paper_id for paper_id in progress.added_papers],
                   "deleted_papers": [paper_id for paper_id in progress.deleted_papers]}, f, indent=4)


def load_progress() -> Progress:
    try:
        with open(progress_file_path, "r", encoding="utf8") as f:
            data = json.load(f)
            return Progress(added_papers=data["added_papers"], deleted_papers=data["deleted_papers"])
    except Exception:
        return Progress(added_papers=[], deleted_papers=[])


app = FastAPI()


@app.get("/diff/", response_model=List[PaperInfo], name="get_diff_papers")
async def get_diff_papers():
    papers = load_papers("filter/filtered_papers.json")
    progress = load_progress()

    # Get the papers that have not been seen yet
    added_seen_ids = {paper for paper in progress.added_papers}
    deleted_seen_ids = {paper for paper in progress.deleted_papers}

    # Filter out the papers that have been seen
    result = [paper for paper in papers if paper.id not in added_seen_ids and paper.id not in deleted_seen_ids]

    return result


@app.get("/progress/", response_model=Progress)
async def get_progress():
    return load_progress()


@app.post("/papers")
async def add_paper(paper: PaperInfo):
    progress = load_progress()
    progress.added_papers.append(paper.id)
    save_progress(progress)
    return {"status": "success"}


@app.delete("/papers")
async def delete_paper(paper: PaperInfo):
    progress = load_progress()
    progress.deleted_papers.append(paper.id)
    save_progress(progress)
    return {"status": "success"}
