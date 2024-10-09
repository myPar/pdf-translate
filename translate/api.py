import asyncio
import os.path

import httpx
import json
from typing import List
from . import client
import datetime
from .cloud_api import get_cloud_id, get_folder_id, set_resource_editor, ResourceType

base_dir = './translate'
PARTITION_SIZE = 20

async def get_api_key() -> dict:
    with open(os.path.join(base_dir, 'oauth_key'), 'r') as f:
        oauth_key = f.read()
    if oauth_key == "":
        raise Exception('no oauth key provided')
    data = {"yandexPassportOauthToken": oauth_key}
    try:
        response = await client.post(url='https://iam.api.cloud.yandex.net/iam/v1/tokens', json=data)
        response.raise_for_status()
        print(f'get api key response code={response.status_code}')
    except httpx.HTTPStatusError as e:
        raise Exception(f'(get api key) error response: status={e.response.status_code}; {repr(e)}')
    except httpx.RequestError as e:
        raise Exception(f'(get api key) request error: {str(e)}')

    return json.loads(response.content)


def key_expired(expiration_string: str):
    utc_now = datetime.datetime.utcnow().astimezone(tz=datetime.timezone.utc)
    expiration_datetime = datetime.datetime.fromisoformat(expiration_string)

    return utc_now > expiration_datetime


async def translate_api_request(text: str, target_language: str, api_token, folder_id: str) -> str:
    body = {
        "targetLanguageCode": target_language,
        "texts": [text],
        "folderId": folder_id,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }
    try:
        response = await client.post(url='https://translate.api.cloud.yandex.net/translate/v2/translate',
                                     json=body,
                                     headers=headers
                                     )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise Exception(f'(translate) error response: status={e.response.status_code}; {e.response.content}')
    except httpx.RequestError as e:
        raise Exception(f'(translate) request error: {str(e)}')
    json_data = json.loads(response.content)
    translation = json_data['translations'][0]

    return translation['text']

async def translate(pages: List[str], user_login: str, target_language: str='ru') -> List[str]:
    print('reading api key...')

    # read api key
    with open(os.path.join(base_dir, 'api_key'), 'r') as f:
        api_token = f.read()
        if api_token != '':
            try:
                # parse api token:
                api_token = json.loads(api_token)
                assert api_token['iamToken'] is not None
                assert datetime.datetime.fromisoformat(api_token['expiresAt']) is not None
            except Exception as e:
                print(f'invalid api token')
                api_token=''
        else:
            print('no api token found')

    if api_token == '' or key_expired(api_token['expiresAt']):
        if not api_token == '':
            print(f'api key={api_token} is expired')
        print('getting new api key...')

        response = await get_api_key()
        # write token to file
        with open(os.path.join(base_dir, 'api_key'), 'w') as f:
            json.dump(response, f)
        print('new api key is successfully written to file')

        api_token = response
    print(f'api key={api_token}')

    # configure cloud:
    cloud_id = await get_cloud_id(api_token['iamToken'])
    await set_resource_editor(api_token=api_token['iamToken'],
                              user_login=user_login,
                              resource_id=cloud_id,
                              resource_type=ResourceType.CLOUD)
    print(f'cloud {cloud_id} is configured')

    folder_id = await get_folder_id(cloud_id, api_token=api_token['iamToken'])
    await set_resource_editor(api_token=api_token['iamToken'],
                              user_login=user_login,
                              resource_id=folder_id,
                              resource_type=ResourceType.FOLDER)
    print(f'folder {folder_id} is configured')

    # translate each page concurrently (send up to 20 pages at one time)
    size = PARTITION_SIZE
    partitions_count = len(pages) // size + (1 if len(pages) % size != 0 else 0)
    partitions = [pages[i * size: min(i * size + size, len(pages))] for i in range(partitions_count)]
    results = []

    for partition in partitions:
        coros = [translate_api_request(page, target_language, api_token['iamToken'], folder_id) for page in partition]
        partition_result = await asyncio.gather(*coros,
                                                return_exceptions=True
                                                )
        results += list(partition_result)
        await asyncio.sleep(1)
    return results
