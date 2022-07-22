import requests
import json
from http import HTTPStatus
host_url = 'http://localhost:8000'

def download_metadata() -> dict:
    #fetch metadata json
    response = requests.get(host_url + '/metadata.json')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    return response.json() 

