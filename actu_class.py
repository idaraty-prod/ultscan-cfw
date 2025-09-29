'''
# Using temporary Actu PYTHON library
'''
from pprint import pprint

import htmlmin
import inspect
import csv
import glob
import os
import re
import pandas as pd
import numpy as np
import requests
from termcolor import colored
from tqdm import tqdm
from bs4 import BeautifulSoup
import urllib
from urllib.parse import urlparse
from urllib.parse import quote
from dateutil import parser
from parsel import Selector
from validator_collection import checkers
from PIL import Image
import datetime
from slugify import slugify
from pathlib import Path
import random
import string
from matcher_utils import MatcherClass
from py_analytics import PyAnalyticsClass
from urllib.parse import urlencode

from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Remove warning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


__all__ = ("ActuClass",)

class ActuClass:
    def __init__(
        self,
        *,
        config_dir: str = '',
        db_post_models_csv: str = '',
        db_already_processed_posts_csv: str = '',
        db_already_processed_images_csv: str = '',
        db_already_processed_publications_csv: str = '',
        db_storage_csv: str = '',
        db_storage_image: str = '',
        should_save_image: bool = True,
        should_use_same_session: bool = False,
        # keep_html: bool = False, # should remove html tags from text?
        test_model = False,
        debug_mode = False, # should debug test_model
        debug_info = False, # should display processing information
        is_deep_scan_mode = True, # should scan all pages
        default_pagination_limit = 3, # pagination limit if is_deep_scan_mode = false

        # analytic params
        enable_analytics: bool = False,
        tracking_id: str = 'MO-XXXXX-X',
        tracking_domain: str = 'yourdomain.com',
    ):
        current_script_path = inspect.getfile(self.__class__).replace('actu_class.py', '')
        # print('current_script_path')
        # print(current_script_path)

        defaults = {
            'db_post_models_csv': 'configs/post_models.csv',
            'db_already_processed_posts_csv': 'configs/processed_posts_urls.csv',
            'db_already_processed_images_csv': 'configs/processed_images_urls.csv',
            'db_already_processed_publications_csv': 'configs/processed_publications_urls.csv',
            'db_storage_csv': 'outputs/posts/',
            'db_storage_image': 'outputs/images/',
        }

        db_post_models_csv = current_script_path + defaults['db_post_models_csv'] if db_post_models_csv == '' else db_post_models_csv
        db_already_processed_posts_csv = current_script_path + defaults['db_already_processed_posts_csv'] if db_already_processed_posts_csv == '' else db_already_processed_posts_csv
        db_already_processed_images_csv = current_script_path + defaults['db_already_processed_images_csv'] if db_already_processed_images_csv == '' else db_already_processed_images_csv
        db_already_processed_publications_csv = current_script_path + defaults['db_already_processed_publications_csv'] if db_already_processed_publications_csv == '' else db_already_processed_publications_csv
        db_storage_csv = current_script_path + defaults['db_storage_csv'] if db_storage_csv == '' else db_storage_csv
        db_storage_image = current_script_path + defaults['db_storage_image'] if db_storage_image == '' else db_storage_image

        self._should_use_same_session = should_use_same_session
        self._should_save_image = should_save_image
        self._test_model = test_model
        self._db_storage_csv = db_storage_csv
        self._db_storage_image = db_storage_image
        self._db_post_models_csv = db_post_models_csv
        self._db_already_processed_posts_csv = db_already_processed_posts_csv
        self._db_already_processed_images_csv = db_already_processed_images_csv
        self._db_already_processed_publications_csv = db_already_processed_publications_csv
        self._debug_mode = debug_mode
        self._debug_info = debug_info
        self._is_deep_scan_mode = is_deep_scan_mode
        self._default_pagination = default_pagination_limit

        '''
        # Load config and history
        '''
        if debug_mode:
            self._post_models = pd.DataFrame([test_model])
        else:
            self._post_models = self.load_csv(db_post_models_csv, pandas=True)
        # print(self._post_models)
        # exit()
        self._post_models_header = self._post_models.head()

        all_publications_urls = self.load_csv(db_already_processed_publications_csv, ',')
        # Flatten the array
        self._all_publications_urls = [item for sublist in all_publications_urls for item in sublist]

        all_post_urls = self.load_csv(db_already_processed_posts_csv, ',')
        # Flatten the array
        self._all_post_urls = [item for sublist in all_post_urls for item in sublist]

        all_image_urls = self.load_csv(db_already_processed_images_csv, ',')
        # Flatten the array
        self._all_image_urls = [item for sublist in all_image_urls for item in sublist]

        # print('self._post_models')
        # print(self._post_models)

        self._new_posts = []
        self._headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_7 rv:5.0; IT) AppleWebKit/533.1.2 (KHTML, like Gecko) Version/7.0.8 Safari/533.1.2",
            # "Host": "news.tunisiatv.tn",
            # "Referer": "http://news.tunisiatv.tn",
        }

        if should_use_same_session:
            self.session = requests.Session()
            self.session.headers.update(self._headers)


        # load matcher
        self.matcher = MatcherClass(config_dir=config_dir)

        # load analytics tracker
        self.enable_analytics = enable_analytics
        self.tracker = None
        if enable_analytics:
            self.tracker = PyAnalyticsClass(tracking_id=tracking_id, tracking_domain=tracking_domain)
        

    def get_should_save_image(self):
        """
        Returns current should_save_image
        """
        return self._should_save_image

    def get_random_string(self, length):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    def url_encode(self, url):
        return urllib.parse.quote(url)

    def get_domain_from_url(self, url):
        return urlparse(url).netloc

    def get_protocol_from_url(self, url):
        return urlparse(url).scheme

    def get_extension_from_url(self, url):
        path = urlparse(url).path
        return os.path.splitext(path)[1]

    def is_valid_url(self, url):
        return checkers.is_url(url)


    def remove_urls_from_text(self, text):
        return re.sub(r'^https?:\/\/.*[\r\n]*', '', text, flags=re.MULTILINE)

    def get_protocol_host_from_url(self, url):
        parsed_uri = urlparse(url)
        return '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)

    def get_now_str(self):
        dateTimeObj = datetime.datetime.now()
        # return time.ctime()
        return dateTimeObj.strftime("%Y-%m-%d %H:%M:%S")

    def get_now_timestamp(self):
        now = datetime.datetime.now()
        timestamp = (now - datetime.datetime(1970, 1, 1)).total_seconds()
        return int(timestamp)

    def is_file_exists(self, fl):
        return os.path.exists(fl)

    def extract_urls(self, text):
        regex = "(?P<url>https?://[^\s]+)"
        return re.findall(regex, text)

    def extract_urls_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        anchors = soup.find_all('a')
        all_links = []
        for link in anchors:
            if(link.get('href') != '#'): 
                linkText = str(link.get('href'))
                all_links.append(linkText)
        return all_links

    def image_resize(self, image_path, mywidth):
        img = Image.open(image_path)
        wpercent = (mywidth/float(img.size[0]))
        hsize = int((float(img.size[1])*float(wpercent)))
        img = img.resize((mywidth, hsize), PIL.Image.ANTIALIAS)
        return img.save(image_path)


    def file_size_kb(self, file_path):
        """
        this function will return the file size in Kb
        """
        if os.path.isfile(file_path):
            file_info = os.stat(file_path)
            return file_info.st_size / 1024
        return 0


    # Check if image fits criteria:
    # > 10Ko: remove
    # resize > 980ko ?
    def filter_cover_image(self, image_path):
        # try:
        size = self.file_size_kb(image_path)
        try:
            image = Image.open(image_path)
        except:
            return False
        width, height = image.size
        # print('filter_cover_image - size ' + str(size))
        # print('image width ' + str(width))
        # print('image height ' + str(height))
        # print('-------')
        if (width < 205 and height < 205):
        # if size < 9 or (width < 200 and height < 200):
        # if size < 9:
            os.remove(image_path)
            return False
        return True
        # except:
        #     print('filter_cover_image ERROR: ' + str(image_path))
        #     return False


    def get_session(self):
        if self._should_use_same_session:
            return self.session
        return requests

    def save_csv(self, csv_file, output):
        df = pd.DataFrame(output)
        df.to_csv(csv_file, index=None, mode='a', quoting=csv.QUOTE_ALL)

    def load_csv(self, csv_file, delimiter=';', pandas=False):
        if pandas:
            tmp = pd.read_csv(csv_file)
            return tmp

        results = []
        with open(csv_file) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            for row in reader:  # each row is a list
                results.append(row)
        return results

    def extract_new_posts(self):
        totalModels = len(self._post_models)
        newPosts = []
        for i in range(len(self._post_models)):
            model = self._post_models.iloc[i]
            model = dict(zip(self._post_models_header, model))
            model['loop_end'] = model['loop_end'] if self._is_deep_scan_mode else self._default_pagination
            print('#######################################')
            print('Processing #' + str(i+1) + ' / ' + str(totalModels) + ' - ' + model['batch_id'] + '...')
            if self.enable_analytics:
                self.tracker.track_pageview('/extract_batch/' + str(model['batch_id']))
            postsLinks = self.get_posts_from_pagination(model)
            if self._debug_mode and not self._is_deep_scan_mode:
                print('postsLinks')
                pprint(postsLinks)
                # exit()
            # print(postsLinks)

            if self._debug_info:
                total_pages = model['loop_end'] if ('loop_end' in model and model['loop_end']) else 'N/A'
                print("Got " + str(len(postsLinks)) + " from " + str(total_pages) + " pages")
                print('------')
            index = 1
            for link in tqdm(postsLinks):
                # Check if post is already processed
                # print("Checking " + str(index) + " / " + str(len(postsLinks)) + " ...")
                url = link['link']
                if (url and not url in self._all_post_urls):
                    # print("Processing " + str(url) + " ...")
                    post = self.get_actu_from_link(link, model)
                    if self._debug_mode and not self._is_deep_scan_mode:
                        print('post')
                        pprint(post)
                        exit()
                    
                    if post and post['slug'] and post['slug'] != '':
                        newPosts.append(post)
                        if 'sources' in post and not post['sources'] == '':
                            self._all_post_urls.append(post['sources'])
                    else:
                        print('@@@@@@@@@@@@@@@@@@')
                        print('Post Export Issue !')
                        print(url)
                        print(post)
                        print('@@@@@@@@@@@@@@@@@@')
                else:
                    if url:
                        print(str(url) + ' was already processed')
                    else:
                        print(colored(str(url) + 'URL was not found !', 'red'))

                # print('-------------')
                index += 1
        
        self._new_posts = newPosts

        return newPosts


    def load_all_posts(self):
        csv_all_posts = glob.glob(self._db_storage_csv+'*.csv')
        posts = pd.concat(map(pd.read_csv, csv_all_posts))
        posts = posts.replace(np.nan, '', regex=True)
        return posts

    '''
    # @TODO
    Extract tagged items in a new csv file
    '''
    def tag_all_posts(self, newPosts=False):
        if not newPosts:
            newPosts = self.load_all_posts()

        # extract orgs from each post
        newPosts = pd.DataFrame(newPosts)
        # print(newPosts)
        newPosts['tagged_orgs'] = newPosts[['content_ar', 'content_fr']].progress_apply(self.matcher.add_org_slugs_exact, axis=1)
        newPosts['final_org_tags'] = newPosts[['organizations', 'tagged_orgs']].progress_apply(self.matcher.combine_tags, axis=1)
        newPosts['organizations'] = newPosts['final_org_tags']
        newPosts = newPosts.assign(organizations=newPosts['final_org_tags'])
        # print(newPosts)


    def save_new_items(self):
        # Save exported posts for today
        print('Save exported posts for today...')
        newPosts = pd.DataFrame(self._new_posts)

        if len(newPosts.columns) == 0:
            print(colored('No new items found !', 'yellow'))
            return False

        latest_posts = self._db_storage_csv + '/posts-' + str(self.get_now_timestamp())+'.csv'
        newPosts = newPosts[["slug","title_en","title_fr","title_ar","excerpt_en","excerpt_fr","excerpt_ar","tags","sources", "source_url", "apply_url","image_url","image_name","langs","published_at","extracted_at","deadline","rubrique_website","themes","organizations","eligibility_criteria","content_en","content_fr","content_ar","content_html"]]
        newPosts.to_csv(latest_posts, index=None, mode='a', quoting=csv.QUOTE_ALL)

        print('# Saved to ' + latest_posts)
        print('# Added ' + str(len(newPosts)) + ' new posts')


    '''
    # @TODO
    # - check unique posts urls
    # - save publications duplicates ?
    '''
    def save_already_processed_items(self):
        print('Save all post urls (avoid duplications)...')
        ######
        # input form self._all_post_urls ??
        ######
        # newPostsId = [p['sources'] for p in self._new_posts]
        # exclude 'mtcen.gov.tn' because it has not valid temp urls
        newPostsId = [urllib.parse.unquote(p['sources']) if not 'mtcen.gov.tn' in p['sources'] else p['sources'] for p in self._new_posts]
        allPostsUrls = newPostsId  # CSV open mode = a (add to file)
        all_processed_posts = self._db_already_processed_posts_csv
        self.save_csv(all_processed_posts, allPostsUrls)
        print('# Saved to ' + all_processed_posts)

        # Save all publications urls (avoid duplications)
        print('Save all publications urls (avoid duplications)...')
        all_processed_publications = self._db_already_processed_publications_csv
        self.save_csv(all_processed_publications, self._all_publications_urls)
        print('# Saved to ' + all_processed_publications)

        print('Save all image urls (avoid duplications)...')
        imagesUrls = [p['image_url'] for p in self._new_posts]
        all_processed_images = self._db_already_processed_images_csv
        self.save_csv(all_processed_images, imagesUrls)
        print('# Saved to ' + all_processed_images)

    def extract_posts_pagination_html(self, counter, model):
        single = model['page_actu_loop']
        url = single.replace('ACTU_NBR', str(int(counter)))
        # print(url)

        # req = self.get_session().get(url, headers=self._headers, verify=False, timeout=30, allow_redirects=True)
        try:
            req = self.get_session().get(
                url,
                headers=self._headers,
                verify=False,
                timeout=30,           # still enforce a reasonable timeout
                allow_redirects=True
            )
            req.raise_for_status()    # optional: catch HTTP 4xx/5xx
        except requests.exceptions.Timeout:
            print(f"Request timed out for {url}")
            req = None
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {url}: {e}")
            req = None
        
        if req:
            req.encoding = 'utf-8'
            html = req.text
            # print(html)
            return self.get_actu_articles_from_page(html, model)
        
        return []


    def extract_posts_pagination_api(self, counter, model):
        api_endpoint = model['api_endpoint']
        api_data = model['api_data']
        api_nbr_key = model['api_nbr_key']
        if not api_nbr_key in api_data:
            print(str(api_nbr_key) + ' not found in set api_data object !')
        api_data[api_nbr_key] = str(int(counter))

        # define request header
        headers = self._headers
        if ('api_header_accept' in model and model['api_header_accept']):
            headers['accept'] = model['api_header_accept']
        if ('api_header_accept_language' in model and model['api_header_accept_language']):
            headers['accept-language'] = model['api_header_accept_language']
        if ('api_header_content_type' in model and model['api_header_content_type']):
            headers['content-type'] = model['api_header_content_type']
        if ('api_header_request_with' in model and model['api_header_request_with']):
            headers['x-requested-with'] = model['api_header_request_with']
        # if ('api_header_origin' in model and model['api_header_origin']):
        #     headers['origin'] = model['api_header_origin']
        # if ('api_header_referer' in model and model['api_header_referer']):
        #     headers['referer'] = model['api_header_referer']
        if ('api_method' in model and model['api_method'] and model['api_method'].lower() in ['get', 'post']):
            method = model['api_method'].upper()
        
        # print('api_data')
        # print(headers)
        # print(api_data)

        if ('api_data_encode' in model and model['api_data_encode'] == True):
            api_data = urlencode(api_data)
        
        # print(api_data)

        # print(api_endpoint)
        # req = self.get_session().post(api_endpoint, headers=headers, data=api_data, verify=False, timeout=30, allow_redirects=True)
        req = self.get_session().request(method, api_endpoint, headers=headers, data=api_data, verify=False, timeout=30, allow_redirects=True)
        # print('req.text')
        # print(req)
        # print(req.text)
        req.encoding = 'utf-8'

        if ('api_result_type' in model and model['api_result_type'] == 'json'):
            result = req.json()
            result_key = model['api_result_key'] if 'api_result_key' in model else 'data'
            # print('result')
            # print(result)
            # print('result_key')
            # print(result_key)
            result = result[result_key]
            # print('result')
            # print(result)
        else:
            result = req.text

        items = result
        if ('api_loop_mode' in model and model['api_loop_mode'] == 'html'):
            # print('transform to html!')
            items = self.get_actu_articles_from_page(result, model)

        return items



        # print('articles')
    def get_posts_from_pagination(self, model):
        """
        Returns current posts_from_pagination
        """
        links = []

        # api / html / rss (future)
        extraction_mode = model['extraction_mode'] if ('extraction_mode' in model and model['extraction_mode'] and model['extraction_mode'] in ['html', 'api']) else 'html'

        start = model['loop_start'] if ('loop_start' in model and model['loop_start'] and model['loop_start'] >= 0) else 1
        step = model['loop_step'] if ('loop_step' in model and model['loop_step'] and model['loop_step'] > 1) else 1
        end = model['loop_end'] if ('loop_end' in model and model['loop_end'] and model['loop_end'] >= 1) else 10
        # print('step')
        # print(step)
        # print('end')
        # print((end*step))
        counter = start
        haveMore = True
        while counter <= (end*step) and haveMore:
            print('Processing page ' + str(int(counter)) + '/' + str(end) + '...')

            # try:
            if extraction_mode == 'html':
                articles = self.extract_posts_pagination_html(counter, model)
            if extraction_mode == 'api':
                articles = self.extract_posts_pagination_api(counter, model)

            if (articles and len(articles) > 0):
                links = links + articles
            else:
                haveMore = False
            # except:
            #     # haveMore = False
            #     print(colored('ISSUE at this URL: ' + url, 'red'))

            counter += step
            
        return links


    def get_actu_articles_from_page(self, html, model):
        result = False

        reg_ul = model['reg_ul']
        reg_li = model['reg_li']
        reg_li_a = model['reg_li_a'] if 'reg_li_a' in model and model['reg_li_a'] else False
        reg_li_title = model['reg_li_title'] if 'reg_li_title' in model and model['reg_li_title'] else False
        reg_li_date = model['reg_li_date'] if 'reg_li_date' in model and model['reg_li_date'] else False
        reg_li_image = model['reg_li_image'] if 'reg_li_image' in model and model['reg_li_image'] else False
        css = str(reg_ul) + ' ' + str(reg_li)
        # css = str(reg_ul) + ' ' + str(reg_li) + ' ' + str(reg_li_a)

        selector = Selector(text=str(html))
        all_links = selector.css(css)
        # print('all_links')
        # print(len(all_links))
        # exit()


        if all_links:
            if self._debug_mode:
                print('DEBUG MODE ON:')
                print('total posts:', str(len(all_links)))

            result = []
            for post in all_links:
                # print('post all links')
                # print(post.get())
                link = False
                hst = self.get_protocol_host_from_url(model['page_actu_loop'])
                ###### try:
                if 'tunisair.com.tn' in hst:
                    # post = link (Tunisiair very messy code)
                    link = post.attrib['href'] if reg_li_a else False

                # exit()
                # print(post)
                # print(post.css(reg_li_a))
                link = post.css(reg_li_a).attrib['href'] if not link and reg_li_a and 'href' in post.css(reg_li_a).attrib else link
                link = link if link else ''
                if link and not link == '' and not self.is_valid_url(link):
                    if (not link.startswith('/')):
                        link = '/'+link
                    # fix exception
                    if 'www.pm.gov.tn' in hst:
                        hst = hst + "/pm/actualites"
                    if 'tunisair.com.tn' in hst:
                        hst = hst + "/site/publish/content"

                    link = hst + link
                    
                    if 'enf.fin.tn' in hst:
                        if '../' in link:
                            link = link.replace('../', '')
                        else:
                            link = link.replace('/index', '/ar/index')

                    if 'intt.tn' in hst:
                        link = link.replace('/index', '/'+model['lang'].lower()+'/index')

                    # print('link')
                    # print(link)
                
                if self._debug_mode:
                    print('link')
                    print(link)
                    
                title = post.css(reg_li_title).get() if reg_li_title else False
                title = title if title else ''
                title = title.strip()
                
                image = post.css(reg_li_image).get() if reg_li_image else False
                # print('image')
                # print(image)
                image = image if image else False

                date = post.css(reg_li_date).get() if reg_li_date else False
                # print('date')
                # print(date)
                if date:
                    date = self.cleanDate(date, model['batch_id'])

                # check if link is already processed (monitoring mode only)
                isAleadyProcessed = not self._is_deep_scan_mode and (link and link in self._all_post_urls)

                if not isAleadyProcessed:
                    result.append({
                        'title': title,
                        'link': link,
                        'date': date if date else '',
                        'image': image,
                    })

                # except:
                #     print(colored('ISSUE when processing actu block', 'red'))


            # result = [link for link in all_links]
            # print(result)
        
        return result
        


    def get_actu_from_link(self, link, model):
        # retrieve data from exerpt
        url = link['link']
        date = link['date'] if 'date' in link and link['date'] else False
        image = link['image'] if 'image' in link and link['image'] else False
        # print('date')
        # print(date)
        # print('link')
        # print(link)
        # print('url')
        # print(url)
        # exit()

        # Send req
        req = False
        try:
            req = self.get_session().get(url, headers=self._headers, verify=False, timeout=30)
        except:
            req = False

        if not req:
            print(colored('Cant get URL: ' + str(url), 'red'))
            return False

        req.encoding = 'utf-8'
        # req.encoding = 'windows-1256'
        html = req.text
        # print(html)
        # print(html[:500])
        # exit()
        selector = Selector(text=str(html))

        # Process regexes
        page_actu_home = model['page_actu_home'] if 'page_actu_home' in model and model['page_actu_home'] else False
        single_title = model['single_title'] if 'single_title' in model and model['single_title'] else False
        single_content = model['single_content'] if 'single_content' in model and model['single_content'] else False
        single_date = model['single_date'] if 'single_date' in model and model['single_date'] else False
        single_image = model['single_image'] if 'single_image' in model and model['single_image'] else False
        single_tags = model['single_tags'] if 'single_tags' in model and model['single_tags'] else False
        deadline = model['deadline'] if 'deadline' in model and model['deadline'] else False
        apply_url = model['apply_url'] if 'apply_url' in model and model['apply_url'] else False
        eligibility_criteria = model['eligibility_criteria'] if 'eligibility_criteria' in model and model['eligibility_criteria'] else False
        
        title = selector.css(single_title).get() if single_title else False
        content = selector.css(single_content).get() if single_content else False
        if not date:
            date = selector.css(single_date).get() if single_date else False
        
        deadline = selector.css(deadline).get() if deadline else False
        if not deadline:
            deadline = date

        eligibility_criteria = selector.css(eligibility_criteria).get() if eligibility_criteria else False

        tags = selector.css(single_tags) if single_tags else False

        if not title and 'title' in link and link['title'] != '':
            title = link['title']

        # print('title')
        # print(title)
        # print('content')
        # print(content)
        # print(str(html))
        # head = selector.css('og:title').get()
        # print('date')
        # print(date)
        # exit()

        new = {
            "slug": "",
            "title_en": "",
            "title_fr": "",
            "title_ar": "",
            "rubrique_website": model['rubrique_website'] if 'rubrique_website' in model else '',
            "sources": "",
            "source_url": "",
            "apply_url": "",
            "image_name": "",
            "langs": "",
            "published_at": "",
            "deadline": "",
            'extracted_at': self.get_now_str(),
            "tags": "",
            "themes": "",
            "eligibility_criteria": "",
            "organizations": "",
            "content_en": "",
            "content_fr": "",
            "content_ar": "",
            "excerpt_en": "",
            "excerpt_fr": "",
            "excerpt_ar": "",
        }

        # print('url')
        # print(url)

        if url:
            new['source_url'] = url

        if eligibility_criteria:
            new['eligibility_criteria'] = eligibility_criteria

        if not content or not title:
            return False

        content = content.replace(' ', ' ')
        content = content.replace('  ', ' ')
        
        # keep content_html
        content_minified = htmlmin.minify(content, remove_comments=True, remove_empty_space=True)
        
        new['content_html'] = content_minified
            
        # clean up content
        # remove extra elements
        content = re.sub('<ul class="breadcrumb">.*?</ul>', '', content)
        content = self.cleanMe(content)
        # content = re.sub('<style type="text/css">*</style>', '', content)
        content = re.sub(
            '<div class="addthis_inline_share_toolbox".*?</ul>', '', content)
        content = re.sub('<div class="mainFig">.*?</div>', '', content)
        content = re.sub('<div class="share-links">.*?</div>', '', content)
        content = re.sub('<div class="atclear">.*?</div>', '', content)
        content = re.sub('<div class="addthis_toolbox">.*?</div>', '', content)
        content = re.sub('<figure class="wp-block-image size-large">.*?</figure>', '', content)

        # remove html tags
        cleanr = re.compile('<.*?>')
        content = re.sub(cleanr, '', content)
        

        content = re.sub('Facebook Twitter LinkedIn Whatsapp Share via Email Print', '', content)
        # print(content)

        lang = model['lang']
        new['langs'] = lang

        # Add title
        if (lang == 'AR'):
            new['title_ar'] = title.strip().replace('\t', '').replace('\n', '') if title else ''
        if (lang == 'FR'):
            new['title_fr'] = title.strip().replace('\t', '').replace('\n', '') if title else ''
        if (lang == 'EN'):
            new['title_en'] = title.strip().replace('\t', '').replace('\n', '') if title else ''
        
        # Add slug
        new['slug'] = slugify(new['title_' + str(lang).lower()])

        # Add context + excerpt
    
        new['content_' + str(lang).lower()] = content if content else ''
        # Remove leading and post spaces / new lines
        new['content_' + str(lang).lower()] = new['content_' + str(lang).lower()].strip()
        new['content_' + str(lang).lower()] = new['content_' + str(lang).lower()].strip('\n')
        new['content_' + str(lang).lower()] = new['content_' + str(lang).lower()].strip('\r')
        tmp_excerpt = self.remove_urls_from_text(new['content_' + str(lang).lower()])
        if (len(tmp_excerpt) > 150):
            new['excerpt_' + str(lang).lower()] = str(tmp_excerpt[:150]) + '...'
        else:
            new['excerpt_' + str(lang).lower()] = tmp_excerpt

        # Add image_name
        image_url = ''
        # print('image_url')
        if (single_image):
            image_url = selector.css(single_image).get() if single_image else False
        if (not image_url and image and (not image == '')):
            image_url = image
        # print(image_url)
        # Default to 'og:image'
        if (not image_url):
            soup = BeautifulSoup(req.text, "lxml")
            tmp = soup.find("meta",  property="og:image")
            if tmp:
                image_url = tmp['content']
        # print(image_url)

        
        if (model["batch_id"] in ['pm-ar', 'pm-fr'] and '../' in image_url):
            image_url = image_url.replace('../', 'http://www.pm.gov.tn/pm/')
        
        if (model["batch_id"] in ['onthemove-news'] and '/sites/default/' in image_url):
            image_url = image_url.replace('/sites/default/', 'https://on-the-move.org/sites/default/')


        # fix image_url with relative path
        if image_url and image_url.startswith('/'):
            image_url =  self.get_protocol_from_url(model['page_actu_home']) + '://' + self.get_domain_from_url(model['page_actu_home']) + image_url

        new['image_url'] = image_url
        if image_url and not image_url == '':
            ext = self.get_extension_from_url(image_url)
            slg = new['slug'] + ext
            local_file = self._db_storage_image + slg
            local_file = local_file.strip()
            slash = '/' if not image_url.startswith('/') else ''
            image_url = image_url if ('http' in image_url) else self.get_protocol_host_from_url(page_actu_home) + slash + image_url
            # print('local_file')
            # print(local_file)
            # print(image_url)

            self._all_image_urls.append(image_url)
            
            if self._should_save_image:
                downloaded = self.download_file(image_url, local_file, overwrite=False)
                if downloaded:
                    passed = self.filter_cover_image(local_file)
                    if passed:
                        new['image_name'] = slg

        # print('image_url')
        # print(image_url)

        if apply_url:
            # print(selector.css(apply_url).get())
            apply_url = selector.css(apply_url) if apply_url else False
            if apply_url and len(apply_url) > 0:
                if isinstance(apply_url, list):
                    apply_url = apply_url.pop()
                try:
                    new['apply_url'] = apply_url['href']
                except:
                    new['apply_url'] = apply_url.extract()

        # try and guess deadline Url
        if 'guess_apply_url_last_url' in model and model['guess_apply_url_last_url'] == True and (not new['apply_url'] or new['apply_url'] == '') and 'content_html' in new and new['content_html']:
            all_urls = self.extract_urls_html(new['content_html'])
            # print('guessing...')
            if all_urls and len(all_urls) > 0:
                all_urls = [u for u in all_urls if not 'www.addtoany.com' in u]
                if len(all_urls) > 0:
                    new['apply_url'] = all_urls.pop()
        

        if deadline:
            new['deadline'] = new['deadline'].replace('deadline:', '')
            new['deadline'] = deadline.rjust(8, '0')
            if ('deadline_format' in model and model['deadline_format']):
                deadline = self.cleanDate(new['deadline'], model['batch_id'])
                try:
                    dtmp = datetime.datetime.strptime(new['deadline'], model['deadline_format'])
                except:
                    try:
                        dtmp = self.cleanDate(new['deadline'], model['batch_id'])
                        # print('dtmp')
                        # print(dtmp)
                        dtmp = datetime.datetime.strptime(dtmp, model['deadline_format'])
                    except:
                        dtmp = False
                        if self._debug_mode:
                            print('Date extract Trial 2 failed (deadline) !')
                            print(new['deadline'])
                            print(dtmp)
                            print('------')
                if dtmp:
                    new['deadline'] = dtmp.strftime('%Y-%m-%d 23:59:00')
        
        # print('deadline')
        # print(new['deadline'])
        # exit()

        # Add published_at
        # print('date')
        # print(date)
        # exit()
        
        if date:
            if model['single_date_format']:
                if model['single_date_format'] == 'timestamp':
                    dtmp = datetime.datetime.fromtimestamp(int(date))
                    new['published_at'] = dtmp.strftime('%Y-%m-%d 08:00:00')
                else:
                    # Add 0 to left to match length (works for length = 8 for now)
                    new['published_at'] = date.rjust(8, '0')
                    # refs: http://strftime.org/
                    if ('single_date_format' in model and model['single_date_format']):
                        # print('---------')
                        # print(url)
                        # print(new['published_at'])
                        try:
                            date = self.cleanDate(new['published_at'], model['batch_id'])
                            dtmp = datetime.datetime.strptime(new['published_at'], model['single_date_format'])
                        except:
                            try:
                                dtmp = self.cleanDate(new['published_at'], model['batch_id'])
                                # print('dtmp')
                                # print(dtmp)
                                dtmp = datetime.datetime.strptime(dtmp, model['single_date_format'])

                            except:
                                dtmp = False
                                if self._debug_mode:
                                    print('Date extract Trial 2 failed (published_at) !')
                                    print(new['published_at'])

                        if dtmp:
                            # Desired date format
                            new['published_at'] = dtmp.strftime('%Y-%m-%d 08:00:00')
                    # print('---------')
        



        # print(new['published_at'])
            
        # Fix empty published date
        if ((not new['published_at'] or new['published_at'] == '') and image_url):
            # print(image_url)
            try:
                # extract from image EXIF
                r = urllib.request.Request(image_url)
                r.add_header("user-agent", self._headers["user-agent"])
                with urllib.request.urlopen(r) as f:
                    dtmp = False
                    # print(f.getheaders())
                    try:
                        hkeys = dict(f.getheaders())
                        if ('date' in hkeys):
                            dtmp = dict(f.getheaders())['date']
                        if ('Date' in hkeys):
                            dtmp = dict(f.getheaders())['Date']
                        if ('last-modified' in hkeys):
                            dtmp = dict(f.getheaders())['last-modified']
                        if ('Last-Modified' in hkeys):
                            dtmp = dict(f.getheaders())['Last-Modified']
                    except:
                        dtmp = False
                    if dtmp:
                        dtmp = parser.parse(dtmp)
                        if dtmp:
                            new['published_at'] = dtmp.strftime('%Y-%m-%d 08:00:00')
            except:
                print("Can't check exif for this file (", image_url, ")")
        
        # Add orgs
        if (model and 'orgs' in model and model['orgs']):
            new['organizations'] = model['orgs']
        
        # Add themes
        if (model and 'themes' in model and model['themes']):
            new['themes'] = model['themes']

        # Add tags
        if tags and len(tags) > 0:
            tags = [re.sub('<[^<]+?>', '', tag.get()) for tag in tags]
            tags = [tag.replace(';',',') for tag in tags]
            new['tags'] = ';'.join([tag for tag in tags])

        # Add sources
        if url:
            stmp = url
            # Prevent URL encoding for certain sources
            if (not model["batch_id"] in ['mini-technologie-ar', 'mini-technologie-fr', 'pm-ar', 'pm-fr']):
                stmp = quote(stmp)
                stmp = stmp.replace('%3A//', '://')
            new['sources'] = stmp

        # Add random post slug
        new['slug'] = str(new['slug']) + '-' + str(self.get_random_string(6))



        '''
        # process document
        1 - read document_url + document_title (if exists)
        2 - download documents to /tmp folder
        3 - rename the downloaded document

        Prepare the generation an importable csv resources

        slug: 'publication-post-' + slug of title + random
        title_ar (check document_title, default to same post name)
        title_fr (check document_title, default to same post name)
        title_en (check document_title, default to same post name)
        description: extract from document
        published_at: same as post date
        deadline: add deadline of the offer
        langs: guess according to title's name / default to post lang
        document_type: extract from document_name (pdf; excel..)
        document: same as slug
        posts: add post slug
        org_slugs: add model org slugs
        + add original filename

        save to publications_from_posts_TIMESTAMP
        '''
        hasDocument = bool (model and 'document_url' in model and model['document_url'])
        if hasDocument:
            document_url = model['document_url'] if 'document_url' in model and model['document_url'] else False
            pdf_url = selector.css(document_url).get() if document_url else False
            document_title = model['document_title'] if 'document_title' in model and model['document_title'] else False
            pdf_title = selector.css(document_title).get() if document_title else False
            pdf_file_name = False
            pdf_file_extension = False
            if pdf_url:
                pdf_file_name = os.path.basename(pdf_url)
                pdf_file_extension = Path(pdf_url).suffix

            '''
            print(pdf_url)
            print(pdf_title)
            print(pdf_file_name)
            print(pdf_file_extension)
            exit()
            '''

        # fix exceptions
        hst = self.get_protocol_host_from_url(link['link'])

        if 'igppp.tn' in hst:
            # define correct date for igppp
            soup = BeautifulSoup(req.text, "lxml")
            tmp = soup.find("meta",  property="og:updated_time")
            tmp = parser.parse(str(tmp['content']))
            new['published_at'] = tmp.strftime("%Y-%m-%d %H:%M:%S")


        if 'intes.rnu.tn' in hst:
            # define correct lang for intes
            new['langs'] = 'AR' if '---' in link['link'] else 'FR'

            # extract publication date from text
            title = 'وثائق خاصة بالتربص الإجباري للسنوات الأولى والثانية بتاريخ 19 ماي 2022'
            title = 'بتاريخ 10 ماي 2020'

            # test 1
            # calendar = pdt.Calendar(pdt.Constants(localeID='ar'))
            # parsed = calendar.parseDT(title)
            # test 2
            # parsed = dateparser.parse(title)
            # test 3
            # parsed = parse(title, fuzzy=True)
            # test 4
            # parsed = dateparser.parse(title, languages=['ar', 'fr'])
            # print(title)
            # print(parsed)
            # exit()
            # if parsed:
            #     print(parsed.date())
            #     exit()
        
        # print(new['published_at'])
        
        return new

    def cleanDate(self, date, current_batch=False):
        cleanr = re.compile('<.*?>')
        date = re.sub(cleanr, '', date)
        date = date.replace(',', '')
        date = date.replace(',', '')
        date = date.replace(',', '')
        date = date.replace('،', '')
        date = date.replace('◔', '')
        date = date.replace('تاريخ النشر: ', '')
        date = date.replace('Date de création: ', '')

        date = re.sub(r"\s+", "", date, flags=re.UNICODE)
        date = date.lower()
        date = date.strip()
        # remove day names
        date = date.replace('dimanche', '')
        date = date.replace('lundi', '')
        date = date.replace('mardi', '')
        date = date.replace('mercredi', '')
        date = date.replace('jeudi', '')
        date = date.replace('vendredi', '')
        date = date.replace('samedi', '')
        date = date.replace('الأحد', '')
        date = date.replace('الإثنين', '')
        date = date.replace('الاثنين', '')
        date = date.replace('الثلاثاء', '')
        date = date.replace('الأربعاء', '')
        date = date.replace('الخميس', '')
        date = date.replace('الجمعة', '')
        date = date.replace('السبت', '')

        date = date.replace('janvier', '01')
        date = date.replace('january', '01')
        date = date.replace('jan', '01')
        date = date.replace('février', '02')
        date = date.replace('fevrier', '02')
        date = date.replace('fév', '02')
        date = date.replace('fev', '02')
        date = date.replace('february', '02')
        date = date.replace('feb', '02')
        date = date.replace('mars', '03')
        date = date.replace('march', '03')
        date = date.replace('mar', '03')
        date = date.replace('avril', '04')
        date = date.replace('april', '04')
        date = date.replace('avr', '04')
        date = date.replace('apr', '04')
        date = date.replace('mai', '05')
        date = date.replace('may', '05')
        date = date.replace('juin', '06')
        date = date.replace('june', '06')
        date = date.replace('jun', '06')
        date = date.replace('juillet', '07')
        date = date.replace('juil', '07')
        date = date.replace('july', '07')
        date = date.replace('jul', '07')
        date = date.replace('august', '08')
        date = date.replace('août', '08')
        date = date.replace('aout', '08')
        date = date.replace('aoû', '08')
        date = date.replace('aou', '08')
        date = date.replace('aug', '08')
        date = date.replace('septembre', '09')
        date = date.replace('september', '09')
        date = date.replace('sept', '09')
        date = date.replace('sep', '09')
        date = date.replace('octobre', '10')
        date = date.replace('october', '10')
        date = date.replace('oct', '10')
        date = date.replace('novembre', '11')
        date = date.replace('november', '11')
        date = date.replace('nov', '11')
        date = date.replace('décembre', '12')
        date = date.replace('decembre', '12')
        date = date.replace('december', '12')
        date = date.replace('décember', '12')
        date = date.replace('déc', '12')
        date = date.replace('dec', '12')


        date = date.replace('جانفي', '01')
        date = date.replace('فيفري', '02')
        date = date.replace('مارس', '03')
        date = date.replace('أفريل', '04')
        date = date.replace('أبريل', '04')
        date = date.replace('مايو', '05')
        date = date.replace('مايو', '05')
        date = date.replace('ماي', '05')
        date = date.replace('جوان', '06')
        date = date.replace('جويلية', '07')
        date = date.replace('أوت', '08')
        date = date.replace('اوت', '08')
        date = date.replace('سبتمبر', '09')
        date = date.replace('أكتوير', '10')
        date = date.replace('أكتوبر', '10')
        date = date.replace('نوفمبر', '11')
        date = date.replace('ديسمبر', '12')
        date = date.replace('يناير', '01')
        date = date.replace('فبراير', '02')
        date = date.replace('مارس', '03')
        date = date.replace('ابريل', '04')
        date = date.replace('يونيو', '06')
        date = date.replace('يوليوز', '07')
        date = date.replace('يوليو', '07')
        date = date.replace('اغسطس', '08')
        date = date.replace('أغسطس', '08')
        date = date.replace('شتنبر', '09')
        date = date.replace('أكتوبر', '10')
        date = date.replace('نونبر', '11')
        date = date.replace('دجنبر', '12')

        # Il y a (jamaity) - deadline
        if 'ilya' in date:
            date = date.split('ilya')[0]

        # Min culture exception
        cultureBatches = [
            'minis-culture',
            'minis-culture-news-ar',
            'minis-culture-actions-ar',
            'minis-culture-activites-fr'
        ]
        # print('date')
        # print(current_batch)
        # print(date)
        if current_batch in cultureBatches and len(date) == 7:
            # print('changed')
            date = date[:2] + '0' + date[2:]
        # print(date)
        # print('------')

        if len(date) == 7:
            date = '0' + str(date)
    
    
        # Min affaires Sociale exception
        if date.endswith('-12:00'):
            date = date.replace('-12:00', '')
            date = date.strip()
            # adjust issue with Min affaires Sociale
            if len(date) == 7:
                # insert zero after month value
                date = date[:2] + '0' + date[2:]

        # Tunisiair exception
        if date.endswith(':'):
            date = date[:len(date)-1]
        
        if current_batch == 'contemporaryand' and '-' in date:
            date = date[len(date)-1]

        date = date.strip()
        date = date.strip('-')
        date = date.replace('misàjourle', '')

        return date

    def cleanMe(self, html):
        # create a new bs4 object from the html data loaded
        soup = BeautifulSoup(html, "html.parser")
        # remove all javascript and stylesheet code
        for script in soup(["script", "style"]):
            script.extract()

        removals = soup.find_all('ul', {'class': 'breadcrumb'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'post-meta'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'addtoany_share_save_container addtoany_content addtoany_content_top'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'news-single-backlink'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'post-footer'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('ul', {'class': 'metas'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'shareBar'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'article-comments'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'news__image col-sm-6'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('span', {'class': 'reforme_date'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('ul', {'class': 'joomla_add_this'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'addthis_inline_share_toolbox'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'ssba ssba-wrap'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'btn-flip-container'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'cmsImg'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'cmsDate'})
        for match in removals:
            match.decompose()
        removals = soup.find_all('div', {'class': 'outils1'})
        for match in removals:
            match.decompose()
        # get text
        text = soup.get_text()
        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text

    def download_file(self, remote_file, local_file, overwrite=False):
        if (not self.is_file_exists(local_file) and not self.is_file_exists(local_file.lower())):
            try:
                r = self.get_session().get(remote_file, headers=self._headers, allow_redirects=True, verify=False)
                # prevent a 404 error page (html string format) - if correct, the result would be a byte
                try:
                    isString = r.content.decode('utf-8')
                except:
                    isString = False
                
                if not isString:
                # if not '<html>' in r.content.decode('utf-8'):
                    with open(local_file.lower(), 'wb') as f:
                        f.write(r.content)
                        return True
                else:
                    print("Downloaded file issue (", remote_file.strip(), ")")
                    return False
            except:
                print("Can't download this file (", remote_file.strip(), ")")
                return False
        else:
            print('File already exists: ', local_file)
            return True
