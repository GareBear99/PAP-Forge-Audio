from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except Exception:  # pragma: no cover
    FastAPI = None
    HTTPException = RuntimeError
    BaseModel = object

from .project import PAPProject


def create_app(template_root: str | Path | None = None):
    if FastAPI is None:
        raise RuntimeError('fastapi is not installed. Install pap-forge[api] to use the HTTP service.')

    resolved_template_root = Path(template_root) if template_root is not None else Path(__file__).resolve().parents[2] / 'templates' / 'juce_effect_basic'
    app = FastAPI(title='PAP Forge API', version='0.9.0')

    class InitPayload(BaseModel):
        project_name: str
        workspace_root: str

    class PromptPayload(BaseModel):
        prompt: str
        branch_name: str = 'main'

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'pap-api'}

    @app.post('/projects/init')
    def init_project(payload: InitPayload):
        project = PAPProject.init(payload.project_name, payload.workspace_root, template_root=resolved_template_root)
        return {'status': 'ok', 'project_root': str(project.root)}

    @app.post('/projects/{project_root:path}/generate')
    def generate(project_root: str, payload: PromptPayload):
        try:
            project = PAPProject.open(project_root)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return project.generate_from_prompt(payload.prompt, branch_name=payload.branch_name)

    @app.get('/projects/{project_root:path}/status')
    def status(project_root: str):
        try:
            project = PAPProject.open(project_root)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return project.status()

    @app.get('/projects/{project_root:path}/doctor')
    def doctor(project_root: str):
        try:
            project = PAPProject.open(project_root)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return project.doctor()

    return app
