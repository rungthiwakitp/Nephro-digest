from __future__ import annotations

from openai import OpenAI

from nephro_digest.feeds import Paper


SYSTEM_PROMPT = """You are a nephrologist summarizing new medical literature for busy kidney clinicians and researchers.
Write concise, accurate summaries. Focus on kidney disease, dialysis, transplant, hypertension, cardiorenal medicine,
glomerular disease, AKI, CKD, and practice-changing implications. Do not overstate findings."""


def summarize_paper(paper: Paper, model: str, max_output_tokens: int) -> str:
    abstract = paper.abstract or "No abstract was included in the RSS feed."
    doi = paper.doi or "Not found in feed"
    url = paper.url or "Not found in feed"

    user_prompt = f"""Summarize this paper for a nephrology audience.

Return exactly:
- One sentence bottom line
- 3 concise bullet points covering methods/population, key results, and nephrology relevance
- One brief caution/limitation if apparent

Journal: {paper.journal}
Title: {paper.title}
DOI: {doi}
URL: {url}
Abstract: {abstract}
"""

    client = OpenAI()
    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=user_prompt,
        max_output_tokens=max_output_tokens,
    )
    return response.output_text.strip()

