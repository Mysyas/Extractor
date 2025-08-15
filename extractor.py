import ee
import urllib.request
import ssl
import certifi
from datetime import datetime
import math
from parameters import getParameter
from Contants import EXPORT_FOLDER_KEY

def Login(project_id):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
    urllib.request.install_opener(opener)
    ee.Authenticate()
    ee.Initialize(project=project_id)


def getCountries():
    features=ee.FeatureCollection('FAO/GAUL/2015/level0')
    return features.aggregate_array('ADM0_NAME').getInfo()


def add_indices(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
    mndwi = image.normalizedDifference(['B3', 'B11']).rename('Flood_Index')
    return image.addBands([ndvi, ndwi, mndwi])

def create_composite(week_num, beginning_date,s2_indexed,chirps,frequency='monthly'):
    week_num = ee.Number(week_num)
    start = ee.Date(beginning_date).advance(week_num, 'week') if frequency=="weekly" \
        else ee.Date(beginning_date).advance(week_num.subtract(1), 'month') if frequency=="monthly" \
        else ee.Date(beginning_date).advance(week_num,'day')
    end = start.advance(1, 'week') if frequency=="weekly" else start.advance(1, 'month') if frequency=="monthly" else start.advance(1, 'day')

    s2_week = s2_indexed.filterDate(start, end).select(['NDVI', 'NDWI', 'Flood_Index']).mean()

    rain_week = chirps.filterDate(start, end).select('precipitation').sum().rename('Rain_Volume')

    year_band = ee.Image.constant(start.get('year')).rename('year').toInt16()
    week_band = ee.Image.constant(week_num.add(1)).rename('week').toInt16()  # 1-based week number
    date_band = ee.Image.constant(start.millis()).rename('date_millis')

    return ee.Image.cat([s2_week, rain_week, year_band, week_band, date_band]) \
             .set('date', start.format('YYYY-MM-dd'))


def extractData(country,begining_date,end_date,cloud_percent=10,frequence="monthly"):

    aoi = ee.FeatureCollection("FAO/GAUL/2015/level0") \
       .filter(ee.Filter.eq("ADM0_NAME", country)) \
       .geometry()
    s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
       .filterBounds(aoi) \
       .filterDate(begining_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")) \
       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_percent))


    s2_indexed = s2_collection.map(add_indices)
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
       .filterBounds(aoi) \
       .filterDate(begining_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    denominator=86400 if frequence=="daily" else 604800 if frequence=="weekly" else 2592000
    period=math.floor((end_date-begining_date).total_seconds()/denominator)
    periods_list=ee.List.sequence(0,period)

    images = ee.ImageCollection.fromImages(periods_list.map(lambda x:create_composite(x,begining_date.strftime("%Y-%m-%d"),s2_indexed,chirps,frequence)))
    sampled = images.map(lambda img: img.sample(
      region=aoi,
      scale=500,
      numPixels=100,  # Adjust based on resolution/performance needs
      geometries=True
    ).map(lambda f: f.set('date', img.get('date')))).flatten()
    task = ee.batch.Export.table.toDrive(
       collection=sampled,
       description='Trained data for flood',
       folder=getParameter(EXPORT_FOLDER_KEY),
       fileNamePrefix=f'{country}_{frequence}_{begining_date.strftime('%d%m%Y')}_{end_date.strftime('%d%m%Y')}',
       fileFormat='CSV'
    )

    task.start()
    return task
