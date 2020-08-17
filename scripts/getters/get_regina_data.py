import requests
import pandas as pd
import geopandas as gpd
import shapely
import time
from bs4 import BeautifulSoup
import elasticsearch
import json
from elasticsearch_dsl import Search, MultiSearch, Q
######################YELP########################
def get_businesses_yelp():
    offset = 0
    size = 20
    results = []
    resp = requests.get('https://api.yelp.com/v3/businesses/search?location=regina&offset={}&limit={}'.format(offset,size),
                        headers={
                            "Authorization":"Bearer 6SFD9SrE0z3Kt5mZN8EURT8jmxIy3rUBhfvtb2R4G46tWqCvnGcclmETU6UkWIzLbQKAPIINW4pBP7fwMvMDNb0AVvCgcp0QqDGQXBL2RE3VKcS5uux7ZuehyCksX3Yx"
                        }).json()
    results.extend(resp['businesses'])
    region = resp['region']
    while len(resp['businesses'])>0:
        time.sleep(2)
        
        offset +=size
        resp = requests.get('https://api.yelp.com/v3/businesses/search?location=regina&offset={}&limit={}'.format(offset,size),
                            headers={
                                "Authorization":"Bearer 6SFD9SrE0z3Kt5mZN8EURT8jmxIy3rUBhfvtb2R4G46tWqCvnGcclmETU6UkWIzLbQKAPIINW4pBP7fwMvMDNb0AVvCgcp0QqDGQXBL2RE3VKcS5uux7ZuehyCksX3Yx"
                            }).json()
        #print(resp)
        results.extend(resp['businesses'])
    return region, pd.DataFrame(results)

region, yelp_businesses = get_businesses_yelp()

es=elasticsearch.Elasticsearch(['http://es_01'], timeout=10000,sniff_on_start=True)

with open('../mappings/regina-yelp-businesses.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-yelp-businesses',body=index_mapping)

def fix_coordinates(coords):
    coords['lat'] = coords.pop('latitude')
    coords['lon'] = coords.pop('longitude')
yelp_businesses.coordinates.map(fix_coordinates)

for key, row in yelp_businesses.iterrows():
    #print(row.to_json())
    row['geoPoint']=row.coordinates
    es.index(index='regina-yelp-businesses',id=row['id'],body=row.to_json())
print('loaded yelp')
######################Trip Advisor########################
resp_ta = requests.get('https://www.tripadvisor.ca/data/1.0/attraction_overview/maps/geoId?g=155042')
with open('../mappings/regina-trip-advisor-businesses.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-trip-advisor-businesses',body=index_mapping)
for key, row in pd.DataFrame(resp_ta.json()['majorAttractionPins']).iterrows():
    fix_coordinates(row.geoPoint)
    #print(row.to_json())
    es.index(index='regina-trip-advisor-businesses',id=row['id'],body=row.to_json())
for key, row in pd.DataFrame(resp_ta.json()['minorAttractionPins']).iterrows():
    fix_coordinates(row.geoPoint)
    #print(row.to_json())
    es.index(index='regina-trip-advisor-businesses',id=row['id'],body=row.to_json())
print('loaded trip advisor')
######################Skip The Dishes########################
headers = {'Content-type': 'application/json', 'Accept': 'text/plain','App-Token': 'd7033722-4d2e-4263-9d67-d83854deb0fc'}
resp = requests.post('https://api.skipthedishes.com/customer/v1/graphql',headers = headers,
                     data='{"operationName":"QueryRestaurantsCuisinesList","variables":{"city":"regina","province":"SK","latitude":50.4792459,"longitude":-104.644233,"isDelivery":true,"dateTime":0,"search":"","language":"en"},"extensions":{"persistedQuery":{"version":1,"sha256Hash":"ca5b47d93973b0231c8e72d6fd75b209c004fe2112e2b7ec7495516b60d9c16c"}}}').json()
with open('../mappings/regina-std-businesses.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-std-businesses',body=index_mapping)
for key, row in pd.DataFrame(resp['data']['restaurantsList']['openRestaurants']).iterrows():
    row['geoPoint']={'lat':row['location']['position']['latitude'],'lon':row['location']['position']['longitude']}
    es.index(index='regina-std-businesses',id=row['id'],body=row.to_json())
print('loaded skip the dishes')
######################Tourism Regina########################
tourism_results = []
for sub_cat in [7,15,20,4,8,9,10,11,13,14,3]:
    resp = requests.get('https://tourismregina.com/api/businesses?subcategory={}'.format(sub_cat))
    tourism_results.extend(resp.json())
