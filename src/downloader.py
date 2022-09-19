
# full datasets are broken into different versions and image_qualities
# Each combination is given a separate URL
# eg.   version = 1.0, 1.1, 1.2, 2.0
#       image_quality = HD, ORIGINAL
#       host_url = https://downloads.host.com/v1_1/HD/, https://downloads.host.com/v2_0/ORIGINAL/

import requests
import json
from http import HTTPStatus
class Downloader:
    def __init__(self, host_url: str) -> None:
        self.host_url = host_url

    def download_metadata(self) -> dict:
        #fetch metadata json
        response = requests.get(self.host_url + '/metadata.json')
        assert response.status_code == HTTPStatus.OK
        assert response.headers['Content-Type'] == 'application/json'
        return response.json()
