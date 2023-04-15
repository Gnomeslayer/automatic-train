import discord
from discord import app_commands
from discord.ext import commands, tasks
import traceback
import json, aiohttp, asyncio, validators
from datetime import datetime
import datetime
from datetime import timezone
class Staff_tracker(commands.Cog):
    
    def __init__(self, client):
        print("[Cog] Staff Tracker has been initiated")
        self.client = client
        with open("config.json", "r") as f:
            config = json.load(f)
        self.config = config
        self.bmtoken = f"Bearer {config['battlemetrics_token']}"
        self.command_number = 0
    
    @app_commands.command(name="register", description="Register a server or servers discord")
    @app_commands.describe(server='Server ID')
    async def register(self, interaction: discord.Interaction, server:str, servername: str, discord:str):
        pass
    
    @commands.command()
    async def starttracking(self, ctx):
        response = await ctx.reply("I am now tracking all staff commands!")
        await ctx.message.delete()
        response = response.delete(delay=5)
        await self.staffcommand_tracker.start()
        
    @tasks.loop(minutes=30)
    async def staffcommand_tracker(self):
        admin_logs = await self.getorgactivity()
        commands = await self.sortdata(admin_logs)
        while admin_logs["links"].get("next"):
            myextension = admin_logs["links"]["next"]
            admin_logs = await self.additional_data(myextension)
            await asyncio.sleep(0.2)
            await self.sortdata(admin_logs)
            #commands.append(await self.sortdata(admin_logs))
        with open("test2.json", "w") as f:
            f.write(json.dumps(commands, indent=4))
        print("Done!")
    
    async def getorgactivity(self):
        dayago = str(datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=24))
        daysago = dayago.split(" ")
        dayago = daysago[0]
        dayago += "T00:00:00.000Z:"
        url = "https://api.battlemetrics.com/activity?version=^0.1.0&page[size]=100&filter[types][whitelist]=adminLog&filter[timestamp]=2022-08-25T00:00:00.000Z:&include=organization,user"
        my_headers = {"Authorization": self.bmtoken}
        response = ""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=my_headers) as r:
                response = await r.json()
        data = response
        with open('test.json', 'w') as f:
            f.write(json.dumps(data, indent=4))
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

    async def GetServerInfo(self, serverid):
            myservers = ''
            serverid = str(serverid)
            with open("servers.json", "r") as f:
                myservers = json.load(f)
            if serverid in myservers:
                return myservers[serverid]
            url = f"https://api.battlemetrics.com/servers/{serverid}"
            async with aiohttp.ClientSession(headers={"Authorization": self.bmtoken}) as session:
                async with session.get(url=url) as r:
                    response = await r.json()
                myservers[serverid] = {
                    "discord": "None registered. You can register a discord by using the slash command /register",
                    'name': response['data']['attributes']['name']
                }
                with open("servers.json", "w") as f:
                    f.write(json.dumps(myservers, indent=4))
                return myservers[serverid]
            
    async def sortdata(self, data):
        newdata = []
        for i in data['data']:
            if "adminLog" in i['attributes']['messageType']:
                if i['attributes']['source'] == 'user':
                    admin_nickname = i['attributes']['data']['admin_nickname']
                    with open(f"./json/command_{admin_nickname}_{self.command_number}.json", "w") as f:
                        f.write(json.dumps(i, indent=4))
            self.command_number += 1
                    #server = i['relationships']['servers']['data'][0]['id']
                    #command_run = i['attributes']['data']['metadata']['raw']
                    #timestamp = i['attributes']['timestamp']
                    #senttochannel = False
                    #command = {
                    #    "admin": admin_nickname,
                    #    "server": server,
                    #    "command_run": command_run,
                    #    "timestamp": timestamp,
                    #    "senttochannel": senttochannel
                    #}
                    #newdata.append(command)
        #return newdata
    #       "type": "activityMessage",
    #       "id": "M+vdQCTwEe2WTHEEGRKbng",
    #       "attributes": {
    #           "messageType": "adminLog:raw",
    #           "timestamp": "2022-08-26T03:36:00.019Z",
    #           "source": "user",
    #           "message": "Skull executed raw command serverinfo",
    #           "categories": [
    #               "adminLog"
    #           ],
    #           "tags": [],
    #           "data": {
    #               "metadata": {
    #                   "raw": "serverinfo"
    #               },
    #               "admin_nickname": "Skull",
    #               "command": "raw"
    #           }
    #       },
    #       "relationships": {
    #           "organizations": {
    #               "data": [
    #                   {
    #                       "type": "organization",
    #                       "id": "13771"
    #                   }
    #               ]
    #           },
    #           "servers": {
    #               "data": [
    #                   {
    #                       "type": "server",
    #                       "id": "13807895"
    #                   }
    #               ]
    #           },
    #           "users": {
    #               "data": [
    #                   {
    #                       "type": "user",
    #                       "id": "206623"
    #                   }
    #               ]
    #           },
    #           "games": {
    #               "data": [
    #                   {
    #                       "type": "game",
    #                       "id": "rust"
    #                   }
    #               ]
    #           }
    #       }
    #   },
    
async def setup(client):
    await client.add_cog(Staff_tracker(client))