import json
import os
import re

from docx import Document
from openai import OpenAI
from PyPDF2 import PdfReader


class ResumeExtractionError(Exception):
    """Raised when resume parsing fails and data should not be persisted."""


MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def unique_keep_order(values):
    seen = set()
    result = []
    for value in values:
        normalized = normalize_text(str(value))
        key = normalized.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def parse_date_token(token):
    token = normalize_text(token).lower()

    mm_yyyy = re.match(r"^(\d{1,2})/(\d{4})$", token)
    if mm_yyyy:
        month, year = int(mm_yyyy.group(1)), int(mm_yyyy.group(2))
        month = month if 1 <= month <= 12 else 1
        return year, month

    month_year = re.match(r"^([a-z]+)\s+(\d{4})$", token)
    if month_year:
        month = MONTH_MAP.get(month_year.group(1), 1)
        year = int(month_year.group(2))
        return year, month

    year_only = re.match(r"^(\d{4})$", token)
    if year_only:
        return int(year_only.group(1)), 1

    return 0, 0


def parse_duration_sort_key(duration):
    if not duration:
        return (0, 0, 0, 0)

    cleaned = normalize_text(duration).lower()
    is_current = "present" in cleaned or "current" in cleaned
    parts = [p.strip() for p in re.split(r"\s*-\s*", cleaned, maxsplit=1)]
    start = parse_date_token(parts[0]) if parts else (0, 0)

    end = (9999, 12) if is_current else (0, 0)
    if len(parts) == 2 and not is_current:
        end = parse_date_token(parts[1])

    return end[0], end[1], start[0], start[1]


def sort_company_history(company_history):
    prepared = []
    for item in company_history:
        if not isinstance(item, dict):
            continue
        company = normalize_text(item.get("company", ""))
        if not company:
            continue

        duration = normalize_text(item.get("duration", ""))
        is_current = bool(item.get("is_current", False))
        if re.search(r"\b(current|present)\b", duration, re.IGNORECASE):
            is_current = True

        prepared.append(
            {
                "company": company,
                "duration": duration,
                "is_current": is_current,
            }
        )

    deduped = []
    seen = set()
    for item in prepared:
        key = item["company"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(
        key=lambda item: (
            1 if item["is_current"] else 0,
            *parse_duration_sort_key(item["duration"]),
        ),
        reverse=True,
    )
    return deduped


def extract_text_from_file(file_path):
    """Extract text from PDF or DOCX file."""
    text = ""
    try:
        if file_path.lower().endswith(".pdf"):
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            raise ValueError("Unsupported file type")
    except Exception as exc:
        print(f"Error extracting text: {exc}")
        return ""
    return text.strip()


def parse_json_from_completion(content):
    result_text = (content or "").strip()
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()
    return json.loads(result_text)


def run_llm_json(client, prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.1,
    )
    return parse_json_from_completion(response.choices[0].message.content)


def extract_resume_info(file_path):
    """Extract resume information using OpenAI API."""
    text = extract_text_from_file(file_path)
    if not text:
        raise ResumeExtractionError("unable to read text from the uploaded resume")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ResumeExtractionError("OpenAI API key is not configured")

    client = OpenAI(api_key=api_key)

    base_prompt = f"""
Extract and return a valid JSON object with EXACT keys:
- name: string
- email: string
- phone: string
- company: string (current/latest company)
- designation: string (current/latest role title)
- skills: array of strings (as exhaustive as possible, include all explicit technical/domain skills found)
- company_history: array of objects with keys:
  - company: string
  - duration: string (preserve source format, e.g. "Jan 2022 - Present" or "02/2024 - 07/2025")
  - is_current: boolean

Rules:
- Use ONLY resume evidence.
- Ensure company_history is in reverse-chronological order (current role first).
- If one role has Present/Current in duration, mark it is_current=true.
- Include as many skills as explicitly mentioned (skills section + experience/projects).
- If missing, use empty string / empty array.

Resume text:
{text}
"""

    verifier_prompt = f"""
From the same resume text, return ONLY this JSON object:
- skills: array of strings (maximize recall, keep entries meaningful and non-empty)
- company_history: array of objects with keys: company, duration, is_current

Rules:
- Capture every explicit skill mention.
- Company history must be reverse chronological and preserve date strings.
- If a duration includes Present/Current, set is_current=true for that company.

Resume text:
{text}
"""

    try:
        primary = run_llm_json(client, base_prompt)
        verifier = run_llm_json(client, verifier_prompt)

        primary_skills = primary.get("skills") if isinstance(primary.get("skills"), list) else []
        verifier_skills = verifier.get("skills") if isinstance(verifier.get("skills"), list) else []
        skills = unique_keep_order(primary_skills + verifier_skills)

        primary_history = primary.get("company_history") if isinstance(primary.get("company_history"), list) else []
        verifier_history = verifier.get("company_history") if isinstance(verifier.get("company_history"), list) else []
        company_history = sort_company_history(primary_history + verifier_history)

        name = normalize_text(primary.get("name", ""))
        email = normalize_text(primary.get("email", ""))
        phone = normalize_text(primary.get("phone", ""))
        designation = normalize_text(primary.get("designation", ""))
        company = normalize_text(primary.get("company", ""))

        if company_history:
            company = company_history[0]["company"]
            if not designation:
                designation = normalize_text(primary.get("designation", ""))

        if not name or not email:
            raise ResumeExtractionError(
                "resume content could not be parsed into required fields (name/email)"
            )

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "designation": designation,
            "skills": skills,
            "company_history": company_history,
        }
    except ResumeExtractionError:
        raise
    except Exception as exc:
        print(f"Error with OpenAI API: {exc}")
        raise ResumeExtractionError(f"OpenAI extraction failed: {exc}") from exc
