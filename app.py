import json
import tempfile
from typing import Any, Dict

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from docxtpl import DocxTemplate

app = FastAPI(title="CV Renderer", version="1.0.0")


def normalize_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    defaults = {
        "candidate": {
            "first_name": "",
            "last_name": "",
            "city": "",
            "phone": "",
            "email": "",
            "linkedin": "",
            "portfolio": "",
            "github": "",
        },
        "headline": "",
        "top_summary": "",
        "summary": "",
        "topkeywords": [],
        "tools": {"office_automation": [], "genai": []},
        "functional_domains": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "languages": [],
    }

    for k, v in defaults.items():
        if k not in ctx or ctx[k] is None:
            ctx[k] = v

    if not isinstance(ctx.get("candidate"), dict):
        ctx["candidate"] = defaults["candidate"]

    if not isinstance(ctx.get("tools"), dict):
        ctx["tools"] = defaults["tools"]

    return ctx


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render_cv")
async def render_cv(
    template: UploadFile = File(...),
    cv_data: str = Form(...)
):
    if not template.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Template must be a .docx file")

    try:
        context = json.loads(cv_data)
        if not isinstance(context, dict):
            raise ValueError("cv_data must be a JSON object")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid cv_data JSON: {e}")

    context = normalize_context(context)

    with tempfile.TemporaryDirectory() as td:
        template_path = f"{td}/template.docx"
        output_path = f"{td}/CV.docx"

        with open(template_path, "wb") as f:
            f.write(await template.read())

        doc = DocxTemplate(template_path)
        doc.render(context)
        doc.save(output_path)

        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="CV.docx"
        )
