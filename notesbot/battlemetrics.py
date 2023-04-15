import asyncio, datetime, json,aiohttp, validators

from datetime import datetime
import datetime
from datetime import timezone

from unicodedata import name
from fuzzywuzzy import fuzz

# noinspection SpellCheckingInspection
class BMAPI:
    def __init__(self):
        # Suggestion: Use TOML instead of JSON for configuration. It is more convinient.
        with open("./json/config.json", "r") as config_file:
            mytokens = json.load(config_file)
        self.config = mytokens
        self.url_base = "https://api.battlemetrics.com/"
        self.bmtoken = f"Bearer {mytokens['battlemetrics_token']}"
        self.vpntoken = mytokens["vpn_token"]
        self.steamtoken = mytokens["steam_token"]
        self.rustbannedapi = mytokens["rustbanned_token"]

    async def getbanlist(self, orgid, pagesize):
        bmtoken = f'Bearer {self.config["battlemetrics_token"]}'
        url = f"https://api.battlemetrics.com/bans?filter[organization]={orgid}&include=user,server&page[size]={pagesize}"
        response = ""
        async with aiohttp.ClientSession(headers={"Authorization": bmtoken}) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data
    
    async def GetServerInfo(self, serverid):
        url = f"https://api.battlemetrics.com/servers/{serverid}"
        async with aiohttp.ClientSession(headers={"Authorization": self.bmtoken}) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data
    
    async def getbanlist_server(self, serverid, pagesize):
        bmtoken = f'Bearer {self.config["battlemetrics_token"]}'
        url = f"https://api.battlemetrics.com/bans?filter[server]={serverid}&page[size]={pagesize}"
        response = ""
        async with aiohttp.ClientSession(headers={"Authorization": bmtoken}) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data
    
    async def get_names(self, bm_id):

        response = ""
        my_headers = {
            "Authorization": f"{self.config['battlemetrics_token']}",
            "Content-Type": "application/json",
        }
        url = f"https://api.battlemetrics.com/players/{bm_id}"
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url, params={"include": "identifier"}) as r:
                response = await r.json()
        data = response
        response = data
        usefuldata = response["included"]
        names = []
        for identifier in usefuldata:
            if identifier["attributes"]["type"] == "name":
                names.append(identifier["attributes"]["identifier"])
        return names

    async def compare(self, person1, person2):
        samenames = []
        for name1 in person1:
            for name2 in person2:
                match_ratio = fuzz.ratio(name1, name2)
                samenames.append(
                    {"match_ratio": match_ratio, "name1": name1, "name2": name2}
                )
        sorted_name_matches = sorted(
            samenames, key=lambda k: k["match_ratio"], reverse=True
        )
        return sorted_name_matches[:5]

    async def get_ids(self, submittedtext: str):
        userinfo = {"bmid": 0, "steamid": 0}
        bmid = 0
        steamid = 0
        # Convert the submitted URL or ID into a Battlemetrics ID.
        if validators.url(submittedtext):  # If it's a link, check what type
            mysplit = submittedtext.split("/")

            if mysplit[3] == "id":
                steamid = await self.get_id_from_steam(mysplit[4])

            if mysplit[3] == "profiles":
                steamid = mysplit[4]

            if mysplit[3] == "rcon":
                bmid = mysplit[5]
        else:  # Make sure it's a steam ID and then move on.
            if len(submittedtext) != 17:
                return userinfo
            steamid = submittedtext

        if not steamid and not bmid:
            return userinfo

        if steamid:
            bmid = await self.search_bm(steamid)
        if bmid:
            userinfo = {"steamid": steamid, "bmid": bmid}
        return userinfo

    async def stats(self, bmid):
        kda_results_day = await self.kda_day(bmid)

        kda_results_week = await self.kda_week(bmid)
        stats = {"kills_day": 0, "deaths_day": 0, "kills_week": 0, "deaths_week": 0}

        for i in kda_results_day["data"]:
            if (
                i.get("attributes")
                and i["attributes"].get("data")
                and i["attributes"]["data"].get("killer_id")
            ):
                if i["attributes"]["data"]["killer_id"] == int(bmid):
                    stats["kills_day"] = stats["kills_day"] + 1
                else:
                    stats["deaths_day"] = stats["deaths_day"] + 1

        for i in kda_results_week["data"]:
            if (
                i.get("attributes")
                and i["attributes"].get("data")
                and i["attributes"]["data"].get("killer_id")
            ):
                if i["attributes"]["data"]["killer_id"] == int(bmid):
                    stats["kills_week"] = stats["kills_week"] + 1
                else:
                    stats["deaths_week"] = stats["deaths_week"] + 1

        while kda_results_day["links"].get("next"):
            myextension = kda_results_day["links"]["next"]
            kda_results_day = await self.additional_data(myextension)
            await asyncio.sleep(0.2)
            for i in kda_results_day["data"]:
                if (
                    i.get("attributes")
                    and i["attributes"].get("data")
                    and i["attributes"]["data"].get("killer_id")
                ):
                    if i["attributes"]["data"]["killer_id"] == int(bmid):
                        stats["kills_day"] = stats["kills_day"] + 1
                    else:
                        stats["deaths_day"] = stats["deaths_day"] + 1

        while kda_results_week["links"].get("next"):
            myextension = kda_results_week["links"]["next"]
            kda_results_week = await self.additional_data(myextension)
            await asyncio.sleep(0.2)
            for i in kda_results_week["data"]:
                if (
                    i.get("attributes")
                    and i["attributes"].get("data")
                    and i["attributes"]["data"].get("killer_id")
                ):
                    if i["attributes"]["data"]["killer_id"] == int(bmid):
                        stats["kills_week"] = stats["kills_week"] + 1
                    else:
                        stats["deaths_week"] = stats["deaths_week"] + 1
        return stats

    async def playernotes(self, bmid):

        url_extension = f"players/{bmid}/relationships/notes?include=user,organization&page[size]=100"
        url = f"{self.url_base}{url_extension}"
        my_headers = {"Authorization": self.bmtoken}
        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        notemaker_name, organization_name, notes, notemaker_id, organization_id = (
            "Autogenerated",
            0,
            {},
            0,
            0,
        )
        for a in data["data"]:
            organization_id = a["relationships"]["organization"]["data"]["id"]
            if a["relationships"].get("user"):
                notemaker_id = a["relationships"]["user"]["data"]["id"]
            noteid = a["id"]
            note = a["attributes"]["note"]
            for b in data["included"]:
                if notemaker_id:
                    if b["type"] == "user":
                        if b["id"] == notemaker_id:
                            notemaker_name = b["attributes"]["nickname"]
                if b["type"] == "organization":
                    if b["id"] == organization_id:
                        organization_name = b["attributes"]["name"]
            notes[noteid] = {
                "noteid": noteid,
                "organization_id": organization_id,
                "notemaker_id": notemaker_id,
                "organization_name": organization_name,
                "notemaker_name": notemaker_name,
                "note": note,
            }
        return notes

    async def relatedplayers(self, bmid):
        """Grabs the information of all related players."""
        url_extension = (
            f"players/{bmid}/relationships/related-identifiers?version=^0.1.0"
            f"&filter[matchIdentifiers]=ip"
            f"&filter[identifiers]=ip&include=player,identifier&page[size]=100"
        )
        url = f"{self.url_base}{url_extension}"

        my_headers = {"Authorization": self.bmtoken}

        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                try:
                    response = await r.json()
                except:
                    altinfo = {}
                    timeout = (
                        "I was unable to gather the related players information as the request timed out.\n "
                        "Please refer to their battlemetrics page for additional information."
                    )
                    altinfo["proxycount"] = 0
                    altinfo["relatedcount"] = 0
                    altinfo["timeout"] = timeout
                    return altinfo

                if r.status != 200:

                    altinfo = {}
                    timeout = (
                        "I was unable to gather the related players information as the request timed out.\n "
                        "Please refer to their battlemetrics page for additional information."
                    )
                    altinfo["proxycount"] = 0
                    altinfo["relatedcount"] = 0
                    altinfo["timeout"] = timeout
                    return altinfo

        data = response

        related, processed, altinfo, relatedcount, proxycount = [], [], {}, 0, 0

        if data["data"]:
            for d in data["data"]:
                if d.get("attributes"):
                    if d["attributes"].get("type"):
                        if d["attributes"]["type"] == "ip":
                            if d["attributes"].get("identifier"):
                                userip = d["attributes"]["identifier"]
                                searchedip = await self.search_ip(userip)
                                if (
                                    searchedip["security"]["vpn"]
                                    or searchedip["security"]["proxy"]
                                    or searchedip["security"]["tor"]
                                    or searchedip["security"]["relay"]
                                ):
                                    if (
                                        d["type"] == "relatedIdentifier"
                                        and d.get("attributes")
                                        and d["attributes"]["type"] == "ip"
                                    ):
                                        if d["attributes"]["metadata"].get(
                                            "connectionInfo"
                                        ):
                                            for rp in d["relationships"][
                                                "relatedPlayers"
                                            ]["data"]:
                                                proxycount += 1
                                    continue
                            else:
                                if (
                                    d["attributes"]["metadata"]["connectionInfo"]["tor"]
                                    or d["attributes"]["metadata"]["connectionInfo"][
                                        "datacenter"
                                    ]
                                    or d["attributes"]["metadata"]["connectionInfo"][
                                        "proxy"
                                    ]
                                ):
                                    for rp in d["relationships"]["relatedPlayers"][
                                        "data"
                                    ]:
                                        proxycount += 1
                                    continue
                if d["type"] == "relatedIdentifier":
                    if (
                        d["type"] == "relatedIdentifier"
                        and d.get("attributes")
                        and d["attributes"]["type"] == "ip"
                    ):
                        if d["attributes"]["metadata"].get("connectionInfo"):
                            for rp in d["relationships"]["relatedPlayers"]["data"]:
                                if not rp["id"] in related and not rp["id"] == bmid:
                                    related.append(rp["id"])

            relatedcount = len(related)

            count = 0
            if relatedcount:
                for d in data["included"]:
                    if d["type"] == "identifier":
                        altbmid = d["relationships"]["player"]["data"]["id"]
                        if altbmid in related and altbmid not in processed:
                            processed.append(altbmid)
                            # Possible Bug: Seems like noone cares about this variable
                            # noinspection PyUnusedLocal
                            # proxy = d["attributes"]["metadata"]["connectionInfo"]["proxy"]

                            altinfo[altbmid] = {
                                "proxy": "No",
                                "bmid": altbmid,
                                "playerinfo": "pi",
                                "notes": "Notes",
                                "serverbans": "serverbans",
                                "gamebans": "gamebans",
                                "country": d["attributes"]["metadata"]["country"],
                                "lastcheck": d["attributes"]["metadata"]["lastCheck"],
                                "isp": d["attributes"]["metadata"]["connectionInfo"][
                                    "isp"
                                ],
                            }
                            count += 1

        altinfo["proxycount"] = proxycount
        altinfo["relatedcount"] = relatedcount
        altinfo["timeout"] = ""
        return altinfo

    async def serverbans(self, bmid):
        url_extension = f"bans?filter[player]={bmid}&include=user,server"
        url = f"{self.url_base}{url_extension}"
        my_headers = {"Authorization": self.bmtoken}

        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        bans, banner, bancount = {}, "", 0

        if data["meta"]["total"] > 0:
            for d in data["data"]:
                banid = d["id"]
                banreason = d["attributes"]["reason"]
                expires = (
                    d["attributes"]["expires"]
                    if d["attributes"]["expires"]
                    else "Never"
                )
                bandate = d["attributes"]["timestamp"]
                bannote = d["attributes"]["note"]
                bandate = bandate.split("T")
                bandate = bandate[0]
                servername = "Unknown"
                banner = "Unknown"
                banreason = 'Unknown'
                serverid = 0
                if d['relationships'].get('server'):
                    serverid = d["relationships"]["server"]["data"]["id"]
                    
                    for i in data["included"]:
                        if i["type"] == "server":
                            if i["id"] == serverid:
                                servername = i["attributes"]["name"]
                    x = banreason.split("|")
                    banreason = x[0]
                    if d["relationships"].get("user"):
                        banner_id = d["relationships"]["user"]["data"]["id"]
                        for b in data["included"]:
                            if b["type"] == "user":
                                banner = (
                                    b["attributes"]["nickname"]
                                    if b["attributes"]["id"] == banner_id
                                    else "Autoban"
                                )

                bans[bancount] = {
                    "bandate": bandate,
                    "expires": expires,
                    "bannote": bannote,
                    "banid": banid,
                    "banreason": banreason,
                    "servername": servername,
                    "serverid": serverid,
                    "banner": banner,
                }
                bancount += 1
        return bans

    async def baninfo(self, banid):
        """Takes a BANID and grabs the ban information from battlemetrics

        Args:
            bmid (int): Requires a battlemetrics banid
            
        Returns:
            dict: reason, timestamp, note, steamid, name, profileurl, expires, bmid, server, organization, banner
        """
        url_extension = f"bans/{banid}?include=server,user,organization"
        url = f"{self.url_base}{url_extension}"

        my_headers = {"Authorization": self.bmtoken}

        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response

        baninfo = {
            "reason": data["data"]["attributes"]["reason"],
            "timestamp": data["data"]["attributes"]["timestamp"],
            "note": data["data"]["attributes"]["note"],
            "steamid": data["data"]["attributes"]["identifiers"][0]["identifier"],
            "name": "None Specified",
            "profileurl": "None Specified",
            "expires": 0,
            "bmid": 0,
            "server": "None Specified",
            "organization": "None Specified",
            "banner": "None Specified",
        }
        if data["data"]["attributes"]["identifiers"][0].get("metadata"):
            baninfo["name"] = data["data"]["attributes"]["identifiers"][0]["metadata"][
                "profile"
            ]["personaname"]
            baninfo["profileurl"] = data["data"]["attributes"]["identifiers"][0][
                "metadata"
            ]["profile"]["profileurl"]
        baninfo["expires"] = data["data"]["attributes"]["expires"]
        baninfo["bmid"] = data["data"]["relationships"]["player"]["data"]["id"]
        for i in data["included"]:
            if i["type"] == "server":
                baninfo["server"] = i["attributes"]["name"]
            if i["type"] == "organization":
                baninfo["organization"] = i["attributes"]["name"]
            if i["type"] == "user":
                baninfo["banner"] = i["attributes"]["nickname"]
        return baninfo

    # Grabs all the information about the user.
    async def playerinfo(self, bmid, action):
        """Takes the BMID and queries the battlemetrics API for the users player information and returns it.

        Args:
            bmid (int): Requires a battlemetrics BMID
            action (str): Set to single if you want the Kill/death info (Can delay the bot.)
            
        Returns:
            dict: playername, rusthours, aimtrain, steamurl, steamid, avatar, stats(if set to single)
        """
        url_extension = f"players/{bmid}?include=server,identifier&fields[server]=name"
        url = f"{self.url_base}{url_extension}"
        response = ""
        async with aiohttp.ClientSession(
            headers={"Authorization": self.bmtoken}
        ) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        #with open("playerinfo.json", "w") as f:
        #    f.write(json.dumps(data, indent=4))
        steamid, avatar, steamurl, rusthours, aimtrain = None, None, "", 0, 0

        if not data.get("included"):
            return steamid

        for a in data["included"]:
            if a["type"] == "identifier":
                if a.get("attributes"):
                    if a["attributes"]["type"] == "steamID":
                        steamid = a["attributes"]["identifier"]
                        if a["attributes"].get("metadata"):
                            if a["attributes"]["metadata"].get("profile"):
                                steamurl = a["attributes"]["metadata"]["profile"][
                                    "profileurl"
                                ]
                                avatar = a["attributes"]["metadata"]["profile"][
                                    "avatarfull"
                                ]
            else:
                servername = a["attributes"]["name"].lower()
                if a["relationships"]["game"]["data"]["id"] == "rust":
                    rusthours += a["meta"]["timePlayed"]
                    currplayed = a["meta"]["timePlayed"]

                    if any(
                        [
                            cond in servername
                            for cond in ["rtg", "aim", "ukn", "arena", "combattag"]
                        ]
                    ):
                        aimtrain += currplayed

        rusthours = rusthours / 3600
        rusthours = round(rusthours, 2)
        aimtrain = aimtrain / 3600
        aimtrain = round(aimtrain, 2)
        playername = data["data"]["attributes"]["name"]

        stats = "None"
        if action == "single":
            stats = await self.stats(bmid)

        playerinfo = {
            "playername": playername,
            "rusthours": rusthours,
            "aimtrain": aimtrain,
            "steamurl": steamurl,
            "steamid": steamid,
            "avatar": avatar,
            "stats": stats,
        }
        return playerinfo

    async def search_bm(self, steamid):
        """Takes a steam ID and converts it into a BM id for use."""
        url_extension = f"players?filter[search]={steamid}&include=identifier"
        url = f"{self.url_base}{url_extension}"
        my_headers = {"Authorization": self.bmtoken}
        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data["data"][0]["id"] if data["data"] else ""

    async def get_id_from_steam(self, url):
        """Takes the URL (well part of it) and returns a steam ID"""

        url = (
            f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?format=json&"
            f"key={self.steamtoken}&vanityurl={url}&url_type=1"
        )
        #?key=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX&format=json&input_json={steamid: 76561197972495328}
        data = ""
        async with aiohttp.ClientSession(
            headers={"Authorization": self.steamtoken}
        ) as session:

            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data["response"]["steamid"] if data["response"]["steamid"] else 0

    async def gamebans(self, steamid):
        """Connects to the rustbanned api and returns any gamebans the user has."""
        searchurl = "https://rustbanned.com/api/eac_ban_check_v2.php"
        payload = {"apikey": f"{self.rustbannedapi}", "steamid64": steamid}
        headers = {"user-agent": "Gnomes App"}
        response = ""
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                url=searchurl, params=payload, allow_redirects=True
            ) as r:
                response = await r.json()
        data = response
        return data["response"][0]

    async def kda_day(self, bmid):
        dayago = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=24)
        dayago = str(dayago).replace("+00:00", "Z:")
        dayago = dayago.replace(" ", "T")
        url_extension = (
            f"activity?version=^0.1.0&tagTypeMode=and"
            f"&filter[timestamp]={dayago}"
            f"&filter[types][whitelist]=rustLog:playerDeath:PVP,"
            f"rustLog:playerDeath:cold,"
            f"rustLog:playerDeath:died,"
            f"rustLog:playerDeath:fall,"
            f"rustLog:playerDeath:blunt,"
            f"rustLog:playerDeath:entity,"
            f"rustLog:playerDeath:drowned,"
            f"rustLog:playerDeath:suicide,"
            f"rustLog:playerDeath:bleeding"
            f"&filter[players]={bmid}&include=organization,user&page[size]=100"
        )
        url = f"{self.url_base}{url_extension}"
        my_headers = {"Authorization": self.bmtoken}
        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data

    async def kda_week(self, bmid):
        weekago = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=168)
        weekago = str(weekago).replace("+00:00", "Z:")
        weekago = weekago.replace(" ", "T")
        url_extension = (
            f"activity?version=^0.1.0&tagTypeMode=and"
            f"&filter[timestamp]={weekago}"
            f"&filter[types][whitelist]=rustLog:playerDeath:PVP,"
            f"rustLog:playerDeath:cold,"
            f"rustLog:playerDeath:died,"
            f"rustLog:playerDeath:fall,"
            f"rustLog:playerDeath:blunt,"
            f"rustLog:playerDeath:entity,"
            f"rustLog:playerDeath:drowned,"
            f"rustLog:playerDeath:suicide,"
            f"rustLog:playerDeath:bleeding"
            f"&filter[players]={bmid}&include=organization,user&page[size]=100"
        )
        url = f"{self.url_base}{url_extension}"
        my_headers = {"Authorization": self.bmtoken}
        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data

    async def additional_data(self, extension: str):
        response = ""
        async with aiohttp.ClientSession(
            headers={"Authorization": self.bmtoken}
        ) as session:
            async with session.get(url=extension) as r:
                response = await r.json()
        data = response
        return data

    async def search_ip(self, ip):
        url = f"https://vpnapi.io/api/{ip}?key={self.vpntoken}"
        response = ""
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data