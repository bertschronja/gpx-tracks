#!/usr/bin/env python
# coding: utf-8

# In[43]:


import pandas as pd
from datetime import datetime
import os
import re
import folium
import gpxpy
import shutil
import gzip
import math
from collections import defaultdict
import gc
from pathlib import Path
from geopy.distance import geodesic
from IPython.display import IFrame, display
from concurrent.futures import ProcessPoolExecutor, as_completed




def cleanup_old_backups(directory, max_files_to_keep=10):
    """
    Deletes backup files older than the most recent 'max_files_to_keep' files.
    
    Args:
    - directory (str): The directory where backup files are stored.
    - max_files_to_keep (int): Maximum number of recent files to keep.
    """
    # List to store files with their modification times
    files_with_times = []

    # Scan the directory and get files with their last modification times
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            # Get the last modification time of the file
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            files_with_times.append((mod_time, filename))
    
    # Sort files by modification time (oldest first)
    files_with_times.sort(key=lambda x: x[0])
    
    # Determine files to delete (all but the latest 'max_files_to_keep')
    files_to_delete = files_with_times[:-max_files_to_keep]

    # Print the number of files that will be deleted
    print(f"{len(files_to_delete)} files will be deleted")

    # Delete the old files
    for _, file in files_to_delete:
        file_path = os.path.join(directory, file)
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")


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




'''def process_gpx_to_df(file_path):
    gpx = gpxpy.parse(open(file_path))
    print('Parsing the following file: ' + file_path)
    
    # Create data frame
    track = gpx.tracks[0]
    segment = track.segments[0]
    activity_type = track.type
    
    # Load the data into a Pandas dataframe (by way of a list)
    data = []
    for point_idx, point in enumerate(segment.points):
        data.append([
            point.longitude, 
            point.latitude,
            point.elevation,
            point.time,
            segment.get_speed(point_idx)
        ])
    
    columns = ['Longitude', 'Latitude', 'Altitude', 'Time', 'Speed']
    gpx_df = pd.DataFrame(data, columns=columns)

    # Create points tuples to display on map
    points = []
    for track in gpx.tracks:
        for segment in track.segments:        
            for point in segment.points:
                points.append((point.latitude, point.longitude))
    
    return gpx_df, points, activity_type'''






import gpxpy
import pandas as pd
import numpy as np

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




def read_csv_with_separators(file_path, dtype, usecols, separators=[',', ';']):
    for sep in separators:
        try:
            df = pd.read_csv(file_path, sep=sep, dtype = dtype, usecols = usecols)
            print(f"Successfully read with separator: '{sep}'")
            return df
        except ValueError:
            print(f"Failed to read with separator: '{sep}'")
    raise ValueError("Unable to read the CSV file with the provided separators.")


def wikiloc_get_activity_name(gpx_file):
    #jenky - second instane of name is what I want
    root = ET.parse(gpx_file).getroot()
    for elem in root.iter():
        if elem.tag=='{http://www.topografix.com/GPX/1/1}name':
            name = elem.text
    return name


from collections import defaultdict

# Iterate over the 'OrderOfDays' column to count the number of trails per day
def calculate_trails_per_day(df):
    
    # Initialize a nested dictionary to store the counts
    trails_dict = defaultdict(lambda: defaultdict(int))
    
    # Iterate over the DataFrame rows
    for _, row in df.iterrows():
        trail_name = row['Name']
        order = row['OrderOfDays']
        
        # Extract the day number from 'OrderOfDays'
        if isinstance(order, str):
            day = int(float(order.split('-')[0]))
        else:
            day = int(round(order, 0))
        
        # Increment the count for this trail name on the specific day
        trails_dict[trail_name][day] += 1
    
    # Convert defaultdicts to regular dictionaries (optional)
    trails_dict = {k: dict(v) for k, v in trails_dict.items()}
    
    # Now you can access the counts for any trail name and day, e.g., trails_dict['Trail1'][2]
    return trails_dict

# Function to apply a small offset to the location
def offset_location(lat, lon):
    # Earth's radius in meters
    R = 6378137.0

    offset_lat, offset_lon = (50, 50)  # Example offset

    # Offset by latitude (in meters)
    d_lat = offset_lat / R
    d_lon = offset_lon / (R * (3.14159 / 180) * lat)

    # Convert offset from radians to degrees
    new_lat = lat + (d_lat * (180 / 3.14159))
    new_lon = lon + (d_lon * (180 / 3.14159))
    
    return new_lat, new_lon





