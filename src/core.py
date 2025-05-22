import os
import json
import re
import logging
import tempfile
import shutil

import PyPDF2
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from zip_processor import ZipFileProcessor
from llm_evaluator import LLMEvaluator
from system_prompt import SYSTEM_PROMPT

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Constants
RESOURCES_PATH = "resources/"

SUPPORTED_EXTENSIONS = [
    ".py",  # Python
    ".cs",  # C#
    ".c",  # C
    ".h",  # C Header
    ".cpp",  # C++
    ".hpp",  # C++ Header
    ".cc",  # C++
    ".hh",  # C++ Header
    ".java",  # Java
    ".js",  # JavaScript
    ".ts",  # TypeScript
    ".go",  # Go
    ".rs",  # Rust
    ".kt",  # Kotlin
    ".kts",  # Kotlin Script
    ".swift",  # Swift
    ".php",  # PHP
    ".rb",  # Ruby
]

DEFAULT_OUTPUT_ROW = {
    "Type": "None",
    "Weakness": "None",
    "Severity": "None",
    "File": "None",
    "Code": "None",
    "Justification": "None",
}


def extract_standard_text() -> str:
    """
    Extracts text from all PDF files in the 'resources/' directory.

    Returns:
        str: The combined text content from all PDF files.
    """
    combined_text = ""

    for filename in os.listdir(RESOURCES_PATH):
        if not filename.lower().endswith(".pdf"):
            continue

        file_path = os.path.join(RESOURCES_PATH, filename)

        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = "".join(page.extract_text() or "" for page in reader.pages)
                combined_text += f"\n\n# {filename}\n{text}"
        except Exception as e:
            logger.warning(f"Failed to extract text from {filename}: {e}")

    return combined_text

# Preloaded standard text
STANDARD_TEXT = extract_standard_text()


def save_uploaded_zip(gradio_file) -> str:
    """
    Saves a Gradio file object to a temporary ZIP file.

    Args:
        gradio_file: Uploaded file object from Gradio.

    Returns:
        str: Path to the saved temporary ZIP file.
    """
    temp_path = tempfile.NamedTemporaryFile(suffix=".zip", delete=False).name
    shutil.copy(gradio_file.name, temp_path)
    return temp_path


def evaluate_zip(zip_path: str, verbose: bool = True) -> str:
    """
    Evaluates source code files in a ZIP archive using an LLM.

    Args:
        zip_path (str): Path to the ZIP archive.
        verbose (bool): Whether to print processing info (default True).

    Returns:
        str: Raw response from the LLM.
    """
    zip_processor = ZipFileProcessor(zip_file_path=zip_path, logger=logger)
    code_files = zip_processor.get_all_files(
        allowed_extensions=SUPPORTED_EXTENSIONS, verbose=verbose
    )

    if not code_files:
        return json.dumps([{"Error": "No source code files found."}])

    llm = LLMEvaluator(
        model=ChatGoogleGenerativeAI(
            api_key=os.getenv("API_KEY"),
            model="gemini-2.0-flash",
        ),
        system_prompt=SYSTEM_PROMPT,
    )

    code_combined = "\n".join(str(code_files))
    payload = {"standard": STANDARD_TEXT, "code_snippet": code_combined}

    response = llm.evaluate(payload)
    logger.info(f"LLM response: {response}")
    return response


def parse_response_to_dataframe(response: str) -> pd.DataFrame:
    """
    Parses the LLM's JSON response into a Pandas DataFrame.

    Args:
        response (str): Raw JSON response from the LLM.

    Returns:
        pd.DataFrame: Parsed DataFrame or fallback error information.
    """
    try:
        match = re.search(r"(\[.*\])", response, re.DOTALL)
        if not match:
            raise ValueError("No JSON array found in response.")

        json_str = match.group(1)
        parsed = json.loads(json_str)

        if not isinstance(parsed, list) or not all(
            isinstance(item, dict) for item in parsed
        ):
            raise ValueError("Parsed response is not a list of dictionaries.")

        if not parsed:
            return pd.DataFrame([DEFAULT_OUTPUT_ROW])

        return pd.DataFrame(parsed)

    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return pd.DataFrame([{"Error": str(e), "Raw response": response}])
