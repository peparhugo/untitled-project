import requests
import pandas as pd
import geopandas as gpd
import shapely
import time
from bs4 import BeautifulSoup
import elasticsearch
from elasticsearch_dsl import Search, MultiSearch, Q

es=elasticsearch.Elasticsearch(['http://es_01'], timeout=10000,sniff_on_start=True)

std = Search(using=es,index=['regina-std-businesses','regina-yelp-businesses','regina-trip-advisor-businesses','regina-tourism-businesses'])
std_results = []
for doc in std.scan():
    std_results.append({**doc.to_dict(),**doc.meta.to_dict()})
print('got all businesses')    
def get_near_objects(geom,indices):
    els_search = Search(using=es,index=indices).filter('geo_distance',distance='100m',**{"geoPoint":geom})
    els_search=els_search[0:10000]
    resp=els_search.execute()
    return resp
indices = ['regina-yelp-businesses','regina-trip-advisor-businesses','regina-tourism-businesses','regina-std-businesses']
resp = [get_near_objects(i['geoPoint'],indices) for i in std_results]
print('got businesses near each business')
from difflib import SequenceMatcher
from geopy.distance import geodesic
def name_match(name1,name2):
    s = SequenceMatcher(None, name1, name2)
    return s.ratio()
def generate_matches(target,matches):
    results = []
    for key, i in enumerate(target):
        for k in matches[key].to_dict()['hits']['hits']:
            if i['index']!=k['_index']:
                temp_dict={}
                temp_dict['target_name']=i['name']
                temp_dict['match_name']=k['_source']['name']
                temp_dict['target_id']=i['id']
                temp_dict['target']=i['index']
                temp_dict['match']=k['_index']
                temp_dict['match_id']=k['_id']
                temp_dict['name_simil']=name_match(temp_dict['target_name'].lower().replace('restaurant',''),temp_dict['match_name'].replace('restaurant',''))
                temp_dict['distance']=geodesic((i['geoPoint']['lat'],i['geoPoint']['lon']), (k['_source']['geoPoint']['lat'],k['_source']['geoPoint']['lon'])).meters
                results.append(temp_dict)
    return results
matched_df = pd.DataFrame(generate_matches(std_results,resp))
print('got matches')
all_df = pd.DataFrame(std_results)

unique_matches = pd.Series(matched_df[matched_df.name_simil>=0.5].groupby('target_id').agg({'match_id':list}).reset_index().apply(lambda x: sorted([x.target_id,*x.match_id]),axis=1).map(lambda x: ','.join(x)).unique()).map(lambda x: x.split(',')[0])

import json
with open('../mappings/regina-master-businesses.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-master-businesses',body=index_mapping)
for row in unique_matches:
    es.index(index='regina-master-businesses',id=row,body=all_df[all_df['id']==row][['name','id','index','geoPoint']].iloc[0].to_json())
for key, row in all_df[all_df.id.isin(matched_df[matched_df.name_simil>=0.5].target_id.unique().tolist())==False][['id','name','index','geoPoint']].iterrows():
    es.index(index='regina-master-businesses',id=row['id'],body=row.to_json())
print('loaded matches to els')
print('http://localhost:5601/app/maps#/map/9d82a020-d823-11ea-b29a-b5a7bdd10a20?_g=(filters:!(),refreshInterval:(pause:!f,value:0),time:(from:now-15m,to:now))&_a=(filters:!(),query:(language:kuery,query:''))')