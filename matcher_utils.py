# coding: utf8
#!/usr/bin/python

# import os
# import io

from pandas.core.frame import DataFrame
from pprint import pprint
import inspect
# import csv

import collections
import pandas as pd
import numpy as np

from fuzzywuzzy import process # replace with https://github.com/seatgeek/thefuzz

# debug = True
debug = False

class MatcherClass:
    def __init__(self,
            *,
            config_dir: str = '',
        ):
        current_script_path = inspect.getfile(self.__class__).replace('matcher_utils.py', '')
        current_script_path = current_script_path + "demo-configs"
        if config_dir and config_dir != '':
            current_script_path = config_dir

        print('Current path:', current_script_path)

        # self.debug = True
        self.debug = False
        self.totalCount = 0
        self.allSlugs = []

        # load gov items
        dict_govs_csv = current_script_path + "/governorates_with_alts.csv"
        govsDict = pd.read_csv(dict_govs_csv, keep_default_na=False, na_values=[""])
        govsDict = govsDict.replace(np.nan, '', regex=True)
        self.govsDict = govsDict

        # print(govsDict)
        govsDict['text_alt'] = govsDict['text_alt'].apply(self.convertToArray)
        govsDict['text_alt'] = govsDict[['text_alt', 'title_fr']].apply(self.appendToArray, axis=1)
        govsDict['text_alt'] = govsDict[['text_alt', 'title_ar']].apply(self.appendToArray, axis=1)
        govsDict['text_alt'] = govsDict[['text_alt', 'title_ar']].apply(self.appendArSenariosToArray, axis=1)

        # column to list (govs)

        textAlts = govsDict["text_alt"].tolist()
        tmp = []
        for alts in textAlts:
            tmp.append([text for text in alts if text ])
        textAlts = tmp
        self.textAlts = textAlts
        # pprint(textAlts)
        # exit()

        # Do Org slug matcher
        # print('Loading orgs...')
        # Load orgs dictionnary
        dict_govs_csv = current_script_path + "/organizations.csv"
        orgsDict = pd.read_csv(dict_govs_csv, keep_default_na=False, na_values=[""])
        orgsDict = orgsDict.replace(np.nan, '', regex=True)

        # exclude specific types
        excludeTypes = [
            'station-synoptique',
            'station-service',
            'station-transport',
            'bureau-change',
        ]
        orgsDict = orgsDict[~orgsDict['org_type'].isin(excludeTypes)]

        orgsDict = orgsDict[['slug', 'title_ar', 'title_fr']]
        self.orgsDict = orgsDict



        # column to list (orgs) + exclude empty titles
        titlesOrgAr = orgsDict["title_ar"].tolist()
        self.titlesOrgAr = [item for item in titlesOrgAr if item and item != '']

        titlesOrgFr = orgsDict["title_fr"].tolist()
        self.titlesOrgFr = [item for item in titlesOrgFr if item and item != '']
        # print(str(len(titlesOrgFr)) +  ' orgs loaded !')
        # print(' ')

    def convertToArray(self, str):
        return str.split(';')

    def appendToArray(self, vec):
        text_alt = vec.iloc[0]
        title = vec.iloc[1]
        if title and title != '':
            text_alt.append(title)
        return text_alt

    def appendArSenariosToArray(self, vec):
        text_alt = vec.iloc[0]
        title_ar = vec.iloc[1]
        text_alt.append( 'ب' + title_ar)
        tmp = 'ل' + title_ar
        if 'لال' in tmp:
            tmp.replace('لال','لل')
        text_alt.append(tmp)

        return text_alt


    def getOrgSlug(self, text, key):
        slug = self.orgsDict[self.orgsDict[key] == text].values
        if (len(slug) > 0 and len(slug[0]) > 0):
            slug = slug[0][0]
            return slug
        return False

    def add_org_slugs_fuzzy(self, vec):
        title_ar = vec.iloc[0]
        title_fr = vec.iloc[1]

        slugs = []
        matcher_col = 'title_ar'
        text = title_ar
        searchList = self.titlesOrgAr
        if (title_fr and not title_fr == ''):
            matcher_col = 'title_fr'
            text = title_fr
            searchList = self.titlesOrgFr

        items = process.extract(text, searchList)
        for item in items:
            # get slug
            result = item[0]
            confidence = item[1]
        
            if (confidence > 83):
                print(result)
                slug = self.getOrgSlug(result, matcher_col)
                if slug:
                    slugs.append(slug)
        
        if debug:
            print('#####################')
            print('Text')
            pprint(text)
            print('Results:')
            pprint(slugs)
            print('#####################')

        return ';'.join(list(set(slugs)))


    def add_org_slugs_exact(self, vec):
        global allSlugs
        global totalCount
        global titlesOrgAr
        global titlesOrgFr
        global debug
        title_ar = vec.iloc[0]
        title_fr = vec.iloc[1]

        matcher_col = 'title_ar'
        text = title_ar
        searchList = self.titlesOrgAr
        if (title_fr and not title_fr == ''):
            matcher_col = 'title_fr'
            text = title_fr
            searchList = self.titlesOrgFr
        slugs = []
        if text and not text == '' and not text == 'nan':
            slugs = [ele for ele in searchList if (ele.lower() in text.lower())]
            slugs = [self.getOrgSlug(item, matcher_col) for item in slugs]
            slugs = list(set(slugs))
        totalCount += len(slugs)
        if debug:
            # print("-----------")
            # pprint(text)
            # pprint(slugs)
            # print("-----------")
            self.allSlugs = self.allSlugs + slugs

        '''
        # debug / test senario
        if 'recette-des-entrepots-monopolises-mahdia' in slugs:
            print("-----------")
            pprint(text)
            pprint(slugs)
            print("-----------")
            exit()
        '''
        return ';'.join(slugs)


    def keep_new_tags_only(self, vec):
        old = vec.iloc[0]
        new = vec.iloc[1]

        new = new.split(';')
        new = [item for item in new if not item in old]

        return ';'.join(new)


    def combine_tags(self, vec):
        old = vec.iloc[0]
        new = vec.iloc[1]

        old = old.split(';')
        new = new.split(';')

        # combine
        new = old + new

        # unique
        new = list(set(new))

        # remove empty values
        new = [item for item in new if item and not item == '']
        # pprint(new)
        return ';'.join(new)


    def getGovSlug(self, text, key):
        '''
        allItems = govsDict[key]
        for text in texts:
            index = 0
            for govAlts in allItems:
                # print(govAlts)
                if text in govAlts:
                    slug = govsDict[index].values
                    print('slug')
                    print(slug)
                    # continue
                    index += 1
                    exit()
        '''
        slug = DataFrame()

        # if not slug.empty():
        #     continue
        # print(text)
        mask = self.govsDict[key].apply(lambda x: text in x)
        # print('mask')
        # print(mask)
        slug = self.govsDict[mask].values
        # print(slug)
        # exit()
        # slug = slug if not slug.empty() else DataFrame()


        # # slug = govsDict[govsDict[key].contains(text)].values
        # slug = False
        # # slug = govsDict[key]
        # slug = text in govsDict[key]
        # slug = govsDict[text in govsDict[key]].values
        # pprint('found gov slug !')
        # pprint(slug)
        # exit()
        if (len(slug) > 0 and len(slug[0]) > 0):
            slug = slug[0][0]
            return slug
        return False

    def add_gov_slugs_exact(self, vec):
        title_ar = vec.iloc[0]
        title_fr = vec.iloc[1]

        searchList = self.textAlts

        text = title_ar
        if (title_fr and not title_fr == ''):
            text = title_fr
        slugs = []
        if text and not text == '' and not text == 'nan':
            slugs = [ele for items in searchList for ele in items if (ele.lower() in text.lower())]
            # print('matched items !')
            # pprint(text)
            # pprint(slugs)
            # if (len(slugs) > 0):
            #     exit()
            if slugs and len(slugs) > 0:
                slugs = [self.getGovSlug(items, 'text_alt') for items in slugs]
                slugs = list(set(slugs))
        self.totalCount += len(slugs)
        if self.debug:
            print("-----------")
            pprint(text)
            pprint(slugs)
            print("-----------")
            self.allSlugs = self.allSlugs + slugs

        '''
        # debug / test senario
        if 'recette-des-entrepots-monopolises-mahdia' in slugs:
            print("-----------")
            pprint(text)
            pprint(slugs)
            print("-----------")
            exit()
        '''
        return ';'.join(slugs)

    # Deleting (Calling destructor)
    def __del__(self):
        if debug:
            print('List of the items found: ')
            pprint(self.allSlugs)
            occurrences = collections.Counter(self.allSlugs)
            print('Top recurrent items: ')
            pprint(occurrences)

            print('---------------')
            print('Total items tagged: ', self.totalCount)
            print('---------------')
