import os
import shutil
import gpxpy
import pandas as pd
from geopy.distance import geodesic
import math


# Function to remove ".gz" if the filename ends with ".gpx.gz"
def remove_gz(filename):
    if filename.endswith('.gpx.gz'):
        return filename[:-3]  # Remove the ".gz" part
    return filename

def gz_extract(directory):
    extension = ".gz"
    os.chdir(directory)
    for item in os.listdir(directory): # loop through items in dir
      if item.endswith(extension): # check for ".gz" extension
          gz_name = os.path.abspath(item) # get full path of files
          file_name = (os.path.basename(gz_name)).rsplit('.',1)[0] #get file name for file within
          with gzip.open(gz_name,"rb") as f_in, open(file_name,"wb") as f_out:
              shutil.copyfileobj(f_in, f_out)
          os.remove(gz_name) # delete zipped file




def process_gpx_to_df(file_path):
    # Open and parse the file once
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    print(f'Parsing the following file: {file_path}')
    
    # Initialize lists for data
    data = []
    points = []
    
    # Extract the first track and segment
    track = gpx.tracks[0]
    segment = track.segments[0]
    activity_type = track.type
    
    # Preallocate numpy arrays if the number of points is known
    for point_idx, point in enumerate(segment.points):
        longitude = point.longitude
        latitude = point.latitude
        elevation = point.elevation
        time = point.time
        speed = segment.get_speed(point_idx)  # assuming this isn't too slow
        
        # Append to data list
        data.append([longitude, latitude, elevation, time, speed])
        
        # Append to points list for mapping
        points.append((latitude, longitude))
    
    # Convert to DataFrame
    columns = ['Longitude', 'Latitude', 'Altitude', 'Time', 'Speed']
    gpx_df = pd.DataFrame(data, columns=columns)

    return gpx_df, points, activity_type





def calculate_stats_from_df(gpx_df):
    # Initialize totals
    total_distance = 0
    elevation_gain = 0
    elevation_loss = 0
    
    # Ensure DataFrame is not empty and has enough data
    if len(gpx_df) < 2:
        raise ValueError("DataFrame does not contain enough points to calculate statistics.")
    
    # Iterate over DataFrame rows
    for i in range(1, len(gpx_df)):
        try:
            # Calculate distance between consecutive points
            prev_lat, prev_lon = gpx_df.iloc[i-1].Latitude, gpx_df.iloc[i-1].Longitude
            curr_lat, curr_lon = gpx_df.iloc[i].Latitude, gpx_df.iloc[i].Longitude
            distance = geodesic((prev_lat, prev_lon), (curr_lat, curr_lon)).kilometers
            total_distance += distance
            
            # Calculate elevation difference
            prev_elevation = gpx_df.iloc[i-1]['Altitude']
            curr_elevation = gpx_df.iloc[i]['Altitude']
            elevation_diff = curr_elevation - prev_elevation
            
            # Update elevation gain and loss
            if elevation_diff > 0:
                elevation_gain += elevation_diff
            elif elevation_diff < 0:
                elevation_loss += abs(elevation_diff)
                
        except KeyError as e:
            raise KeyError(f"Missing expected column in DataFrame: {e}")
        except Exception as e:
            raise RuntimeError(f"Error processing data: {e}")

    return {
        'total_distance': round(total_distance, 1),
        'elevation_gain': round(elevation_gain, 1),
        'elevation_loss': round(elevation_loss, 1)
    }




def get_mid_of_trail(x: pd.DataFrame):
    d={}
    # Count files per trail (passed here by 'Name') and divide by 2 to get middle point
    mid_point = x['Path'].count() / 2
    #print('mid_point')
    #print(mid_point)

    if mid_point == 1:
        mid_point_int = int(mid_point)
        mid_gpx = x.sort_values('Date').iloc[mid_point_int].Path
        marker = 'mid'
    elif mid_point.is_integer():
        mid_point_int = int(mid_point)
        mid_gpx = x.sort_values('Date').iloc[mid_point_int-1].Path
        marker = 'end'
    # If a non-integer (e.g. 4.5) is returned as mid_point, it will be rounded up by math.ceil()
    else:
        mid_point_int = math.ceil(mid_point)
        mid_gpx = x.sort_values('Date').iloc[mid_point_int-1].Path
        marker = 'mid'
    d['mid_gpx'] = mid_gpx
    d['marker'] = marker
    d['start_gpx'] = x.sort_values('Date').iloc[0].Path
    d['end_gpx'] = x.sort_values('Date').iloc[-1].Path

    return pd.Series(d, index=['mid_gpx', 'marker', 'start_gpx', 'end_gpx' ])


def get_trail_summary(x: pd.DataFrame):
    d = {}
    d['Days on Camino'] = x['Date'].count()
    d['Distance (km)'] = x['distance_km'].sum()
    d['Elapsed Time (hours)'] = x['elapsed_time_sec'].sum() / 3600
    d['Elevation Gain (m)'] = x['elevationGain'].sum()
    d['Elevation Loss (m)'] = x['elevationLoss'].sum()    
    
    return pd.Series(d)
