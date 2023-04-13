# Prisma SDWAN (CloudGenix) Get Path Capacity
This script provides insight into provisioned circuit capacity and offers a comparison with PCM data for the specified time period.

#### Synopsis
This scripts queries the provisioned bandwidth and the PCM (Path Capacity Measurement) data for all circuits at the specified site or all sites. 
It downloads this information into a CSV file. PCM data by default is retrieved for the 24 hours. However, a specific time range can also be provided.  

#### Requirements
* Active CloudGenix Account
* Python >=3.6
* Python modules:
    * CloudGenix Python SDK >= 5.4.3b1 - <https://github.com/CloudGenix/sdk-python>

#### License
MIT

#### Installation:
 - **Github:** Download files to a local directory, manually run `getpathcapacity.py`. 

### Usage:
Get path capacity measurements for a single site:
```
./getpathcapacity.py -S Sitename 
```
Get path capacity measurements for ALL Sites:
``` 
./getpathcapacity.py -S ALL_SITES 
```
Get path capacity measurements for a number of hours:
```angular2
./getpathcapacity.py -H 24 -S Sitename
```
Get path capacity measurements for a time range:
```angular2
./getpathcapacity.py -S Sitename -H RANGE -ST 2021-03-01T00:00:00Z -ET 2021-03-03T00:00:00Z
```

Help Text:
```angular2
TanushreeMacBookPro:getpathcapacity tanushreekamath$ ./getpathcapacity.py -h
usage: getpathcapacity.py [-h] [--controller CONTROLLER] [--email EMAIL]
                          [--pass PASS] [--sitename SITENAME] [--hours HOURS]
                          [--starttime STARTTIME] [--endtime ENDTIME]

CloudGenix: Get Path Capacity.

optional arguments:
  -h, --help            show this help message and exit

API:
  These options change how this program connects to the API.

  --controller CONTROLLER, -C CONTROLLER
                        Controller URI, ex. C-Prod:
                        https://api.elcapitan.cloudgenix.com

Login:
  These options allow skipping of interactive login

  --email EMAIL, -E EMAIL
                        Use this email as User Name instead of prompting
  --pass PASS, -P PASS  Use this Password instead of prompting

Capacity Measurement Filters:
  Information shared here will be used to query PCM data for a site or
  ALL_SITES for the specified time period

  --sitename SITENAME, -S SITENAME
                        Name of the Site. Or use keyword ALL_SITES
  --hours HOURS, -H HOURS
                        Number of hours from now you need the PCM data queried
                        for. Or use the keyword RANGE to provide a time range
  --starttime STARTTIME, -ST STARTTIME
                        If using RANGE, Start time in format YYYY-MM-
                        DDTHH:MM:SSZ
  --endtime ENDTIME, -ET ENDTIME
                        If using RANGE, End time in format YYYY-MM-
                        DDTHH:MM:SSZ
TanushreeMacBookPro:getpathcapacity tanushreekamath$

```

#### Version
| Version | Build | Changes |
| ------- | ----- | ------- |
| **1.0.0** | **b3** | Support for pandas 2.0 |
|           | **b2** | Bug fix - empty datapoints in API response |
|           | **b1** | Initial Release. |


#### For more info
 * For more information on Prisma SDWAN Python SDK, go to https://developers.cloudgenix.com
 
