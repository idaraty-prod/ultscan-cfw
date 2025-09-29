# Reference
# GA4 new implementation
# https://support.google.com/analytics/answer/10089681
# https://firebase.google.com/codelabs/firebase_mp
# https://github.com/adswerve/GA4-Measurement-Protocol-Python
# https://adswerve.com/blog/how-to-use-the-google-analytics-4-measurement-protocol-python-client/

# @DEPRECATE
# from pyga.requests import Tracker, Page, Session, Visitor


import requests

__all__ = ("PyAnalyticsClass",)

class PyAnalyticsClass:
    def __init__(self,
            *,
            tracking_id: str = 'MO-XXXXX-X',
            tracking_domain: str = 'yourdomain.com',
        ):
            print('Init analytics tracker...')
            
            if not tracking_id or tracking_id == 'MO-XXXXX-X' or tracking_id == '':
                print('Please init with tracking_id')
            if not tracking_domain or tracking_domain == 'yourdomain.com' or tracking_domain == '':
                print('Please init with tracking_domain')
            
            self.ip = self.get_ip()
            print('IP = ' + str(self.ip))

            '''
            # reference:
            # https://pypi.org/project/pyga/
            # self.tracker = Tracker(tracking_id, tracking_domain)
            # self.visitor = Visitor()
            # self.visitor.ip_address = self.ip
            # self.session = Session()
            '''

    """
    # reference:
    # https://stackoverflow.com/questions/2311510/getting-a-machines-external-ip-address-with-python
    """
    def get_ip(self):
        ip_service = 'https://api.ipify.org' # or 'https://ident.me'
        ip = requests.get(ip_service).content.decode('utf8')
        return ip

    def session_start(self, path = '/'):
        '''
        # GA4
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python/blob/main/ga4mp/utils.py
        event = gtag_tracker.create_new_event(name="session_start")
        '''
        pass

    def track_pageview(self, path = '/'):
        # GA3
        # page = Page(path)
        # self.tracker.track_pageview(page, self.session, self.visitor)
        '''
        # GA4
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python/blob/main/ga4mp/utils.py
        event = gtag_tracker.create_new_event(name="page_view")
        event.set_event_param(name="page_location", value="/page")
        event.set_event_param(name="page_referrer", value="/previous_page")
        '''
        pass

    def track_select_content(self, content_id, content_type):
        '''
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python/blob/main/ga4mp/utils.py
        event = gtag_tracker.create_new_event(name="select_content")
        event.set_event_param(name="content_type", value=content_type)
        event.set_event_param(name="item_id", value=content_id)
        '''
        pass

    def track_search(self, query = '/'):
        '''
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python
        # https://github.com/adswerve/GA4-Measurement-Protocol-Python/blob/main/ga4mp/utils.py
        event = gtag_tracker.create_new_event(name="search")
        event.set_event_param(name="search_term", value=query)
        '''
        pass