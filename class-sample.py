from termcolor import colored
from pathlib import Path
import datetime
from bs4 import BeautifulSoup
from slugify import slugify
import os
import re
import htmlmin
from dateutil import parser
from parsel import Selector
import urllib
from urllib.parse import urlparse
from urllib.parse import quote
from urllib.parse import urlencode

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
        new['deadline'] = deadline.rjust(8, '0')
        if ('deadline_format' in model and model['deadline_format']):
            deadline = self.cleanDate(new['deadline'], model['batch_id'])
            try:
                dtmp = datetime.datetime.strptime(new['deadline'], model['deadline_format'])
            except:
                dtmp = self.cleanDate(new['deadline'], model['batch_id'])
                # print('dtmp')
                # print(dtmp)
                dtmp = datetime.datetime.strptime(dtmp, model['deadline_format'])
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
                    date = self.cleanDate(new['published_at'], model['batch_id'])
                    try:
                        dtmp = datetime.datetime.strptime(new['published_at'], model['single_date_format'])
                    except:
                        dtmp = self.cleanDate(new['published_at'], model['batch_id'])
                        # print('dtmp')
                        # print(dtmp)
                        dtmp = datetime.datetime.strptime(dtmp, model['single_date_format'])

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

    return new
