import json
import base64
import tempfile
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docxtpl import DocxTemplate


app = FastAPI(title="CV Renderer", version="2.0.0")


# ==============================
# Request Model (JSON only)
# ==============================

class CVRequest(BaseModel):
    template_base64: str
    cv_data: str


# ==============================
# Context Normalization
# ==============================

def normalize_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    defaults = {
        "candidate": {
            "first_name": "",
            "last_name": "",
            "location": "",
            "phone": "",
            "email": "",
        },
        "target_title": "",
        "headline_keywords": "",
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


# ==============================
# Health Check
# ==============================

@app.get("/health")
def health():
    return {"status": "ok"}


# ==============================
# Render Endpoint (JSON)
# ==============================

@app.post("/render_cv")
async def render_cv(request: CVRequest):

    # Decode template from base64
    try:
        template_bytes = base64.b64decode(request.template_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template_base64 encoding")

    # Parse cv_data JSON
    try:
        context = json.loads(request.cv_data)
        if not isinstance(context, dict):
            raise ValueError("cv_data must be a JSON object")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid cv_data JSON: {e}")

    context = normalize_context(context)

    with tempfile.TemporaryDirectory() as td:
        template_path = f"{td}/template.docx"
        output_path = f"{td}/CV.docx"

        # Write decoded template
        with open(template_path, "wb") as f:
            f.write(template_bytes)

        # Render document
        doc = DocxTemplate(template_path)
        doc.render(context)
        doc.save(output_path)

        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="CV.docx"
        )
