#!/usr/bin/env python
"""
CGNX script to retrieve PCM data and Provisioned Capacity
By default, queries for PCM data over the past 24 hours, unless specified otherwise.

tkamath@paloaltonetworks.com

Version: 1.0.0b3
"""
import cloudgenix
import pandas as pd
import os
import sys
import argparse
import logging
import datetime
import time



# Global Vars
SDK_VERSION = cloudgenix.version
SCRIPT_NAME = 'CloudGenix: Get Path Capacity'


# Set NON-SYSLOG logging to use function name
logger = logging.getLogger(__name__)

try:
    from cloudgenix_settings import CLOUDGENIX_AUTH_TOKEN

except ImportError:
    # will get caught below.
    # Get AUTH_TOKEN/X_AUTH_TOKEN from env variable, if it exists. X_AUTH_TOKEN takes priority.
    if "X_AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
    elif "AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
    else:
        # not set
        CLOUDGENIX_AUTH_TOKEN = None

try:
    from cloudgenix_settings import CLOUDGENIX_USER, CLOUDGENIX_PASSWORD

except ImportError:
    # will get caught below
    CLOUDGENIX_USER = None
    CLOUDGENIX_PASSWORD = None


RANGE = "RANGE"

sid_sname = {}
sname_sid = {}
lid_lname = {}
wid_wname = {}
lid_label = {}
wid_wtype = {}


def create_dicts(cgx_session):

    #
    # Get Sites
    #
    resp = cgx_session.get.sites()
    if resp.cgx_status:
        sitelist = resp.cgx_content.get("items", None)
        for site in sitelist:
            sid_sname[site["id"]] = site["name"]
            sname_sid[site["name"]] = site["id"]
    else:
        print("ERR: Could not retrieve Sites")
        cloudgenix.jd_detailed(resp)

    #
    # Get WAN Interface Labels & WAN Networks
    #
    resp = cgx_session.get.waninterfacelabels()
    if resp.cgx_status:
        labels = resp.cgx_content.get("items", None)
        for label in labels:
            lid_lname[label["id"]] = label["name"]
            lid_label[label["id"]] = label["label"]
    else:
        print("ERR: Could not retrieve WAN Interface Labels")
        cloudgenix.jd_detailed(resp)

    resp = cgx_session.get.wannetworks()
    if resp.cgx_status:
        nws = resp.cgx_content.get("items", None)
        for nw in nws:
            wid_wname[nw["id"]] = nw["name"]
            wid_wtype[nw["id"]] = nw["type"]
    else:
        print("ERR: Could not retrieve WAN Networks")
        cloudgenix.jd_detailed(resp)

    return


#
# Get PCM Data
#

def getpcmdata(hours, starttime, endtime, site_id, swi_id, cgx_session):

    if hours:
        END_TIME = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        START_TIME = END_TIME - datetime.timedelta(hours=int(hours))

        END_TIME_ISO = END_TIME.isoformat() + "Z"
        START_TIME_ISO = START_TIME.isoformat() + "Z"
    else:
        START_TIME_ISO = starttime
        END_TIME_ISO = endtime

    pcmdata = {}
    data = {
        "start_time": START_TIME_ISO,
        "end_time": END_TIME_ISO,
        "interval": "5min",
        "view": {
            "summary": False,
            "individual": "direction"
        },
        "filter": {
            "site": [site_id],
            "path": [swi_id]
        },
        "metrics": [
            {
                "name": "PathCapacity",
                "statistics": ["average"],
                "unit": "Mbps"
            }
        ]
    }
    resp = cgx_session.post.monitor_metrics(data=data)
    if resp.cgx_status:
        metrics = resp.cgx_content.get("metrics", None)
        for item in metrics:
            series = item.get("series", None)

            for seriesdata in series:
                view = seriesdata.get("view", None)
                direction = view["direction"]

                data = seriesdata.get("data", None)[0]
                datapoints = data.get("datapoints", None)

                if len(datapoints) > 0:
                    dp = pd.DataFrame(datapoints)
                    dp = dp.rename(columns={"value": "Value"})
                    dp = dp.rename(columns={"time": "Time"})

                    statdp = dp.Value.describe(include='all')
                    spdict = {}
                    if statdp["count"] > 0:
                        spdict["Count"] = statdp["count"]
                        spdict["Mean"] = statdp["mean"]
                        spdict["Min"] = statdp["min"]
                        spdict["Max"] = statdp["max"]
                        spdict["Std"] = statdp["std"]
                        spdict["25%"] = statdp["25%"]
                        spdict["50%"] = statdp["50%"]
                        spdict["75%"] = statdp["75%"]

                    else:
                        print("\tWARN: No {} PCM data retrieved for {}:{}".format(direction, sid_sname[site_id], swi_id))
                        spdict["Count"] = statdp["count"]
                        spdict["Mean"] = "-"
                        spdict["Min"] = "-"
                        spdict["Max"] = "-"
                        spdict["Std"] = "-"
                        spdict["25%"] = "-"
                        spdict["50%"] = "-"
                        spdict["75%"] = "-"

                else:
                    spdict = {}
                    print("\tWARN: No {} PCM data retrieved for {}:{}".format(direction, sid_sname[site_id], swi_id))
                    spdict["Count"] = 0
                    spdict["Mean"] = "-"
                    spdict["Min"] = "-"
                    spdict["Max"] = "-"
                    spdict["Std"] = "-"
                    spdict["25%"] = "-"
                    spdict["50%"] = "-"
                    spdict["75%"] = "-"

                pcmdata[direction] = spdict


    else:
        print("ERR: Could not retrieve PCM data for {}: {}".format(sid_sname[site_id], swi_id))
        cloudgenix.jd_detailed(resp)

    return pcmdata



