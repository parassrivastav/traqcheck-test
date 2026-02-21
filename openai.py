import openai
import os
import json
from PyPDF2 import PdfReader
from docx import Document

def extract_text_from_file(file_path):
    """Extract text from PDF or DOCX file."""
    text = ""
    try:
        if file_path.lower().endswith('.pdf'):
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif file_path.lower().endswith('.docx'):
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            raise ValueError("Unsupported file type")
    except Exception as e:
        print(f"Error extracting text: {e}")
        text = ""
    return text.strip()

def extract_resume_info(file_path):
    """Extract resume information using OpenAI API."""
    text = extract_text_from_file(file_path)
    if not text:
        return {
            'name': 'Unknown',
            'email': 'unknown@example.com',
            'phone': 'Unknown',
            'company': 'Unknown',
            'designation': 'Unknown',
            'skills': []
        }

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")

    client = openai.OpenAI(api_key=api_key)

    prompt = f"""
    Extract the following information from the resume text below. Return the result as a valid JSON object with these exact keys:
    - name: string
    - email: string
    - phone: string
    - company: string
    - designation: string
    - skills: array of strings

    If any information is not found, use "Not found" for strings or empty array for skills.

    Resume text:
    {text}

    JSON:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )
        result_text = response.choices[0].message.content.strip()
        
        # Clean up the response to extract JSON
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        data = json.loads(result_text)
        return data
    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return {
            'name': 'Error extracting',
            'email': 'error@example.com',
            'phone': 'Error',
            'company': 'Error',
            'designation': 'Error',
            'skills': []
        }