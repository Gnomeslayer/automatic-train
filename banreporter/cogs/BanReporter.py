import json, http3, discord
import aiohttp
from discord.ext import commands, tasks
from discord.utils import get
import traceback

HTTP = http3.AsyncClient()


class BanReporter_admin(commands.Cog):
    def __init__(self, client):
        print("[Cog] BanReporter has been initiated")
        self.client = client
        self.BanListCache = {}
        self.totalbans = 0
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        self.config = config
        self.banchecker.start()

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
      
    @tasks.loop(seconds=30)
    async def banchecker(self):
        servers = ''
        with open('./json/servercfg.json', 'r') as f:
            servers = json.load(f)
        
        for server in servers:
            banList = await self.getbanlist(server['orgid'], server['pagesize'])
            self.totalbans = banList['meta']['total']
            banList = await self.processlist(banList)
            banList = await self.compareList(server['orgid'], banList, self.config['first_run_spam'])
            # The Embed
            for guild in self.client.guilds:
                guildid = str(guild.id)
                PublicChannel = ''
                PrivateChannel = ''
                if guildid in server['guilds']:
                    if server['guilds'][guildid].get('PublicChannel'):
                        PublicChannel = guild.get_channel(server['guilds'][guildid]['PublicChannel'])
                    if server['guilds'][guildid].get('PrivateChannel'):
                        PrivateChannel = guild.get_channel(server['guilds'][guildid]['PrivateChannel'])
                for i in banList:
                    PublicEmbed = await self.PublicView(bandata=banList[i], orgname=server['name'], color=server['color'], logo=server['logo'])
                    PrivateEmbed = await self.PrivateView(bandata=banList[i], orgname=server['name'], color=server['color'], logo=server['logo'])
                    if PublicChannel:
                        await PublicChannel.send(embed=PublicEmbed)
                    if PrivateChannel:
                        await PrivateChannel.send(embed=PrivateEmbed)

    @banchecker.before_loop
    async def banchecker_wait_for_ready(self):
        await self.client.wait_until_ready()
    
    async def PrivateView(self, bandata, orgname, color, logo):
        embedVar = discord.Embed(
                title=f"{orgname}", color=int(color, base=16)
            )
        embedVar.add_field(
            name="Player Information",
            value=f"{bandata['playername']} - {bandata['steamid']}",
            inline=False,
        )
        bantime = bandata["timestamp"].split("T")
        embedVar.add_field(
            name="Ban Information",
            value=f"Ban Time: {bantime[0]}\nExpires: {bandata['expires']} \n ```{bandata['reason']}```",
            inline=False,
        )
        if bandata['profileurl'] != 'Unknown':
            embedVar.add_field(
                name="Links",
                value=f"Profile: [{bandata['steamid']}]({bandata['profileurl']})\nBattlemetrics: [Profile](https://www.battlemetrics.com/rcon/players/{bandata['bmid']})\nNote: [Battlemetrics note](https://www.battlemetrics.com/rcon/bans/edit/{bandata['banid']})",
                inline=False,
            )
        else:
            embedVar.add_field(
                name="Links",
                value=f"Profile: {bandata['steamid']}",
                inline=False,
            )
        
        if not bandata['note']:
            embedVar.add_field(name="Note", value=f"```No note was submitted```", inline=False)
        else:
            embedVar.add_field(name="Note", value=f"```{bandata['note']}```", inline=False)
            
        embedVar.set_thumbnail(url=logo)
        embedVar.set_footer(text="Developed by Gnomeslayer#5551")
        return embedVar
    
    async def PublicView(self, bandata, orgname, color, logo):
        embedVar = discord.Embed(
                title=f"{orgname}", color=int(color, base=16)
            )
        embedVar.add_field(
            name="Player Information",
            value=f"{bandata['playername']} - {bandata['steamid']}",
            inline=False,
        )
        bantime = bandata["timestamp"].split("T")
        embedVar.add_field(
            name="Ban Information",
            value=f"Ban Time: {bantime[0]}\nExpires: {bandata['expires']} \n ```{bandata['reason']}```",
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
            
        embedVar.set_thumbnail(url=logo)
        embedVar.set_footer(text="Developed by Gnomeslayer#5551")
        return embedVar
    
    async def getbanlist(self, orgid, pagesize):
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        bmtoken = f'Bearer {config["battlemetrics_token"]}'
        url = f"https://api.battlemetrics.com/bans?filter[organization]={orgid}&include=user,server&page[size]={pagesize}"
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

    async def compareList(self, orgid, banlist, firstrunspam):
        newList = {}
        
        if orgid not in self.BanListCache:
            self.BanListCache[orgid] = []
        
        if not firstrunspam and not self.BanListCache[orgid]:
            for i in banlist:
                self.BanListCache[orgid].append(i)
        for i in banlist:
            if i not in self.BanListCache[orgid]:
                newList[i] = banlist[i]
                if len(self.BanListCache) > 100:
                    self.BanListCache[orgid][0] = i
                    self.BanListCache[orgid].pop()
                else:
                    self.BanListCache[orgid].append(i)
        return newList


async def setup(client):
    await client.add_cog(BanReporter_admin(client))