def cleanexit(cgx_session):
    print("INFO: Logging Out")
    cgx_session.get.logout()
    sys.exit()


def go():
    ############################################################################
    # Begin Script, parse arguments.
    ############################################################################

    # Parse arguments
    parser = argparse.ArgumentParser(description="{0}.".format(SCRIPT_NAME))

    # Allow Controller modification and debug level sets.
    controller_group = parser.add_argument_group('API', 'These options change how this program connects to the API.')
    controller_group.add_argument("--controller", "-C",
                                  help="Controller URI, ex. "
                                       "C-Prod: https://api.elcapitan.cloudgenix.com",
                                  default=None)

    login_group = parser.add_argument_group('Login', 'These options allow skipping of interactive login')
    login_group.add_argument("--email", "-E", help="Use this email as User Name instead of prompting",
                             default=None)
    login_group.add_argument("--pass", "-P", help="Use this Password instead of prompting",
                             default=None)

    # Commandline for entering PCM info
    site_group = parser.add_argument_group('Capacity Measurement Filters',
                                           'Information shared here will be used to query PCM data for a site or ALL_SITES for the specified time period')
    site_group.add_argument("--sitename", "-S", help="Name of the Site. Or use keyword ALL_SITES", default="ALL_SITES")
    site_group.add_argument("--hours", "-H", help="Number of hours from now you need the PCM data queried for. Or use the keyword RANGE to provide a time range", default=24)
    site_group.add_argument("--starttime", "-ST", help="If using RANGE, Start time in format YYYY-MM-DDTHH:MM:SSZ", default=None)
    site_group.add_argument("--endtime", "-ET", help="If using RANGE, End time in format YYYY-MM-DDTHH:MM:SSZ", default=None)

    args = vars(parser.parse_args())

    ############################################################################
    # Parse arguments provided via CLI
    ############################################################################
    numhours = args['hours']
    sitename = args['sitename']
    starttime = args['starttime']
    endtime = args['endtime']
    stime = None
    etime = None

    if numhours is None:
        print("ERR: Invalid number of hours.")
        sys.exit()

    if numhours == RANGE:
        if starttime is None or endtime is None:
            print("ERR: For time range, please provide both starttime and endtime in format YYYY-MM-DDTHH:MM:SSZ")
            sys.exit()

        else:
            if "." in starttime:
                stime = datetime.datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                stime = datetime.datetime.strptime(starttime, "%Y-%m-%dT%H:%M:%SZ")

            if "." in endtime:
                etime = datetime.datetime.strptime(endtime, "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                etime = datetime.datetime.strptime(endtime, "%Y-%m-%dT%H:%M:%SZ")

            numhours = None

    else:
        numhours = int(numhours)
        if numhours <= 0:
            print("ERR: Invalid number of hours.")
            sys.exit()

    if sitename is None:
        print("INFO: No site filter configured. PCM measurements will be queried for ALL Sites")
    ############################################################################
    # Instantiate API & Login
    ############################################################################

    cgx_session = cloudgenix.API(controller=args["controller"], ssl_verify=False)
    print("{0} v{1} ({2})\n".format(SCRIPT_NAME, SDK_VERSION, cgx_session.controller))

    # login logic. Use cmdline if set, use AUTH_TOKEN next, finally user/pass from config file, then prompt.
    # figure out user
    if args["email"]:
        user_email = args["email"]
    elif CLOUDGENIX_USER:
        user_email = CLOUDGENIX_USER
    else:
        user_email = None

    # figure out password
    if args["pass"]:
        user_password = args["pass"]
    elif CLOUDGENIX_PASSWORD:
        user_password = CLOUDGENIX_PASSWORD
    else:
        user_password = None

    # check for token
    if CLOUDGENIX_AUTH_TOKEN and not args["email"] and not args["pass"]:
        cgx_session.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if cgx_session.tenant_id is None:
            print("AUTH_TOKEN login failure, please check token.")
            sys.exit()

    else:
        while cgx_session.tenant_id is None:
            cgx_session.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not cgx_session.tenant_id:
                user_email = None
                user_password = None

    ############################################################################
    # Get Provisioned Capacity & PCM Data
    ############################################################################
    create_dicts(cgx_session)

    if sitename == "ALL_SITES":
        print("INFO: PCM Data for ALL Sites")
        sitelist = sid_sname.keys()

    elif sitename in sname_sid.keys():
        print("INFO: Getting PCM Data for {}".format(sitename))
        sitelist = [sname_sid[sitename]]

    else:
        print("ERR: Invalid Site Name: {}. Please reenter sitename".format(sitename))
        cleanexit(cgx_session)


    provisioned_data = pd.DataFrame()
    for sid in sitelist:
        print("{}".format(sid_sname[sid]))
        resp = cgx_session.get.waninterfaces(site_id=sid)
        if resp.cgx_status:
            swilist = resp.cgx_content.get("items", None)
            print("\tNum WAN Interfaces: {}".format(len(swilist)))
            df = {}
            for swi in swilist:
                df["site_name"] = sid_sname[sid]
                df["site_id"] = sid
                df["circuit_name"] = swi["name"]
                df["circuit_id"] = swi["id"]
                df["circuit_label"] = lid_lname[swi["label_id"]]
                df["wan_network"] = wid_wname[swi["network_id"]]
                df["wan_network_type"] = swi["type"]
                df["upstream_bw_provisioned"] = swi["link_bw_up"]
                df["downstream_bw_provisioned"] = swi["link_bw_down"]
                df["bwc_enabled"] = swi["bwc_enabled"]
                df["lqm_enabled"] = swi["lqm_enabled"]

                data = getpcmdata(hours=numhours, starttime=starttime, endtime=endtime, site_id=sid, swi_id=swi["id"], cgx_session=cgx_session)
                if data:
                    ingressdata = data["Ingress"]
                    egressdata = data["Egress"]
                else:
                    #
                    # Could not retrieve data for the circuit. Nothing to extract -> continue to next SWI
                    #
                    continue

                df["upstream_bw_pcm_mean"] = egressdata["Mean"]
                df["upstream_bw_pcm_min"] = egressdata["Min"]
                df["upstream_bw_pcm_max"] = egressdata["Max"]
                df["upstream_bw_pcm_std"] = egressdata["Std"]
                df["upstream_bw_pcm_25pct"] = egressdata["25%"]
                df["upstream_bw_pcm_50pct"] = egressdata["50%"]
                df["upstream_bw_pcm_70pct"] = egressdata["75%"]

                df["downstream_bw_pcm_mean"] = ingressdata["Mean"]
                df["downstream_bw_pcm_min"] = ingressdata["Min"]
                df["downstream_bw_pcm_max"] = ingressdata["Max"]
                df["downstream_bw_pcm_std"] = ingressdata["Std"]
                df["downstream_bw_pcm_25pct"] = ingressdata["25%"]
                df["downstream_bw_pcm_50pct"] = ingressdata["50%"]
                df["downstream_bw_pcm_70pct"] = ingressdata["75%"]
                dp = pd.DataFrame([df])
                provisioned_data = pd.concat([provisioned_data, dp], ignore_index=True)

                time.sleep(0.5)

    ############################################################################
    # Save Data to CSV
    ############################################################################
    # get time now.
    curtime_str = datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S')

    # create file-system friendly tenant str.
    tenant_str = "".join(x for x in cgx_session.tenant_name if x.isalnum()).lower()

    # Set filename
    csvfile = os.path.join('./', '%s_pcmdata_%s.csv' % (tenant_str, curtime_str))
    print("INFO: Saving PCM data to file {}".format(csvfile))
    provisioned_data.to_csv(csvfile, index=False)

    ############################################################################
    # Logout to clear session.
    ############################################################################
    cleanexit(cgx_session)

if __name__ == "__main__":
    go()
