import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class VayesUploader:
    def __init__(self, base_url, warm_session=True):
        self.base_url = base_url.rstrip("/").replace("www.", "")  # Force non-www canonical
        self.session = requests.Session()
        
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        
        # Full header stack to match your dump—browser-like AF
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en;q=0.5",  # Matches your dump
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Gpc": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Priority": "u=0, i",
            "Connection": "keep-alive",  # requests sets this anyway, but explicit
        })
        
        # self.session.verify = False #### REMOVE LATER
        self.session_id = None
        self.csrf_vayes_cookie = None
        self.logged_in = False
        
        if warm_session:
            self._warm_session()
        print("Init locked in—session live.")

    def _warm_session(self):
        cp_url = f"{self.base_url}/admin/system_access"
        response = self.session.get(cp_url)

        # print(response)
        # with open('test.txt','w') as f:
        #     f.write(f"{response.content}\n\n\n\n\n\n\n{dict(response.headers)}")
        if response.status_code == 200 or response.status_code == 301:
            self.csrf_vayes_cookie = response.cookies.get("csrf_vayes_cookie")
            if self.csrf_vayes_cookie:
                print(f"Cookie grabbed: {self.csrf_vayes_cookie[:20]}...")
            else:
                print("csrf_vayes_cookie MIA—double-check Set-Cookie in headers.")

            self.session_id = response.cookies.get("vayes_session")
            if self.session_id:
                print(f"Cookie grabbed: {self.session_id[:20]}...")
            else:
                print("vayes_session MIA—double-check Set-Cookie in headers.")
        else:
            print(f"/cp warm-up failed: {response.status_code}")



    def refresh_cookies(self, response):
        """Sip new cookies from response, update self."""
        if response.status_code != 200:
            print(f"Skipping refresh on non-200: {response.status_code}")
            return
        
        # print(response.headers)
        # with open('test2.txt','w') as f:
        #     f.write(f"{response.headers}")
        new_cookies = dict(response.cookies)  # Jar as dict for easy peek
        print(response.cookies, "\n\n\n")
        print("AAAAAA",new_cookies)
        updated = False
        
        # CSRF check/swap
        new_csrf = new_cookies.get('csrf_vayes_cookie')
        if new_csrf and new_csrf != self.csrf_vayes_cookie:
            old_csrf = self.csrf_vayes_cookie
            self.csrf_vayes_cookie = new_csrf
            print(f"CSRF flipped: {old_csrf}... -> {new_csrf}...")
            updated = True
        
        # Session check/swap
        new_session = new_cookies.get('vayes_session')
        if new_session and new_session != self.session_id:
            old_session = self.session_id
            self.session_id = new_session
            print(f"Session rotated: {old_session}... -> {new_session}...")
            updated = True
        
        if not updated:
            print("Cookies steady—no swaps needed.")
        else:
            print(f"Post-refresh state: CSRF={self.csrf_vayes_cookie}..., Session={self.session_id}...")

    def login(self,username, password):
        if not self.csrf_vayes_cookie:
            print("Missing csrf_vayes_cookie—run warm_session?")
            self.logged_in = False
            return False
        
        login_url = f"{self.base_url}/admin/system_access"  # Confirm this is the POST endpoint
        login_data = {
            'csrf_vayes': self.csrf_vayes_cookie,
            'username': username,
            'password': password,
            'submit': 'Oturum Aç'
        }
        response = self.session.post(login_url, data=login_data)  # Now hits a real session
        self.refresh_cookies(response)
        
        if response.status_code == 200 or response.status_code ==  301 or response.status_code == 302:  # Broader success sniff
            if self.session_id:
                print(f"Auth sealed: session_id={self.session_id}...")
            else:
                print("Session ID hunt empty—peek response.cookies.")
            self.logged_in = True
            return True
        print(f"Login rejected: {response.status_code} | Body: {response.text[:300]}")
        self.logged_in = False
        return False
    
    #Testising
    def upload_article(self, **parameters):
        if not self.logged_in:
            return False
            
        if not self.csrf_vayes_cookie:
            print("No csrf_vayes—refresh cookies?")
            return False
            
        manage_url = f"{self.base_url}/admin/article/manage/{parameters['id_article']}"
        get_resp = self.session.get(manage_url)  # Fixed typo from gget_resp
        print(f"GET manage status: {get_resp.status_code} | Final URL: {get_resp.url}")
        if get_resp.status_code != 200 or "Oturum Aç" in get_resp.text or "login-form" in get_resp.text:
            print("Auth failed—GET to manage hit login page. Login didn't stick.")
            return False

        # Dynamic Referer: point back to the GET we just did
        self.session.headers["Referer"] = get_resp.url
        self.session.headers["Origin"] = self.base_url  # Static origin
        
        parameters['csrf_vayes'] = self.csrf_vayes_cookie
        
        response = self.session.post(manage_url, data=parameters)  # No manual cookies—session handles
        print("Cookies sent:", dict(self.session.cookies))  # Debug peek
        
        # print(response.headers)
        # with open('test2.txt','w') as f:
        #     f.write(f"{dict(response.headers)}\n\n\n{response.text}")
        self.refresh_cookies(response)
        
        if response.status_code == 200:
            print(f"Uploaded no sweat.")
            return True
        print(f"Upload failed: {response.status_code} | {response.text[:400]}")
        return False


