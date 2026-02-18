import json
import os
import uuid
import logging
import requests
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from docxtpl import DocxTemplate


# ==========================================================
# App Config
# ==========================================================

app = FastAPI(title="CV Renderer", version="3.2.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================================================
# Request Model
# ========================================================== 
class CVRequest(BaseModel):
    template_url: HttpUrl
    cv_data: str


# ==========================================================
# Context Normalization
# ==========================================================
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

    for key, value in defaults.items():
        if key not in ctx or ctx[key] is None:
            ctx[key] = value

    if not isinstance(ctx.get("candidate"), dict):
        ctx["candidate"] = defaults["candidate"]

    if not isinstance(ctx.get("tools"), dict):
        ctx["tools"] = defaults["tools"]

    return ctx


# ==========================================================
# Health Endpoint
# ========================================================== 
@app.get("/")
def root():
    return {"status": "CV Renderer is live", "version": "3.2.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ==========================================================
# Template Download
# ==========================================================
def download_template(url: str) -> bytes:
    try:
        logger.info(f"Downloading template from: {url}")

        response = requests.get(
            url,
            allow_redirects=True,
            timeout=20
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")

        return response.content

    except Exception as e:
        logger.error(f"Template download failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Template download error: {str(e)}"
        )


# ==========================================================
# Render Endpoint
# ==========================================================
@app.post("/render_cv")
async def render_cv(request: CVRequest):

    # 1️ Download template
    template_bytes = download_template(str(request.template_url))

    # 2️ Parse JSON
    try:
        context = json.loads(request.cv_data)

        if not isinstance(context, dict):
            raise ValueError("cv_data must be a JSON object")

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cv_data JSON: {str(e)}"
        )

    context = normalize_context(context)

    # 3️ Render document safely
    try:
        template_path = f"/tmp/template_{uuid.uuid4()}.docx"
        output_path = f"/tmp/CV_{uuid.uuid4()}.docx"

        # Save template
        with open(template_path, "wb") as f:
            f.write(template_bytes)

        # Render
        doc = DocxTemplate(template_path)
        doc.render(context)
        doc.save(output_path)

        # Return file (IMPORTANT: no TemporaryDirectory!)
        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="CV.docx"
        )

    except Exception as e:
        logger.error(f"Rendering error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document rendering error: {str(e)}"
        )