# In[68]:


def process_gpx_file(args):
    file_path, activity_df = args
    if os.path.getsize(file_path) == 0:
        print('Skipping this file due to it being EMPTY: ' + file_path)
        return None

    df, points, activity = process_gpx_to_df(file_path)
    stats = calculate_stats_from_df(df)
    
    # Extract additional info from activity_df
    trail_info = activity_df.loc[activity_df.Path == file_path].iloc[0]
    trail_name = trail_info['Name']
    trail_day_name = trail_info['OrderOfDays']
    trail_day = int(float(trail_day_name.split('-')[0]))
    
    return {
        'file_path': file_path,
        'df': df,
        'points': points,
        'activity': activity,
        'stats': stats,
        'trail_name': trail_name,
        'trail_day_name': trail_day_name,
        'trail_day': trail_day
    }

def create_map(gpx_file_path, gpx_files, activity_df, map_name, plot_method='poly_line', zoom_level=12, add_trail_info=False, mark_track_terminals=False, track_terminal_radius_size=2000, show_minimap=False, map_type='terrain', fullscreen=False, number_of_tracks="all", max_workers=20):
    pd.set_option('display.precision', 0)
    os.chdir(gpx_file_path)

    
    trails_per_day = calculate_trails_per_day(activity_df)
    print('Tracks per day: ' + str(trails_per_day))
    
    # Prepare arguments for parallel processing
    args_list = [(file_path, activity_df) for file_path in gpx_files]
    
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_gpx_file, args): args[0] for args in args_list}
        for future in as_completed(future_to_file):
            result = future.result()
            if result is not None:
                results.append(result)
    
    # Sort results if necessary
    results = sorted(results, key=lambda x: x['trail_day'])
    
    # Initialize the map
    first_result = results[0]
    df = first_result['df']
    mymap = folium.Map(location=[df.Latitude.mean(), df.Longitude.mean()], zoom_start=zoom_level)
    
    if map_type == 'regular':
        folium.TileLayer('openstreetmap', name='OpenStreet Map').add_to(mymap)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}', 
                         attr="Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC", 
                         name='Nat Geo Map').add_to(mymap)
    elif map_type == 'terrain':
        folium.TileLayer('Stamen Terrain').add_to(mymap)
    elif map_type == 'nat_geo':
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}', 
                         attr="Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC").add_to(mymap)
    
    order_of_days_df = activity_df.groupby('Name').apply(get_mid_of_trail)

    i = 0
    iteration = 1
    for result in results:
        file_path = result['file_path']
        df = result['df']
        points = result['points']
        activity = result['activity']
        stats = result['stats']
        trail_name = result['trail_name']
        trail_day_name = result['trail_day_name']
        print('trail day name' + trail_day_name)
        trail_day = result['trail_day']
        trail_distance = stats['total_distance']
        elevation_gain = stats['elevation_gain']
        elevation_loss = stats['elevation_loss']

        # get start and end lat/long
        lat_start = df.iloc[0].Latitude
        long_start = df.iloc[0].Longitude
        lat_end = df.iloc[-1].Latitude
        long_end = df.iloc[-1].Longitude

        # Determine activity color and icon
        if activity == 'Cycling':
            activity_color = 'green'
            activity_icon = 'bicycle'
        elif activity == 'Hiking':
            activity_color = 'blue'
            activity_icon = 'compass'
        else:
            activity_color = 'red'
            activity_icon = 'rocket'

        if i==0:
            mymap = folium.Map( location=[ df.Latitude.mean(), df.Longitude.mean() ], zoom_start=zoom_level)
            if map_type=='regular':
                mymap = folium.Map( location=[ df.Latitude.mean(), df.Longitude.mean() ], zoom_start=zoom_level, tiles=None)
                folium.TileLayer('openstreetmap', name='OpenStreet Map').add_to(mymap)
                folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}', attr="Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC", name='Nat Geo Map').add_to(mymap)

            elif map_type=='terrain':
                mymap = folium.Map(location=[ df.Latitude.mean(), df.Longitude.mean() ], tiles='http://tile.stamen.com/terrain/{z}/{x}/{y}.jpg', attr="terrain-bcg", zoom_start=zoom_level)
            elif map_type=='nat_geo':
                mymap = folium.Map(location=[ df.Latitude.mean(), df.Longitude.mean() ], tiles='https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}', attr="Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC", zoom_start=zoom_level)

        
        # Find out if a given gpx_file file belongs to a "main track" or an "additional track" (e.g. summit hike)
        if iteration == 1 and trails_per_day[trail_name][trail_day] == 1: # Only one track on this day
            is_main_track = True
        elif (iteration == 1) and (trails_per_day[trail_name][trail_day] != 1): # More than one track on this day
            is_main_track = True
            iteration = iteration + 1
        elif iteration == trails_per_day[trail_name][trail_day]: # This is the last track of the day
            is_main_track = False
            iteration = 1
        else: # Those are all other tracks (not first, not last ones)
            is_main_track = False    
            iteration = iteration + 1

        ''' HELPER
        X trails_per_day = 1 & iteration = 1
        Y iteration = 1 & trails_per_day[trail_name][trail_day]  != 1
        Z iteration = trails_per_day
            
        
        trail day  Iteration     trails_per_day[trail_name][trail_day]      is_main_track
        X1             1            1    -> new day, set iteration to 1       true
        Y2             1            3                                          true
        2             2            3                                         false
        Z2             3            3      -> new day, set iteration to 1     false
        Y3             1            2                                          true
        Z3             2            2     -> new day, set iteration to 1       false
        X4             1            1     -> new day, set iteration to 1       true
        X5             1            1     -> new day, set iteration to 1        true
        '''

        print(str(trail_day_name) + ' - Is this a main track? ' + str(is_main_track))

        print('Facts about trail ' + file_path + ': Name: ' + trail_day_name + ', Day: ' + str(trail_day) + ', Distance: ' + str(trail_distance))

        
        
        if plot_method=='poly_line':
            if file_path in order_of_days_df.start_gpx.to_list() and add_trail_info==True:
                
                # Create feature group by trail name
                fg = folium.FeatureGroup(name=trail_name, show=True)
                
                mymap.add_child(fg)
                folium.PolyLine(points, color=activity_color, weight=4.5, opacity=.5).add_to(mymap).add_to(fg)
                
                #build starting marker
                html_camino_start = """
                Start of {trail_name}
                """.format(trail_name=trail_name)
                popup = folium.Popup(html_camino_start, max_width=400)
                #nice green circle
                folium.vector_layers.CircleMarker(location=[lat_start, long_start], radius=9, color='white', weight=1, fill_color='green', fill_opacity=1,  popup=html_camino_start).add_to(mymap).add_to(fg) 
                #OVERLAY triangle
                folium.RegularPolygonMarker(location=[lat_start, long_start], 
                      fill_color='white', fill_opacity=1, color='white', number_of_sides=3, 
                      radius=3, rotation=0, popup=html_camino_start).add_to(mymap).add_to(fg)

            elif file_path in order_of_days_df.mid_gpx.to_list() and add_trail_info==True:
                #camino_summary = activity_df.groupby('Name').apply(get_trail_summary)
                
                #print('summary: ' + str(camino_summary))
                #add 'mid' or 'end' marker, depending on how many tracks there are on camino (to approximate midpoint)
                marker_location = order_of_days_df.loc[order_of_days_df.mid_gpx==file_path,'marker'][0]
                #mask = (camino_summary.index==Name)
                #print('mask' + str(mask))
                #camino_summary_for_icon = camino_summary[mask].melt().rename(columns={'variable':'Metric'}).set_index('Metric').round(1)
                #melt_mask = (camino_summary_for_icon['value'].notnull()) & (camino_summary_for_icon['value']!=0)
                #camino_summary_for_icon = pd.DataFrame(camino_summary_for_icon[melt_mask]['value'].apply(lambda x : "{:,}".format(x)))

                html_Name = """
                <div align="justify">
                <h5>{Name}</h5><br>
                </div>

                """.format(Name=trail_name)

                
                

                #html = html_Name + """<div align="center">""" + camino_summary_for_icon.to_html(justify='center', header=False, index=True, index_names=False, col_space=300, classes='table-condensed table-responsive table-success') + """</div>""" #
                html = html_Name + """<div align="center">"""
                #(justify='center', header=False, index=True, index_names=False, col_space=300, classes='table-condensed table-responsive table-success') + """</div>""" #


                popup = folium.Popup(html, max_width=300)
                

                if marker_location=='mid':
                    #get midpoint long / lad
                    length = df.shape[0]
                    mid_index= math.ceil(length / 2)

                    lat = df.iloc[mid_index]['Latitude']
                    long = df.iloc[mid_index]['Longitude']
                else:
                    lat = lat_end
                    long = long_end
                mymap.add_child(fg)
                #create line:
                folium.PolyLine(points, color=activity_color, weight=4.5, opacity=.5).add_to(mymap).add_to(fg)
                
                folium.Marker([lat, long], popup=popup, icon=folium.Icon(color=activity_color, icon_color='white', icon=activity_icon, prefix='fa')).add_to(mymap).add_to(fg)

            # end of trail:  
            elif file_path in  order_of_days_df.end_gpx.to_list() and add_trail_info==True:
                mymap.add_child(fg)
                #create line:
                folium.PolyLine(points, color=activity_color, weight=4.5, opacity=.5).add_to(mymap).add_to(fg)
                
                #camino end marker ORIGINAL THAT WORKS
                html_camino_end = """
                End of {trail_name}
                """.format(trail_name=trail_name)
                popup = html_camino_end
                
                #nice red circle
                folium.vector_layers.CircleMarker(location=[lat_end, long_end], radius=9, color='white', weight=1, fill_color='red', fill_opacity=1,  popup=popup).add_to(mymap).add_to(fg) 
                #OVERLAY square
                folium.RegularPolygonMarker(location=[lat_end, long_end], 
                      fill_color='white', fill_opacity=1, color='white', number_of_sides=4, 
                      radius=3, rotation=45, popup=popup).add_to(mymap).add_to(fg)            
            elif add_trail_info==True:
                mymap.add_child(fg)
                folium.PolyLine(points, color=activity_color, weight=4.5, opacity=.5).add_to(mymap).add_to(fg)         


        # Add terminal messages to all tracks
        if mark_track_terminals==True:
            track_terminal_message = 'End of Day ' + str(trail_day_name) + '-  Distance: ' + str(trail_distance) + ' km.'
            mymap.add_child(fg)
            # If there are multiple activities that have the same end date, their location must be manipulated
            if is_main_track == False:
                new_lat, new_lon = offset_location(lat_end, long_end)
                activity_color = 'green'
                folium.vector_layers.Marker(location=[new_lat, new_lon], popup = track_terminal_message, radius=track_terminal_radius_size, color=activity_color, fill_color=activity_color, weight=2, fill_opacity=0.3,  tooltip=track_terminal_message, icon=folium.Icon(icon='info-sign')).add_to(mymap).add_to(fg)
            else:
                folium.vector_layers.Circle(location=[lat_end, long_end], radius=track_terminal_radius_size, color=activity_color, fill_color=activity_color, weight=2, fill_opacity=0.3,  tooltip=track_terminal_message).add_to(mymap).add_to(fg)

        if plot_method=='circle_marker':
            coordinate_counter = 30
            for coord in df[['Latitude','Longitude']].values:
                if 1==1:
                    #every 10th element, mark
                    folium.CircleMarker(location=[coord[0],coord[1]], radius=1,color=activity_color).add_to(mymap)
                coordinate_counter += 1
                
        i+=1
        print('TRACK ADDED TO MAP FOR FILE ' + file_path)
        if i == number_of_tracks:
            break;
            
    if show_minimap == True:
        minimap = MiniMap(zoom_level_offset=-4)
        mymap.add_child(minimap)
            
    #fullscreen option
    if fullscreen==True:
        plugins.Fullscreen(
            position='topright',
            title='Expand me',
            title_cancel='Exit me',
            force_separate_button=True
        ).add_to(mymap)

    folium.LayerControl(collapsed=True).add_to(mymap)
    print('Saving to map: ' + map_name)
    mymap.save(map_name) # saves to html file for display below


