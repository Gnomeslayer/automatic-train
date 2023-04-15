import json, discord
import aiohttp
from discord.ext import commands, tasks
from discord.utils import get
import traceback


class Loops(commands.Cog):
    def __init__(self, client):
        print("[Cog] Loops has been initiated")
        self.client = client
        self.BanListCache = []
        self.totalbans = 0
        self.banchecker.start()
        self.statusupdater.start()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        with open("./json/config.json", "r") as f:
            config = json.load(f)
            
        commandname = str(ctx.command)
        commandauthor = ctx.author
        channel = self.client.get_channel(config["error_channel"])
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        commandrun = ""
        for i in tb:
            commandrun += f"{i}"
        with open("error_log.txt", "w") as f:
            f.write(commandrun)
        with open("error_log.txt", "rb") as f:
            await channel.send(
                content=f"Command Name: {commandname}, Author: {commandauthor}",
                file=discord.File(f, filename="error_log.txt"),
            )
    
    @tasks.loop(seconds=300)
    async def statusupdater(self):
        await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{self.totalbans} bans"))

    @statusupdater.before_loop
    async def statusupdater_wait(self):
        await self.client.wait_until_ready()
        
    @tasks.loop(seconds=30)
    async def banchecker(self):
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        banList = await self.getbanlist()
        if not self.BanListCache:
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{banList['meta']['total']} bans"))
        self.totalbans = banList['meta']['total']
        banList = await self.processlist(banList)
        banList = await self.compareList(banList, config['first_run_spam'])
        # The Embed
        channel = self.client.get_channel(config["bans_channel"])
        
        for i in banList:
            embedVar = await self.defaultembed(banList[i], config['organization_name'])
            await channel.send(embed=embedVar)

    @banchecker.before_loop
    async def banchecker_wait(self):
        await self.client.wait_until_ready()
        
    async def defaultembed(self, bandata, orgname):
        embedVar = discord.Embed(
                title=f"{orgname}", color=0x00FF00
            )
        embedVar.add_field(
            name="Player Information",
            value=f"{bandata['playername']} - {bandata['steamid']}",
            inline=False,
        )
        bantime = bandata["timestamp"].split("T")
        embedVar.add_field(
            name="Ban Information",
            value=f"Ban Time: {bantime[0]} - Expires: {bandata['expires']} \n `{bandata['reason']}`",
            inline=False,
        )
        if bandata['profileurl'] != 'Unknown':
            embedVar.add_field(
                name="Links",
                value=f"Profile: [{bandata['steamid']}]({bandata['profileurl']})",
                inline=False,
            )
        else:
            embedVar.add_field(
                name="Links",
                value=f"Profile: {bandata['steamid']}",
                inline=False,
            )
           
        if bandata['avatar'] != 'Unknown':
            embedVar.set_thumbnail(url=bandata["avatar"])
        embedVar.set_footer(text="Created by Gnomeslayer#5551")
        return embedVar
    
    
    async def gunnysembed(self, bandata, orgname):
        embedVar = discord.Embed(
                title=f"{orgname}", color=0x00FF00
            )
        embedVar.add_field(
            name="Banned Player",
            value=f"```{bandata['playername']} - {bandata['steamid']}```",
            inline=False,
        )
            
        embedVar.add_field(
            name="Ban Information",
            value=f"```{bandata['reason']} - Banning Admin {bandata['banner']}```",
            inline=False,
        )
        bantime = bandata["timestamp"].split("T")
        embedVar.add_field(
            name="Date",
            value=f"```{bantime[0]}```",
            inline=True,
        )
        embedVar.add_field(
            name="Length",
            value=f"```{bandata['expires']}```",
            inline=True
        )
        if bandata['profileurl'] != 'Unknown':
            embedVar.add_field(
                name="Links",
                value=f"Profile: [{bandata['steamid']}]({bandata['profileurl']})",
                inline=False,
            )
        else:
            embedVar.add_field(
                name="Links",
                value=f"Profile: {bandata['steamid']}",
                inline=False,
            )
            
        if bandata['avatar'] != 'Unknown':
            embedVar.set_thumbnail(url=bandata["avatar"])
        embedVar.set_footer(text="Created by Gnomeslayer#5551")
        return embedVar
    
    async def getbanlist(self):
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        bmtoken = f'Bearer {config["battlemetrics_token"]}'
        url = f"https://api.battlemetrics.com/bans?filter[organization]={config['organization_id']}&include=user,server&page[size]={config['pagesize']}"
        response = ""
        async with aiohttp.ClientSession(headers={"Authorization": bmtoken}) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response

        return data

    async def processlist(self, banlist):
        newList = {}
        admins = {}
        playername = 'Unknown'
        
        for i in banlist["included"]:
            if i["type"] == "user":
                admins[i["attributes"]["id"]] = i["attributes"]["nickname"]

        for i in banlist["data"]:
            if i["type"] == "ban":
                banid = i["id"]
                if i.get('meta') and i['meta'].get('player'):
                    playername = i["meta"]["player"]
                timestamp = i["attributes"]["timestamp"]
                expires = i["attributes"]["expires"]
                reason = i["attributes"]["reason"]
                note = i["attributes"]["note"]
                bmid = i["id"]
                banner = "Autoban"
                steamid = "unknown"
                steamurl = "unknown"
                avatar = "Unknown"
                if i["relationships"].get("user"):
                    banner = admins[i["relationships"]["user"]["data"]["id"]]
                if i['attributes'].get('identifiers') and i['attributes']['identifiers'][0].get("metadata"):
                    if playername == 'Unknown':
                        playername = i['attrbiutes']['identifiers'][0]['metadata']['profile']['personaname']
                    steamid = i["attributes"]["identifiers"][0]["metadata"][
                            "profile"]["steamid"]
                    steamurl = i["attributes"]["identifiers"][0]["metadata"][
                        "profile"
                    ]["profileurl"]
                    avatar = i["attributes"]["identifiers"][0]["metadata"][
                        "profile"
                    ]["avatarfull"]
                    
                newList[i["id"]] = {
                    "banid": banid,
                    "playername": playername,
                    "timestamp": timestamp,
                    "expires": expires,
                    "reason": reason,
                    "note": note,
                    "bmid": bmid,
                    "steamid": steamid,
                    "avatar": avatar,
                    "profileurl": steamurl,
                    "banner": banner,
                }
        
        return newList

    async def compareList(self, banlist, firstrunspam):
        newList = {}
        if not firstrunspam:
            if len(self.BanListCache) == 0:
                self.BanListCache = banlist
                
        for i in banlist:
            if i not in self.BanListCache:
                newList[i] = banlist[i]
        self.BanListCache = banlist
        return newList


async def setup(client):
    await client.add_cog(Loops(client))