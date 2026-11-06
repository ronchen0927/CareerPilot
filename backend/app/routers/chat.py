"""Streaming job Q&A chat endpoint."""

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..models import JobListing
from ..openai_client import get_openai_client

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    job: JobListing
    user_cv: str
    job_description: str = ""


_SYSTEM_PROMPT = """\
You are a professional career advisor helping a job seeker evaluate and prepare \
for a specific job opportunity. Always respond in Traditional Chinese (繁體中文).

[Target Job]
Title: {job}
Company: {company}
City: {city}
Salary: {salary}
Experience required: {experience}
Education required: {education}
Job URL: {link}

[User Resume and Preferences]
{user_cv}\
"""


@router.post("/api/chat")
async def chat(request: ChatRequest):
    client = get_openai_client()
    job = request.job
    system_content = _SYSTEM_PROMPT.format(
        job=job.job,
        company=job.company,
        city=job.city,
        salary=job.salary,
        experience=job.experience,
        education=job.education,
        link=job.link,
        user_cv=request.user_cv.strip() or "（未提供）",
    )
    if request.job_description.strip():
        system_content += f"\n\n[Job Description]\n{request.job_description.strip()}"

    async def generate():
        try:
            stream = await client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=[
                    {"role": "system", "content": system_content},
                    *[{"role": m.role, "content": m.content} for m in request.messages],
                ],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            from openai import OpenAIError

            if isinstance(e, OpenAIError):
                yield "\n\n⚠ 服務暫時無法使用，請稍後再試。"
            else:
                yield "\n\n⚠ 發生未預期的錯誤，請稍後再試。"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