with open('../mappings/regina-tourism-businesses.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-tourism-businesses',body=index_mapping)
for key, row in pd.DataFrame(tourism_results).iterrows():
    row['geoPoint']={'lat':row['latitude'],'lon':row['longitude']}
    es.index(index='regina-tourism-businesses',id=row['id'],body=row.to_json())
print('loaded regina tourism')
##################City of Regina########################
amenties = requests.get('https://opengis.regina.ca/arcgis/rest/services/OpenData/ParksAndAmenities/MapServer/1/query?f=json&where=(1%3D1)%20AND%20(1%3D1)&returnGeometry=true&spatialRel=esriSpatialRelIntersects&outFields=*&orderByFields=OBJECTID%20ASC&outSR=4326&resultOffset=0&resultRecordCount=10000')
with open('../mappings/regina-park-amenities.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-park-amenities',body=index_mapping)
for key, row in pd.DataFrame([{**i['attributes'],'geometry':i['geometry']} for i in amenties.json()['features']]).iterrows():
    row['geoPoint']={'lat':row['geometry']['y'],'lon':row['geometry']['x']}
    es.index(index='regina-park-amenities',id=row['GLOBALID'],body=row.to_json())
print('loaded park amenities')
dog_park = requests.get('https://opengis.regina.ca/arcgis/rest/services/CGISViewer/OffLeash_DogPark_Area/MapServer/0/query?f=json&where=(1%3D1)%20AND%20(1%3D1)&returnGeometry=true&spatialRel=esriSpatialRelIntersects&outFields=*&orderByFields=OBJECTID%20ASC&outSR=4326&resultOffset=0&resultRecordCount=1000')
with open('../mappings/regina-park-dog.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-park-dog',body=index_mapping)
for key, row in pd.DataFrame([{**i['attributes'],'geometry':i['geometry']} for i in dog_park.json()['features']]).iterrows():
    row['geoPoint']={'lat':row['geometry']['y'],'lon':row['geometry']['x']}
    es.index(index='regina-park-dog',id=row['OBJECTID'],body=row.to_json())
print('loaded dog parks')
paths = requests.get('https://opengis.regina.ca/arcgis/rest/services/OpenData/Pathways/MapServer/0/query?f=json&where=(1%3D1)%20AND%20(1%3D1)&returnGeometry=true&spatialRel=esriSpatialRelIntersects&outFields=*&orderByFields=OBJECTID%20ASC&outSR=4326&resultOffset=0&resultRecordCount=10000')
with open('../mappings/regina-pathways.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-pathways',body=index_mapping)
for key, row in pd.DataFrame([{**i['attributes'],'geometry':i['geometry']} for i in paths.json()['features']]).iterrows():
    if len(row['geometry']['paths'])==1:
        #print(len(row['geometry']['paths']))
        row['path']=shapely.geometry.mapping(shapely.geometry.LineString(row['geometry']['paths'][0]))
        es.index(index='regina-pathways',id=row['OBJECTID'],body=row.to_json())
    elif len(row['geometry']['paths'])>1:
        #print(len(row['geometry']['paths']))
        row['path']=shapely.geometry.mapping(shapely.geometry.MultiLineString(row['geometry']['paths']))
        es.index(index='regina-pathways',id=row['OBJECTID'],body=row.to_json())
print('loaded park paths')
park_shapes = requests.get('https://opengis.regina.ca/arcgis/rest/services/CGISViewer/ParksandRecFinder/MapServer/1/query?f=json&where=(1%3D1)%20AND%20(1%3D1)&returnGeometry=true&spatialRel=esriSpatialRelIntersects&outFields=*&outSR=4326&resultOffset=0&resultRecordCount=10000')
with open('../mappings/regina-park-shape.json','r') as f:
    index_mapping = json.loads(f.read())
es.indices.create(index='regina-park-shape',body=index_mapping)
for key,row in pd.DataFrame([{**i['attributes'],'geometry':i['geometry']} for i in park_shapes.json()['features']]).iterrows():
    if len(row['geometry']['rings'])==1:

        row['shape']=shapely.geometry.mapping(shapely.geometry.Polygon(row['geometry']['rings'][0]))
        es.index(index='regina-park-shape',id=row['GIS.OPENSPACE.GLOBALID'],body=row.to_json())
    elif len(row['geometry']['rings'])>1:

        row['shape']=shapely.geometry.mapping(shapely.geometry.MultiPolygon([shapely.geometry.Polygon(k) for k in row['geometry']['rings']]))
        es.index(index='regina-park-shape',id=row['GIS.OPENSPACE.GLOBALID'],body=row.to_json())
print('loaded park geometries')
url = 'http://kib_01:5601/api/saved_objects/_import'
files = {'file': open('../mappings/export.ndjson', 'rb')}

r = requests.post(url, files=files, headers={'kbn-xsrf': 'true'})
print('loaded kibana objects for map')
