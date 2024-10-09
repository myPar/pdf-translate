import asyncio
import os.path
import sys
from translate.api import translate
from pdf_worker.worker import extract_text
import argparse
from typing import List
from translate import client


# prints exceptions and returns list of non-excepiton results
def handle_parallel_coro_results(results: List[str | Exception], descriptions: List[str]):
    filter_exceptions = lambda x: not isinstance(x, Exception)

    for i,res in enumerate(results):
        if isinstance(res, Exception):
            print(f'exception at {descriptions[i]}: {str(res)}', file=sys.stderr)

    return list(filter(filter_exceptions, results))


def save_translation(text: List[str], dst_dir: str):
    if dst_dir is None or not os.path.isdir(dst_dir):
        dst_dir = './'    # just save to file in the current dir
    with open(dst_dir + 'result.txt', 'w', encoding="utf-8") as f:
        for i in range(len(text)):
            f.write(text[i] + "\n" + "-"*10 + "page " + str(i + 1) + "-"*10 + "\n")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', type=str, required=True,
                        help='source dir of pdf file to translate text from')
    parser.add_argument('-dst', '--destination', type=str, default=None, required=False,
                        help='(optional) directory to store translate result, default is the directory of the script')
    parser.add_argument('-lan', '--language', type=str, default='ru', required=False,
                        help='(optional) language to translate pdf document to, default is \'Russian\'')
    parser.add_argument('-log', '--login', type=str, required=True,
                        help='login for your yandex account')
    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        return
    try:
        print('extracting the pages...')
        pages: List[str | Exception] = await extract_text(args.source)
        print(f'total pages={len(pages)}')
        descriptions = [f'parsing page {i}' for i in range(len(pages))]
        pages = handle_parallel_coro_results(pages, descriptions)

        print('translating the pages...')
        result: List[str | Exception] = await translate(pages, user_login=args.login, target_language=args.language)
        descriptions = [f'translating page {i}' for i in range(len(result))]
        result = handle_parallel_coro_results(result, descriptions)
        print('translated')
        save_translation(result, args.destination)
        print('translation is saved')
    except Exception as e:
        print(f'{str(e)}', file=sys.stderr)
    finally:
        await client.aclose()


if __name__ == '__main__':
    with asyncio.Runner() as runner:
        runner.run(main())