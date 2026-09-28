from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    description: str
    competencies: list[str] = []
    rubric: list[str] = []
    publish: bool = True


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    description: str
    criteria: list[str] = []
    status: str = "published"
