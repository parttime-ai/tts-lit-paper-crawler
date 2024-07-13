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
    papers: List[PaperInfo]


def load_papers(path: str) -> list[PaperInfo]:
    # Load papers from JSON file
    with open(path, "r") as f:
        papers = json.load(f)

    # Convert to PaperInfo objects
    internal = [InternalPaperInfo(**paper) for paper in papers]

    # sort by date and source
    internal.sort(key=lambda x: (x.submitted, x.source))

    result = []

    # Add an ID to each paper
    for i, paper in enumerate(internal):
        year = paper.submitted.split("-")[0]
        # hash the title to get a unique ID
        paper_id = f"{year}-{hash(paper.title)}"

        result.append(PaperInfo(id=paper_id, title=paper.title, abstract=paper.abstract, submitted=paper.submitted,
                                source=paper.source))

    return result


def save_progress(progress: Progress):
    with open(progress_file_path, "w") as f:
        json.dump(progress, f)


def load_progress() -> Progress:
    try:
        with open(progress_file_path, "r", encoding="utf8") as f:
            return Progress(**json.load(f))
    except FileNotFoundError:
        return Progress(papers=[])


app = FastAPI()


@app.get("/papers/", response_model=List[PaperInfo])
async def get_papers():
    return load_papers("filter/filtered_papers.json")


@app.get("/papers/diff/", response_model=List[PaperInfo])
async def get_diff_papers():
    papers = load_papers("filter/filtered_papers.json")
    progress = load_progress()

    # Get the papers that have not been seen yet
    seen_ids = {paper.id for paper in progress.papers}
    result = [paper for paper in papers if paper.id not in seen_ids]

    return result


@app.get("/progress/", response_model=Progress)
async def get_progress():
    return load_progress()


@app.post("/papers")
async def add_paper(paper: PaperInfo):
    progress = load_progress()
    progress.papers.append(paper)
    save_progress(progress)
    return {"status": "success"}


@app.delete("/papers")
async def delete_paper(paper_id: str):
    progress = load_progress()

    # Remove the paper with the given ID from the progress
    progress.papers = [paper for paper in progress.papers if paper.id != paper_id]

    save_progress(progress)
    return {"status": "success"}