if __name__ == "__main__":
    uploader = VayesUploader(base_url="https://mobilapp.vayes.com.tr")
    success = uploader.login(username="arda_durak", password="YWDCHMUIH9wiXvcb")
    print(f"Login: {success}, Session ID: {uploader.session_id}...")

    # uploadSomePost = uploader.upload_article(
    #     id_article = 0,
    #     id_page = 6,
    #     price = '',
    #     title_tr = "Arda blog post deneme 4",
    #     subtitle_tr = '',
    #     url_tr = "arda-blog-ama-post-deneme-4",
    #     meta_title_tr = '',
    #     summary_tr = '',
    #     content_tr = "<h3>içindekiler 4</h3><ul><li>test html</li><li>test html4</li></ul><p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi utx<span class="Renk--Metin-Antrasit"><strong> aliquip ex ea commodo</strong> </span>consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>",
    #     videolar_tr = '',
    #     schema_soru_tr = '',
    #     schema_cevap_tr = '',
    #     title_en = "Arda blog post deneme 4",
    #     subtitle_en = '',
    #     url_en = "arda-blog-post-deneme-4",
    #     meta_title_en = '',
    #     summary_en = '',
    #     content_en = "<h3>içindekiler 4</h3><ul><li>test html</li><li>test html4</li></ul><p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi utx<span class="Renk--Metin-Antrasit"><strong> aliquip ex ea commodo</strong> </span>consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>",
    #     videolar_en = '',
    #     schema_soru_en = '',
    #     schema_cevap_en = '',
    #     submit = 'Kaydet',
    #     base_image = '',
    #     logical_date = '',
    #     publish_on = '',
    #     publish_off = '',
    #     meta_description_tr = "meta desc test",
    #     meta_keywords_tr = "meta,keywords,türkçe",
    #     meta_description_en = "a meta desc ",
    #     meta_keywords_en = "meta,keyword,english",
    #     ordering = '',
    #     is_indexed = 1,
    # )


    example_data = {
        "id_article": 0,
        "id_page": 6,
        "price": "",
        "title[tr]": "Arda blog post deneme 7",
        "subtitle[tr]": "",
        "url[tr]": "test-arda-blog-post-deneme-7",
        "meta_title[tr]": "",
        "summary[tr]": "",
        "content[tr]": "<h3>içindekiler 7</h3><ul><li>test html</li><li>test html7</li></ul><p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi utx<span class=\"Renk--Metin-Antrasit\"><strong> aliquip ex ea commodo</strong> </span>consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>",
        "videolar[tr]": "",
        "schema-soru[tr]": "",
        "schema-cevap[tr]": "",
        "title[en]": "Arda blog post deneme 7",
        "subtitle[en]": "",
        "url[en]": "arda-blog-post-deneme-7",
        "meta_title[en]": "",
        "summary[en]": "",
        "content[en]": "<h3>içindekiler 7</h3><ul><li>test html</li><li>test html4</li></ul><p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi utx<span class=\"Renk--Metin-Antrasit\"><strong> aliquip ex ea commodo</strong> </span>consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>",
        "videolar[en]": "",
        "schema-soru[en]": "",
        "schema-cevap[en]": "",
        "submit": "Kaydet",
        "base_image": "",
        "logical_date": "",
        "publish_on": "",
        "publish_off": "",
        "meta_description[tr]":  "meta desc test",
        "meta_keywords[tr]": "meta,keywords,türkçe",
        "meta_description[en]":  "a meta desc",
        "meta_keywords[en]": "meta,keywords,english",
        "ordering": "",
        "is_indexed": 1,
    }

    
    uploadAPost = uploader.upload_article(**example_data)

    print(f"Done:{uploadAPost}")

"""
What is Laser Wrinkle Treatment? How is it done?
What is Laser Skin Rejuvenation? How is it done?
Tattoo Removal Treatment and Prices
"""