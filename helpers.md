# Source Data  
Garmin is for historic data (before Apple Watch)  
Strava is for actual data  
  
<https://github.com/liskin/strava-offline>  
1. Download activities to sqlite database  
strava-offline sqlite  
  
2. Download respective GPX tracks  
strava-offline gpx \--strava4-session 400q93snpu5pk1jgfp3acu13i5m7u80v
\--dir-activities-backup
/Users/ronja/Documents/dateien/tech/gpx/source-data/strava/output
\--dir-activities
/Users/ronja/Documents/dateien/tech/gpx/source-data/strava/output
\--verbose  
  
  
  
<https://github.com/evgeniyarbatov/strava2csv>  
Create CSV file out of activities folder (with gpx files)  
  
Run this in strava2csv folder  
go run main.go \\  
../output/ \\  
../gpx-file-strava.csv  
  
# Questions  
- There is a gap between Garmin & Strata data -\> What is this?  
- If columns are added to Strava CSV file, how does import tool handle
this?  
  
  
  
File structure  
  
Strava  
Time,ActivityType,Filename,Latitude,Longitude,Elevation,Cadence,Heartrate,Power  
  
  
Garmin  
Start Time;End Time;Activity ID;Activity
Name;Name;MehrtagesTourName;OrderOfDays;Family;Location  
  
  


# Python
source .venv/bin/activate 