def main():


    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    # This is the file that comes from the Strava export tools
    # https://github.com/liskin/strava-offline
    # https://github.com/evgeniyarbatov/strava2csv
    strava_export_file = 'gpx-file-strava'

    # This is the file where new activities from the Strava export file above are merged into and manual comments are added
    strava_merged_comment_file = 'strava-export-merged-with-comments-PUT-COMMENTS-HERE'

    strava_base_path = '/Users/ronja/Documents/Dateien/tech/gpx/source-data/strava/'

    # Define the directory containing the backup files
    backup_directory = strava_base_path + '/sicherungskopien'

    # Delete old backups
    cleanup_old_backups(backup_directory)

    os.chdir(strava_base_path)

    # Create a backup
    strava_export_file_backup = shutil.copyfile(strava_base_path + strava_export_file + '.csv',
                                            strava_base_path + 'sicherungskopien/' + strava_export_file + '-' + datetime.now().strftime("%Y-%m-%d-%H-%M") +'.csv')

    strava_export_file_dtypes = {'ActivityType': 'string', 'Filename': 'string', 'Latitude': 'float64', 'Longitude': 'float64', 'Comment': 'string'}

    # Read Strava export file
    strava_export_file_df = pd.read_csv(strava_base_path + strava_export_file + '.csv',
                            sep=',', header = None, dtype = strava_export_file_dtypes,
                            names=['Time',"ActivityType","Filename","Latitude","Longitude","Elevation","Cadence","Heartrate","Power"])

    print(f'Successfully read file {strava_export_file}')

    # Drop entries that belong to the same activity
    strava_export_file_without_duplicates_df = strava_export_file_df.drop_duplicates(subset='Filename')

    # Rename columns for better accessibility
    strava_export_file_without_duplicates_df.rename(columns=
                                { 'Elevation': 'elevationGain',
                                'Heartrate': 'averageHR',
                                'ActivityType': 'activityType',
                                'Filename': 'Path'
                                }, inplace=True)

    print(strava_export_file_without_duplicates_df.head())


    strava_export_file_without_duplicates_df.to_csv(strava_base_path + strava_export_file + '-without-duplicates.csv', index=False)





    # Create first version of comment file, if it does not yet exist
    file_path = Path(strava_base_path + strava_merged_comment_file + '.csv')

    if file_path.exists():
        print(f"A file including comments {file_path} exists, hence will not be created.")
    else:
        print(f"A file including comments {file_path} does not exist, hence will be created.")

        strava_commented_file_headers_df = strava_export_file_without_duplicates_df
        
        # Add comment columns
        strava_commented_file_headers_df['Name'] = None
        strava_commented_file_headers_df['OrderOfDays'] = 0
        strava_commented_file_headers_df['Family'] = None
        
        # Save header line to CSV file
        strava_commented_file_headers_df.head(0).to_csv(strava_base_path + strava_export_file_with_comments + '.csv', index=False)
        strava_commented_file_headers_df.head(0)

    strava_export_file_with_comments_dtypes = {'Path': 'string', 'activityType': 'string', 'Name': 'string', 'OrderOfDays': 'string', 'Family': 'string'}

    # 1. Read merged comment file from previous run (CSV)
    strava_export_file_with_comments_df = read_csv_with_separators(strava_base_path + strava_merged_comment_file + '.csv',
                                                    strava_export_file_with_comments_dtypes, ['Time', 'activityType', 'Path', 'Name', 'OrderOfDays', 'Family'])
    print(f'Successfully read file {strava_merged_comment_file}')
    print(strava_export_file_with_comments_df.head())

    # Create a backup
    strava_export_file_with_comments_backup = shutil.copyfile(strava_base_path + strava_merged_comment_file + '.csv',
                                                            strava_base_path + 'sicherungskopien/' + strava_merged_comment_file + '-' + datetime.now().strftime("%Y-%m-%d-%H-%M") +'.csv')




    # In[61]:


    # 2. Merge with export file

    if strava_export_file_with_comments_df.empty:
        print("The comment file is still empty. Only header names will be added.")

        df2_with_headers = pd.DataFrame(columns=['Name', 'OrderOfDays', 'Family'])
        # Combine DF1 with empty DF2's headers
        strava_merged_file_df = pd.concat([strava_export_file_without_duplicates_df, df2_with_headers], axis=1)
    else:
        print("Comment file will be merged with export file.")
        # Perform the merge if DF2 is not empty
        strava_merged_file_df = pd.merge(strava_export_file_without_duplicates_df,strava_export_file_with_comments_df, on=["Path", "Time", "activityType"], how = "inner")
        print(strava_merged_file_df.head())
        
    strava_merged_file_df.to_csv(strava_base_path + strava_merged_comment_file + '.csv', index=False)

    # 3. Create a backup of merged file (CSV)
    strava_export_file_with_comments_backup = shutil.copyfile(strava_base_path + strava_merged_comment_file + '.csv', strava_base_path + 'sicherungskopien/' + strava_merged_comment_file + '-' + datetime.now().strftime("%Y-%m-%d-%H-%M") +'.csv')



    # In[62]:


    # 4. Manually put in comments

    # 5. Read comment (merged) file again (CSV) -> final df
    strava_final_file_df = read_csv_with_separators(strava_base_path + strava_merged_comment_file + '.csv',
                                                    strava_export_file_with_comments_dtypes,['Time', 'activityType', 'Path', 'Name', 'OrderOfDays', 'Family'])

    # Convert to datetime after reading CSV because not all times are in the exact same format
    # Format 1: 2021-09-03T21:37:01.973Z
    # Format 2: 2013-07-15T15:28:07Z
    strava_final_file_df['Time'] = pd.to_datetime(strava_final_file_df['Time'], format='ISO8601')


    # Add GPX filepath to merged file after it was extracted
    strava_final_file_df['Path'] = strava_final_file_df['Path'].apply(remove_gz)

    # Rename date column to be consistent with Garmin data
    strava_final_file_df.rename(columns={'Time': 'Date'}, inplace=True)

    print(strava_final_file_df.sort_values(by='Date', ascending = False).head())

    strava_final_file = 'strava-final'

    # Store after modifications
    strava_final_file_df.to_csv(strava_base_path + strava_final_file + '.csv', index=False)




    # # Prepare GPX files

    # In[63]:


    # Unzip GPX files
    gz_extract(strava_base_path)
    # Source: https://gist.github.com/kstreepy/a9800804c21367d5a8bde692318a18f5


    # In[64]:


    # Read final file
    strava_merged_file_final = pd.read_csv(strava_base_path + strava_final_file + '.csv', sep=',', dtype = strava_export_file_with_comments_dtypes, usecols = ['Date', 'activityType', 'Path', 'Name', 'OrderOfDays', 'Family'],)

    print(strava_merged_file_final.head())
    # Only take hikes
    mask = strava_merged_file_final.activityType == ('hiking')
    strava_hiking_df = strava_merged_file_final[mask]
    strava_hiking_df.info()

    # Sort file
    strava_hiking_sorted = strava_hiking_df.sort_values(['Family','Name','Date']).Path.to_list()
    strava_hiking_sorted

    # Save filtered file as CSV
    strava_hiking_df.to_csv(strava_base_path + strava_final_file + '-hiking.csv')



    #mehrtagestouren=filtered_trails_file[filtered_trails_file.Family=='Mehrtagestour'].sort_values(['Family', 'Name', 'Date']).Path.to_list()

    # Only take hikes
    #mask = strava_merged_file_final.activityType == ('hiking')
    #strava_hiking_df = strava_merged_file_final[mask]
    #strava_hiking_df.head()

    # Save filtered file as CSV
    #strava_hiking_df.to_csv(strava_base_path + strava_final_file + '-hiking.csv')

    # Sort file
    #strava_hiking_sorted = strava_hiking_df.sort_values(['Family','Name','Date']).Path.to_list()

    strava_hiking_file_df = pd.read_csv(strava_base_path + strava_final_file + '-hiking.csv', sep=',', dtype = strava_export_file_with_comments_dtypes, usecols = ['Date', 'activityType', 'Path', 'Name', 'OrderOfDays', 'Family'],)


    mask_by_trail_family = strava_hiking_file_df.Name == ('Tauern Hoehenweg')
    #mask_by_trail_family = strava_hiking_file_df.Family == ('Mehrtagestouren')

    # Contains only path
    tracks_to_display = strava_hiking_file_df[mask_by_trail_family].sort_values(['Family', 'Name', 'Date']).Path.to_list()
    tracks_to_display_df = strava_hiking_file_df[mask_by_trail_family]

    #mehrtagestouren_df = strava_hiking_df[mask_by_trail_family]
    # Set number of tracks to be displayed on the map
    # Pass an integer to display less
    numberOfTracks="all"

    base_path = '/Users/ronja/Documents/Dateien/tech/gpx/'
    map_name = base_path + 'strava.html'
    gpx_file_path = strava_base_path + 'output/'

    create_map(gpx_file_path, tracks_to_display, tracks_to_display_df, map_name, plot_method='poly_line', zoom_level=6, add_trail_info=True, mark_track_terminals=True, track_terminal_radius_size=100, map_type='regular', number_of_tracks=numberOfTracks)


    print(map_name)


    # Set working directory to base_path
    os.chdir(base_path)
    display(IFrame(src='strava.html', width=1000, height=500))


if __name__ == "__main__":
    main()