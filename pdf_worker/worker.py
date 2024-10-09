import os.path
from pypdf import PdfReader
import asyncio
from typing import List


def get_worker(document_path: str):
    if not os.path.isfile(document_path):
        raise Exception(f'no such file exists: {document_path}')
    if document_path.split('.')[-1] != 'pdf':
        raise Exception(f'invalid file type - {document_path}; should be \'pdf\'')
    try:
        reader = PdfReader(document_path)
    except Exception as e:
        raise Exception(f'Unexpected exception: {str(e)}')

    return reader


async def extract_text(document_path: str) -> List[str]:
    pdf_worker = get_worker(document_path)

    async def extract_page_text(idx: int):
        loop = asyncio.get_running_loop()
        l = lambda idx: pdf_worker.pages[idx].extract_text().replace('\n','')

        return await loop.run_in_executor(None, l, idx)

    results = await asyncio.gather(*[extract_page_text(page) for page in range(len(pdf_worker.pages))],
                                   return_exceptions=True)
    return list(results)
