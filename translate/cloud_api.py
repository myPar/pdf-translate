from . import client
import json
import httpx
from enum import Enum


base_dir = 'translate'


class ResourceType(str, Enum):
    FOLDER = 'folders'
    CLOUD='clouds'


def get_headers(api_token: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }
    return headers


async def get_cloud_id(api_token: str) -> str:
    try:
        response = await client.get(url='https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds',
                                    headers={"Authorization": f"Bearer {api_token}"}
                                   )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise Exception(f'(get cloud id) error response: status={e.response.status_code}; {repr(e)}')
    except httpx.RequestError as e:
        raise Exception(f'(get cloud id) request error: {str(e)}')
    json_data = json.loads(response.content)
    cloud_data = json_data['clouds'][0]

    return cloud_data['id']


async def get_user_id(api_token: str, user_login: str):
    try:
        response = await client.get(url='https://iam.api.cloud.yandex.net/iam/v1/yandexPassportUserAccounts:byLogin?login=' + user_login,
                                    headers={"Authorization": f"Bearer {api_token}"}
                                   )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise Exception(f'(get user id) error response: status={e.response.status_code}; {repr(e)}')
    except httpx.RequestError as e:
        raise Exception(f'(get user id) request error: {str(e)}')
    json_data = json.loads(response.content)

    return json_data['id']


async def set_resource_editor(resource_id: str, resource_type: ResourceType, api_token: str, user_login: str):
    user_id = await get_user_id(api_token, user_login)

    body = {"accessBindingDeltas":
                [{
                    "action": "ADD",
                    "accessBinding":
                    {
                        "roleId": "ai.editor",
                        "subject": {
                            "id": user_id,
                            "type": "userAccount"
                        }
                    }
                }]
            }
    url = f'https://resource-manager.api.cloud.yandex.net/resource-manager/v1/{resource_type.value}/{resource_id}:updateAccessBindings'
    try:
        response = await client.post(headers=get_headers(api_token), url=url, json=body)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise Exception(f'({resource_type.value} editor) error response: status={e.response.status_code}; {repr(e)}')
    except httpx.RequestError as e:
        raise Exception(f'({resource_type.value} editor) request error: {str(e)}')


async def get_folder_id(cloud_id: str, api_token: str) -> str:
    url='https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders'
    try:
        response = await client.get(headers={"Authorization": f"Bearer {api_token}"}, url=url, params={'cloudId': cloud_id})
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise Exception(f'(get folder id) error response: status={e.response.status_code}; {repr(e)}')
    except httpx.RequestError as e:
        raise Exception(f'(get folder id) request error: {str(e)}')
    json_data = json.loads(response.content)
    folder = json_data['folders'][0]

    return folder['id']
