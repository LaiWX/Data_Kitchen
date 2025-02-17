import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from .config import ConfigManager

# Disable InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class FileItem:
    name: str
    is_directory: bool
    size: str
    modified_date: datetime
    url: str

class NetworkManager:
    def __init__(self):
        self.config = ConfigManager()
        self.session = requests.Session()
        self.session.verify = False
        self._update_auth()

    def _update_auth(self):
        """Update session headers with current auth credentials"""
        headers = self.config.get_auth_header()
        if headers:
            self.session.headers.update(headers)
        else:
            # Remove auth header if no credentials
            self.session.headers.pop('Authorization', None)

    def set_credentials(self, username: str, password: str):
        """Set new credentials and update session"""
        self.config.set_credentials(username, password)
        self._update_auth()

    def list_directory(self, url: str) -> List[FileItem]:
        if not url.endswith('/'):
            url += '/'
            
        response = self.session.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        file_list = soup.find('table', id='list').find('tbody').find_all('tr')
        
        items = []
        for file in file_list:
            link_tag = file.find('td', class_='link').find('a')
            if not link_tag or link_tag['href'] == "../":
                continue
                
            link = link_tag['href']
            name = link_tag.get('title', link)
            is_directory = link.endswith('/')
            
            # Get size and date from other columns
            columns = file.find_all('td')
            size = columns[1].text.strip() if len(columns) > 1 else ''
            date_str = columns[2].text.strip() if len(columns) > 2 else ''
            
            try:
                modified_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            except:
                modified_date = datetime.now()
                
            file_url = urljoin(url, link)
            
            items.append(FileItem(
                name=name,
                is_directory=is_directory,
                size=size,
                modified_date=modified_date,
                url=file_url
            ))
            
        return items

    def download_file(self, url: str, callback=None) -> requests.Response:
        """
        Download a file and return the response object
        callback: Optional function to receive download progress updates
        """
        response = self.session.get(url, stream=True)
        response.raise_for_status()
        return response 