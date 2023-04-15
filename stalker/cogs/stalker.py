import discord
from discord import app_commands
from discord.ext import commands, tasks
import traceback
import json, aiohttp, asyncio, validators

class Stalker(commands.Cog):
    
    def __init__(self, client):
        print("[Cog] Stalker has been initiated")
        self.client = client
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        self.config = config
        self.stalks = {}
        self.stalker.start()
    
    @app_commands.command(name="register", description="Register a server or servers discord")
    @app_commands.describe(server='Server ID')
    @app_commands.describe(servername='Server ID')
    @app_commands.describe(discord='Servers discord link')
    async def register(self, interaction: discord.Interaction, server:str, servername: str, discord:str):
        myservers = ''
        with open('./json/servers.json', 'r') as f:
            myservers = json.load(f)
        myservers[server]['discord'] = discord
        myservers[server]['name'] = servername
        
        with open('./json/servers.json', 'w') as f:
            f.write(json.dumps(myservers, indent=4))
        await interaction.response.send_message("You've successfully updated or added a servers information!")
    
    @commands.command()
    async def hunt(self, ctx, submittedinfo):
        userids = await self.get_ids(submittedinfo)
        if not userids['bmid']:
            await ctx.reply("Could not find this user.")
            return
        if userids['bmid'] in self.stalks:
            await ctx.reply("I am already hunting that user!")
            return
        stalker_channel = ctx.guild.get_channel(self.config['stalker_channel'])
        playerinfo = await self.playerinfo(userids['bmid'])
        embed = discord.Embed(
            title=f"{playerinfo['playername']} - {playerinfo['steamid']}"
        )
        embed.set_thumbnail(url=playerinfo["avatar"])
        embed.add_field(
            name="Regular Hours",
            value=f"{playerinfo['rusthours']}",
            inline=True,
        )
        embed.add_field(
            name="Aimtrain Hours",
            value=f"{playerinfo['aimtrain']}",
            inline=True,
        )
        embed.add_field(name="Links", value=f"[steam]({playerinfo['steamurl']})\n[Battlemetrics](https://www.battlemetrics.com/rcon/players/{userids['bmid']})")
        embed.set_footer(text="Developed by Gnomeslayer#5551")
        create_thread = await stalker_channel.send(f"Let the hunt begin! I am now stalking {playerinfo['playername']}")
        thread = await stalker_channel.create_thread(name=f"{playerinfo['playername']}", message=create_thread, auto_archive_duration=10080)
        await thread.send(content=f"{ctx.author.mention}", embed=embed)
        self.stalks[userids['bmid']] = {
                "thread": thread,
                "bmid": userids['bmid'],
                "start": 0,
                "stop": 0,
            }
            
        
    @commands.command()
    async def endhunt(self, ctx, submittedinfo):
        userids = await self.get_ids(submittedinfo)
        if not userids['bmid']:
            await ctx.reply("Could not find this user.")
            return
        if not userids['bmid'] in self.stalks:
            await ctx.reply('I am not even hunting that person..')
            return
        await ctx.send("The hunt has ended!")
        await self.stalks[userids['bmid']]['thread'].delete()
        del self.stalks[userids['bmid']]
                
        
    @tasks.loop(minutes=1)
    async def stalker(self):
        for i in self.stalks:
            await asyncio.sleep(1)
            playersession = await self.GetPlayerSession(i)
            serverid = playersession['relationships']['server']['data']['id']
            server = await self.GetServerInfo(serverid)
            thread = self.stalks[i]['thread']
            if not playersession['attributes']['stop']:
                playersession['attributes']['stop'] = 'Still on this server'
            if not playersession['attributes']['start'] == self.stalks[i]['start']:
                embed = discord.Embed(title=f"Session - Server ID: {serverid}")
                embed.add_field(
                    name="Server name",
                    value=f"```{server['name']}```",
                    inline=False
                )
                embed.add_field(
                    name="Server Discord",
                    value=f"```{server['discord']}```",
                    inline=False
                )
                embed.add_field(
                    name="Join time",
                    value=f"Player has joined a server```{playersession['attributes']['start']}```",
                    inline=False
                )
                embed.add_field(
                    name="Leave time",
                    value=f"```{playersession['attributes']['stop']}```",
                    inline=False
                )
                embed.set_footer(text="Developed by Gnomeslayer#5551")
                try:
                    await thread.send(embed=embed)
                except:
                    del self.stalks[self.stalks[i]]
            if playersession['attributes']['start'] == self.stalks[i]['start'] and not playersession['attributes']['stop'] == self.stalks[i]['stop']:
                embed = discord.Embed(title=f"Session - Server ID: {serverid}")
                embed.add_field(
                    name="Server name",
                    value=f"```{server['name']}```",
                    inline=False
                )
                embed.add_field(
                    name="Server Discord",
                    value=f"```{server['discord']}```",
                    inline=False
                )
                embed.add_field(
                    name="Join time",
                    value=f"```{playersession['attributes']['start']}```",
                    inline=False
                )
                embed.add_field(
                    name="Leave time",
                    value=f"Player has left the server.```{playersession['attributes']['stop']}```",
                    inline=False
                )
                embed.set_footer(text="Developed by Gnomeslayer#5551")
                try:
                    await thread.send(embed=embed)
                except:
                    del self.stalks[self.stalks[i]]
            self.stalks[i]['start'] = playersession['attributes']['start']
            self.stalks[i]['stop'] = playersession['attributes']['stop']
            
    @stalker.before_loop
    async def stalker_wait_for_ready(self):
        await self.client.wait_until_ready()
        
    async def GetPlayerSession(self, playerid):
        response = ""
        serverid = 0
        url = f"https://api.battlemetrics.com/players/{playerid}/relationships/sessions"
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.config['battlemetrics_token']}"}) as session:
            async with session.get(url=url) as r:
                response = await r.json()
            serverid = response['data'][0]['relationships']['server']['data']['id']
        await self.GetServerInfo(serverid)
        return response['data'][0]
    
    async def GetServerInfo(self, serverid):
        myservers = ''
        serverid = str(serverid)
        with open("./json/servers.json", "r") as f:
            myservers = json.load(f)
        if serverid in myservers:
            return myservers[serverid]
        url = f"https://api.battlemetrics.com/servers/{serverid}"
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {self.config['battlemetrics_token']}"}) as session:
            async with session.get(url=url) as r:
                response = await r.json()
            myservers[serverid] = {
                "discord": "None registered. You can register a discord by using the slash command /register",
                'name': response['data']['attributes']['name']
            }
            with open("./json/servers.json", "w") as f:
                f.write(json.dumps(myservers, indent=4))
            return myservers[serverid]
        

    async def get_ids(self, submittedtext: str):
        userinfo = {"bmid": 0, "steamid": 0}
        bmid = ""
        steamid = ""
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
    
    async def get_id_from_steam(self, url):
        """Takes the URL (well part of it) and returns a steam ID"""

        url = (
            f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?format=json&"
            f"key={self.config['steam_token']}&vanityurl={url}&url_type=1"
        )
        data = ""
        async with aiohttp.ClientSession(
            headers={"Authorization": self.config['steam_token']}
        ) as session:

            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data["response"]["steamid"] if data["response"]["steamid"] else 0
    
    async def search_bm(self, steamid):
        """Takes a steam ID and converts it into a BM id for use."""
        url_extension = f"players?filter[search]={steamid}&include=identifier"
        url = f"https://api.battlemetrics.com/{url_extension}"

        my_headers = {"Authorization": f"Bearer {self.config['battlemetrics_token']}"}
        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data["data"][0]["id"] if data["data"] else ""
    
    async def playerinfo(self, bmid):
        url_extension = f"players/{bmid}?include=server,identifier&fields[server]=name"
        url = f"https://api.battlemetrics.com/{url_extension}"
        response = ""
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.config['battlemetrics_token']}"}
        ) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
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

        playerinfo = {
            "playername": playername,
            "rusthours": rusthours,
            "aimtrain": aimtrain,
            "steamurl": steamurl,
            "steamid": steamid,
            "avatar": avatar,
        }
        return playerinfo
    
async def setup(client):
    await client.add_cog(Stalker(client))