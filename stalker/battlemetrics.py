import asyncio, datetime, json, traceback, discord, aiohttp, requests, validators, vdf
from discord.ext import commands

from datetime import datetime
import datetime
from datetime import timezone

from unicodedata import name
from urllib import response
from fuzzywuzzy import fuzz

with open("./json/config.json", "r") as f:
    config = json.load(f)


# noinspection SpellCheckingInspection
class Battlemetrics(commands.Cog):
    def __init__(self, client):
        print("[Cog] Battlemetrics has been initiated")
        self.client = client
        self.config = config

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        commandname = str(ctx.command)
        commandauthor = ctx.author
        channel = self.client.get_channel(self.config["error_channel"])
        if commandname in ["alts", "all", "bans", "compare", "info", "stats"]:
            await channel.send(f"Command run: {ctx.message.content}")
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

    @commands.command()
    async def all(self, ctx, submittedtext):
        bmapi = BMAPI()
        userids = await bmapi.get_ids(submittedtext)
        if not userids:
            await ctx.reply(
                f"I was unable to find that user. Are you sure you typed in their STEAM ID, STEAM URL or BM URL correctly?\n"
                f"Heres what you submitted:\n{submittedtext}"
            )
            return
        serverbans = await bmapi.serverbans(userids["bmid"])
        playerinfo = await bmapi.playerinfo(userids["bmid"], "single")
        notes = await bmapi.playernotes(userids["bmid"])
        myserverbans = await bmapi.serverbans(userids["bmid"])
        if not userids["steamid"]:
            userids["steamid"] = playerinfo["steamid"]
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
            name="Aim train hours",
            value=f"{playerinfo['aimtrain']}",
            inline=True,
        )
        embed.add_field(
            name="Links",
            value=f"[Steam]({playerinfo['steamurl']})\n[RCON](https://www.battlemetrics.com/rcon/players/{userids['bmid']})",
            inline=True,
        )
        serverbans = "No server bans"
        if myserverbans:
            serverbans = ""
            for i in myserverbans:
                banid = myserverbans[i]["banid"]
                banreason = myserverbans[i]["banreason"]
                serverbans += f"[{banreason}](https://www.battlemetrics.com/rcon/bans/edit/{banid})\n"
        embed.add_field(name="Server bans", value=f"{serverbans}", inline=False)
        ratio_day = 0
        ratio_week = 0
        if (
            playerinfo["stats"]["kills_day"] > 0
            and playerinfo["stats"]["deaths_day"] > 0
        ):
            ratio_day = round(
                playerinfo["stats"]["kills_day"] / playerinfo["stats"]["deaths_day"],
                2,
            )
        if (
            playerinfo["stats"]["kills_day"] > 0
            and playerinfo["stats"]["deaths_day"] == 0
        ):
            ratio_day = playerinfo["stats"]["kills_day"]
        if (
            playerinfo["stats"]["kills_week"] > 0
            and playerinfo["stats"]["deaths_week"] > 0
        ):
            ratio_week = round(
                playerinfo["stats"]["kills_week"] / playerinfo["stats"]["deaths_week"],
                2,
            )
        if (
            playerinfo["stats"]["kills_week"] > 0
            and playerinfo["stats"]["deaths_week"] == 0
        ):
            ratio_week = playerinfo["stats"]["kills_week"]
        embed.add_field(
            name="Statistics",
            value=f"**Last 24 Hours**\n"
            f"Kills: {playerinfo['stats']['kills_day']}\n"
            f"Deaths:{playerinfo['stats']['deaths_day']}\n"
            f"KD Ratio: {ratio_day}:1",
            inline=True,
        )
        embed.add_field(
            name="Statistics",
            value=f"Kills in the week: {playerinfo['stats']['kills_week']}\n"
            f"Deaths last week: {playerinfo['stats']['deaths_week']}\n"
            f"KD: {ratio_week}:1",
            inline=True,
        )
        embed.set_footer(text="Created by Gnomeslayer#5551")
        if notes:
            with open("./json/note.json", "w") as f:
                f.write(json.dumps(notes, indent=4))
            with open("./json/note.json", "rb") as f:
                await ctx.reply(
                    embed=embed, file=discord.File(f, filename="notes.json")
                )
        else:
            await ctx.reply(embed=embed)

        embed = discord.Embed(title=f"Ban info for - {submittedtext}")
        embed.set_thumbnail(url=playerinfo["avatar"])
        embed.add_field(
            name="Player Information",
            value=f"{playerinfo['playername']} - {playerinfo['steamid']}",
        )
        embed.add_field(
            name="Links",
            value=f"[Steam]({playerinfo['steamurl']})\n[Battlemetrics](https://www.battlemetrics.com/rcon/players/{userids['bmid']})",
            inline=False,
        )
        bandata = ""
        for bans in myserverbans:
            bandata += f"{myserverbans[bans]['servername']} - {myserverbans[bans]['bandate']} - Expires: {myserverbans[bans]['expires']} ```{myserverbans[bans]['bannote']} | {myserverbans[bans]['banreason']}```\n"
        if bandata == "":
            bandata = "Nothing to see here."

        if len(bandata) > 500:
            with open("./json/bandata.json", "w") as f:
                f.write(json.dumps(myserverbans, indent=4))
            with open("./json/bandata.json", "rb") as f:
                await ctx.reply(
                    embed=embed,
                    content="Ban Information was too long to be embed. Force sent as json file.",
                    file=discord.File(f, filename="bandata.json"),
                )
        else:
            embed.add_field(name="Ban Information", value=f"{bandata}", inline=False)
            await ctx.reply(embed=embed)
        waitmsg = await ctx.reply("Grabbing alts for that user now!")
        view = AltResults()
        api = BMAPI()
        proxylimit = 5
        await waitmsg.delete(delay=600)

        relatedplayers = await api.relatedplayers(userids["bmid"])

        if relatedplayers["timeout"]:
            await ctx.reply(f"Timed out.\n**Reason**\n{relatedplayers['timeout']}")
            return

        cmdresponse = await ctx.reply(
            f"I have found {relatedplayers['relatedcount']} users and {relatedplayers['proxycount']} proxy users."
        )
        await cmdresponse.delete(delay=15)

        if relatedplayers["proxycount"]:
            thelist = list(relatedplayers.keys())
            if relatedplayers["proxycount"] >= proxylimit:
                await ctx.reply(
                    f"This user is connected to at least {proxylimit} accounts who are on a proxy/vpn.\n"
                    f"This user is connected to {len(thelist)-3} accounts who are not on a proxy/vpn."
                )
            else:
                await ctx.reply(
                    f"I found {relatedplayers['proxycount']} accounts connected to this user via proxy.\n"
                    f"I am not gathering the data on these users."
                )
        thelist = list(relatedplayers.keys())
        thelist.remove("relatedcount")
        thelist.remove("proxycount")
        thelist.remove("timeout")
        if relatedplayers["relatedcount"]:
            usernames = await api.get_names(userids["bmid"])
        if thelist:
            await waitmsg.edit(content=f"Found {len(thelist)} related players!")
            print(
                f"{ctx.author} used alts command to search for {submittedtext} - {len(thelist)} related players!"
            )
            for i in thelist:
                await waitmsg.edit(
                    content=f"Grabbing player information for {i}. This may take a moment."
                )
                relatedplayers[i]["playerinfo"] = await api.playerinfo(i, "alts")
                # await waitmsg.edit(content=f'Grabbing player names for {i}. This may take a moment.')
                relatedplayers[i]["names"] = await api.get_names(i)
                # await waitmsg.edit(content=f'Grabbing player serverbans for {i}. This may take a moment.')
                relatedplayers[i]["serverbans"] = await api.serverbans(i)
                # await waitmsg.edit(content=f'Grabbing player gamebans for {i}. This may take a moment.')
                relatedplayers[i]["gamebans"] = await api.gamebans(
                    relatedplayers[i]["playerinfo"]["steamid"]
                )
                relatedplayers[i]["compared"] = await api.compare(
                    usernames, relatedplayers[i]["names"]
                )

        tempdict_banned = {}
        tempdict_notbanned = {}
        ignoreditems = ["relatedcount", "proxycount", "timeout"]
        for i in relatedplayers:
            if i not in ignoreditems:
                if relatedplayers[i]["gamebans"]["eac_ban_count"] == "0":
                    tempdict_banned[i] = relatedplayers[i]
                else:
                    tempdict_notbanned[i] = relatedplayers[i]

        relatedplayers = tempdict_notbanned
        for i in tempdict_banned:
            relatedplayers[i] = tempdict_banned[i]
        thelist = list(relatedplayers.keys())
        await waitmsg.edit(
            content=f"All player information acquired. Now displaying. "
            f"I was able to find {len(thelist)} related players."
        )
        if len(thelist) == 1:
            bmid = thelist[0]
            embed = discord.Embed(title=f"Alts for {submittedtext}")
            myimage = relatedplayers[bmid]["playerinfo"]["avatar"]
            embed.set_thumbnail(url=myimage)
            embed.add_field(
                name="Name",
                value=f"{relatedplayers[bmid]['playerinfo']['playername']}",
                inline=True,
            )
            steamid = relatedplayers[bmid]["playerinfo"]["steamid"]
            steamurl = relatedplayers[bmid]["playerinfo"]["steamurl"]
            embed.add_field(
                name="SteamID64",
                value=f"[{steamid}]({steamurl})",
                inline=True,
            )
            embed.add_field(
                name="Battlemetrics ID",
                value=f"[{bmid}](https://www.battlemetrics.com/rcon/players/{bmid})",
                inline=True,
            )
            embed.add_field(name="Alt Number", value=f"1/1", inline=True)
            embed.add_field(
                name="# Server Bans (including expired)",
                value=f"{len(relatedplayers[bmid]['serverbans'])}",
                inline=True,
            )

            if relatedplayers[bmid]["gamebans"]["eac_ban_count"] == "0":
                embed.add_field(
                    name="Gamebanned?",
                    value=f"False",
                    inline=True,
                )
            else:
                twitterurl = relatedplayers[bmid]["gamebans"]["url"]
                daysago = relatedplayers[bmid]["gamebans"]["days_ago"]
                embed.add_field(
                    name="Gamebanned?",
                    value=f"[True]({twitterurl}) {daysago} day(s) ago",
                    inline=True,
                )
            embed.add_field(
                name="Total Rust Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['rusthours']}",
                inline=True,
            )
            embed.add_field(
                name="Total Aimtrain Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['aimtrain']}",
                inline=True,
            )

            namematches = ""
            for i in relatedplayers[bmid]["compared"]:
                namematches += f"**{i['name1']}** against **{i['name2']}** -> {i['match_ratio']}%\n"
            embed.add_field(
                name="Name Matches",
                value=f"{namematches}",
                inline=False,
            )
            if relatedplayers[bmid]["country"]:
                embed.add_field(
                    name="Country",
                    value=f"{relatedplayers[bmid]['country']}",
                    inline=True,
                )
            else:
                embed.add_field(name="Country", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["isp"]:
                embed.add_field(
                    name="ISP", value=f"{relatedplayers[bmid]['isp']}", inline=True
                )
            else:
                embed.add_field(name="ISP", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["lastcheck"]:
                embed.add_field(
                    name="lastcheck",
                    value=f"{relatedplayers[bmid]['lastcheck']}",
                    inline=True,
                )
            else:
                embed.add_field(name="lastcheck", value=f"Unknown", inline=True)

            embed.set_footer(text="Created by Gnomeslayer#5551")
            await ctx.reply(embed=embed)
        if len(thelist) > 1:
            view.setusers(relatedplayers)
            view.submittedtext = submittedtext
            bmid = thelist[0]
            embed = discord.Embed(title=f"Alts for {submittedtext}")
            myimage = relatedplayers[bmid]["playerinfo"]["avatar"]
            embed.set_thumbnail(url=myimage)
            embed.add_field(
                name="Name",
                value=f"{relatedplayers[bmid]['playerinfo']['playername']}",
                inline=True,
            )
            steamid = relatedplayers[bmid]["playerinfo"]["steamid"]
            steamurl = relatedplayers[bmid]["playerinfo"]["steamurl"]
            embed.add_field(
                name="SteamID64",
                value=f"[{steamid}]({steamurl})",
                inline=True,
            )
            embed.add_field(
                name="Battlemetrics ID",
                value=f"[{bmid}](https://www.battlemetrics.com/rcon/players/{bmid})",
                inline=True,
            )
            embed.add_field(
                name="Alt Number", value=f"0/{len(thelist) - 1}", inline=True
            )
            embed.add_field(
                name="# Server Bans (including expired)",
                value=f"{len(relatedplayers[bmid]['serverbans'])}",
                inline=True,
            )

            if relatedplayers[bmid]["gamebans"]["eac_ban_count"] == "0":
                embed.add_field(
                    name="Gamebanned?",
                    value=f"False",
                    inline=True,
                )
            else:
                twitterurl = relatedplayers[bmid]["gamebans"]["url"]
                daysago = relatedplayers[bmid]["gamebans"]["days_ago"]
                embed.add_field(
                    name="Gamebanned?",
                    value=f"[True]({twitterurl}) {daysago} day(s) ago",
                    inline=True,
                )
            embed.add_field(
                name="Total Rust Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['rusthours']}",
                inline=True,
            )
            embed.add_field(
                name="Total Aimtrain Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['aimtrain']}",
                inline=True,
            )
            namematches = ""
            for i in relatedplayers[bmid]["compared"]:
                namematches += f"**{i['name1']}** against **{i['name2']}** -> {i['match_ratio']}%\n"
            embed.add_field(
                name="Name Matches",
                value=f"{namematches}",
                inline=False,
            )

            if relatedplayers[bmid]["country"]:
                embed.add_field(
                    name="Country",
                    value=f"{relatedplayers[bmid]['country']}",
                    inline=True,
                )
            else:
                embed.add_field(name="Country", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["isp"]:
                embed.add_field(
                    name="ISP", value=f"{relatedplayers[bmid]['isp']}", inline=True
                )
            else:
                embed.add_field(name="ISP", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["lastcheck"]:
                embed.add_field(
                    name="lastcheck",
                    value=f"{relatedplayers[bmid]['lastcheck']}",
                    inline=True,
                )
            else:
                embed.add_field(name="lastcheck", value=f"Unknown", inline=True)
            await ctx.send(
                "relatedplayers are sorted showing those with gamebans first."
            )
            embed.set_footer(text="Created by Gnomeslayer#5551")
            await ctx.reply(embed=embed, view=view)

        if not thelist:
            await ctx.reply(
                "I was unable to find anybody directly connected to this user through an IP that was not connected through a proxy."
            )

    @commands.command()
    async def bans(self, ctx, submittedtext):
        bmapi = BMAPI()
        userids = await bmapi.get_ids(submittedtext)
        if not userids:
            await ctx.reply(
                f"I was unable to find that user. Are you sure you typed in their STEAM ID, STEAM URL or BM URL correctly?\n"
                f"Heres what you submitted:\n{submittedtext}"
            )
            return

        serverbans = await bmapi.serverbans(userids["bmid"])
        playerinfo = await bmapi.playerinfo(userids["bmid"], "single")

        if not userids["steamid"]:
            userids["steamid"] = playerinfo["steamid"]

        embed = discord.Embed(title=f"Ban info for - {submittedtext}")
        embed.set_thumbnail(url=playerinfo["avatar"])
        embed.add_field(
            name="Player Information",
            value=f"{playerinfo['playername']} - {playerinfo['steamid']}",
        )
        embed.add_field(
            name="Links",
            value=f"[Steam]({playerinfo['steamurl']})\n[Battlemetrics](https://www.battlemetrics.com/rcon/players/{userids['bmid']})",
            inline=False,
        )
        bandata = ""
        for bans in serverbans:
            bandata += f"{serverbans[bans]['servername']} - {serverbans[bans]['bandate']} - Expires: {serverbans[bans]['expires']} ```{serverbans[bans]['bannote']} | {serverbans[bans]['banreason']}```\n"
        if bandata == "":
            bandata = "Nothing to see here."

        if len(bandata) > 500:
            with open("./json/bandata.json", "w") as f:
                f.write(json.dumps(serverbans, indent=4))
            with open("./json/bandata.json", "rb") as f:
                await ctx.reply(
                    embed=embed,
                    content="Ban Information was too long to be embed. Force sent as json file.",
                    file=discord.File(f, filename="bandata.json"),
                )
        else:
            embed.add_field(name="Ban Information", value=f"{bandata}", inline=False)
            await ctx.send(embed=embed)

    @commands.command(
        aliases=["COMPARE", "Compare"], help="Also works with COMPARE and Compare"
    )
    async def compare(self, ctx, arg1, arg2):

        print(f"{ctx.author} used the compare command and said {arg1} and {arg2}")
        if not arg2:
            await ctx.reply("Please submit a second steam id.")
            print(
                f"{ctx.author} did not submit a second steam id for the compare command!"
            )
            return

        def get_bm_ids(submittedtext):
            userinfo = {"bmid": 0, "steamid": 0}
            if len(submittedtext) != 17:
                return userinfo
            steamid = submittedtext
            bmid = search_bm(steamid)
            if bmid:
                userinfo = {"steamid": steamid, "bmid": bmid}
            return userinfo

        def search_bm(steamid):
            mytoken = f"Bearer {config['battlemetrics_token']}"
            url_extension = f"players?filter[search]={steamid}&include=identifier"
            url = f"https://api.battlemetrics.com/{url_extension}"
            my_headers = {"Authorization": mytoken}
            response = requests.get(url, headers=my_headers)
            data = response.json()
            return data["data"][0]["id"] if data["data"] else ""

        def get_data(bm_id):

            headers = {
                "Authorization": f"{config['battlemetrics_token']}",
                "Content-Type": "application/json",
            }
            response = requests.get(
                f"https://api.battlemetrics.com/players/{bm_id}",
                headers=headers,
                timeout=10,
                params={"include": "identifier"},
            )
            return response.json()

        def parse_data(data):
            usefuldata = data["included"]
            names = []
            for identifier in usefuldata:
                if identifier["attributes"]["type"] == "name":
                    names.append(identifier["attributes"]["identifier"])
            return names

        def compare(person1, person2):
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

        user_ids_1 = get_bm_ids(arg1)
        user_ids_2 = get_bm_ids(arg2)
        output1 = get_data(user_ids_1["bmid"])
        output2 = get_data(user_ids_2["bmid"])
        person1 = parse_data(output1)
        person2 = parse_data(output2)
        text = compare(person1, person2)
        embed_description = f"comparing **{arg1}** and **{arg2}**!\n\n"

        for match in text:
            embed_description += f"**{match['name1']}** against **{match['name2']}** -> {match['match_ratio']}%\n"
        embed = discord.Embed(
            title="Name Comparison Bot", description=embed_description, color=0x748CAB
        )
        await ctx.send(embed=embed)

    # Listens for any errors and displays them to the user.
    @commands.Cog.listener()
    async def on_message(self, message):

        api = BMAPI()
        if not message.author.bot and message.attachments:
            message_attachment = message.attachments
            users = {}

            def lowercase_keys(obj):
                if isinstance(obj, dict):
                    obj = {key.lower(): value for key, value in obj.items()}
                    for key, value in obj.items():
                        if isinstance(value, list):
                            for idx, item in enumerate(value):
                                value[idx] = lowercase_keys(item)
                        obj[key] = lowercase_keys(value)
                return obj

            for attachment in message_attachment:
                print(
                    f"{message.author} used the on_message command and sent an attachment!"
                )
                if "vdf" in attachment.filename and "loginusers" in attachment.filename:
                    if not accounts[account_name].get("steamid"):
                        await message.reply(
                            f"{account_name} does not have an associated steam id. Please check the config file."
                        )
                        continue
                    attachment_url = attachment.url
                    file_request = requests.get(attachment_url)
                    data = file_request.content.decode("utf-8")
                    myvdf = vdf.loads(data)
                    new_dict = lowercase_keys(myvdf)
                    for i in new_dict["users"]:
                        users[i] = {
                            "gamebanned": "No",
                            "bandate": "Null",
                            "rustbanned": "",
                            "twitter": "",
                            "days_ago": "",
                        }
                    embed = discord.Embed()
                    for u in users:
                        gamebanned = await api.gamebans(u)

                        if gamebanned["eac_ban_count"] == "1":
                            users[u]["bandate"] = gamebanned["date"]
                            users[u]["twitter"] = gamebanned["url"]
                            users[u][
                                "rustbanned"
                            ] = f"https://rustbanned.com/profile.php?id={u}"
                            users[u]["daysago"] = gamebanned["days_ago"]
                            users[u]["gamebanned"] = "Yes"
                        if users[u]["gamebanned"] == "Yes":
                            embed.add_field(
                                name=f"{u}",
                                value=f"Banned {users[u]['daysago']} days ago. "
                                f"[twitter]({users[u]['twitter']}) "
                                f"[RustBanned]({users[u]['rustbanned']})",
                                inline=False,
                            )
                        else:
                            embed.add_field(
                                name=f"{u}", value=f"Not Gamebanned.", inline=False
                            )
                    await message.reply(embed=embed)
                if "vdf" in attachment.filename and "config" in attachment.filename:
                    attachment_url = attachment.url
                    file_request = requests.get(attachment_url)
                    data = file_request.content.decode("utf-8")
                    myvdf = vdf.loads(data)
                    new_dict = lowercase_keys(myvdf)
                    accounts = new_dict["installconfigstore"]["software"]["valve"][
                        "steam"
                    ]["accounts"]
                    for account_name in accounts:
                        if not accounts[account_name].get("steamid"):
                            await message.reply(
                                f"{account_name} does not have an associated steam id. Please check the config file."
                            )
                            continue
                        account_id = accounts[account_name]["steamid"]
                        users[account_id] = {
                            "gamebanned": "No",
                            "bandate": "Null",
                            "rustbanned": "",
                            "twitter": "",
                            "days_ago": "",
                        }
                    embed = discord.Embed()
                    for u in users:
                        gamebanned = await api.gamebans(u)
                        if gamebanned["eac_ban_count"] == "1":
                            users[u]["bandate"] = gamebanned["date"]
                            users[u]["twitter"] = gamebanned["url"]
                            users[u][
                                "rustbanned"
                            ] = f"https://rustbanned.com/profile.php?id={u}"
                            users[u]["daysago"] = gamebanned["days_ago"]
                            users[u]["gamebanned"] = "Yes"

                        if users[u]["gamebanned"] == "Yes":
                            embed.add_field(
                                name=f"{u}",
                                value=f"Banned {users[u]['daysago']} days ago. "
                                f"[twitter]({users[u]['twitter']}) "
                                f"[RustBanned]({users[u]['rustbanned']})",
                                inline=False,
                            )
                        else:
                            embed.add_field(
                                name=f"{u}", value=f"Not Gamebanned.", inline=False
                            )
                    embed.set_footer(text="Created by Gnomeslayer#5551")
                    await message.reply(embed=embed)

    @commands.command(
        aliases=["STATS", "Stats", "STAT", "Stat", "stat"],
        help="Also works with STATS, Stats, STAT, Stat and stat",
    )
    async def stats(self, ctx, submittedtext: str):
        print(f"{ctx.author} used the stats command and said {submittedtext}")
        await ctx.send("Stats!")
        api = BMAPI()
        waitmsg = await ctx.send(
            "Please wait a moment while I grab the kills and deaths for the user."
        )
        await waitmsg.delete(delay=600)
        userids = await api.get_ids(submittedtext)
        if not userids:
            await ctx.reply(
                f"I was unable to find that user. Are you sure you typed in their STEAM ID, STEAM URL or BM URL correctly?\n"
                f"Heres what you submitted:\n{submittedtext}"
            )
            return

        playerinfo = await api.playerinfo(userids["bmid"], "single")

        if not userids["steamid"]:
            userids["steamid"] = playerinfo["steamid"]

        userstats = await api.stats(userids["bmid"])
        embed = discord.Embed(title=f"Statistics for {userids['steamid']}")
        ratio_day, ratio_week = 0, 0

        if userstats["kills_day"] and userstats["deaths_day"]:
            ratio_day = round(userstats["kills_day"] / userstats["deaths_day"], 2)

        if userstats["kills_day"] and not userstats["deaths_day"]:
            ratio_day = userstats["kills_day"]

        if userstats["kills_week"] and userstats["deaths_week"]:
            ratio_week = round(userstats["kills_week"] / userstats["deaths_week"], 2)

        if userstats["kills_week"] and not userstats["deaths_week"]:
            ratio_week = userstats["kills_week"]

        embed.add_field(
            name=f"24 hour Stats",
            value=f"Kills last 24 hours: {userstats['kills_day']}\n"
            f"Deaths last 24 hours: {userstats['deaths_day']}\n"
            f"KDA: {ratio_day}:1",
            inline=False,
        )
        embed.add_field(
            name=f"Week Stats",
            value=f"Kills in the week: {userstats['kills_week']}\n"
            f"Deaths last 24 hours: {userstats['deaths_week']}\n"
            f"KDA: {ratio_week}:1",
            inline=False,
        )
        embed.set_footer(text="Created by Gnomeslayer#5551")
        await ctx.reply(embed=embed)

    # @commands.command()
    async def baninfo(self, ctx, submittedtext: str):
        myauthor = ctx.author
        embed_feedback = discord.Embed()
        embed_feedback.add_field(
            name="Fetching the data now.",
            value=f"Please be patient. I am grabbing the data!",
            inline=True,
        )
        feedback = await ctx.send(embed=embed_feedback)
        await feedback.delete(delay=600)
        log_info = f"{myauthor} used the command baninfo {submittedtext} \n"
        bmapi = BMAPI()

        baninfo = await bmapi.baninfo(submittedtext)
        log_info += f"Grabbed log info for banid '{submittedtext}'\n"
        name = baninfo["name"]
        steamid = baninfo["steamid"]
        bmlink = f"https://www.battlemetrics.com/rcon/players?filter[search]={steamid}"
        server = baninfo["server"]
        banner = baninfo["banner"]
        reason = baninfo["reason"]
        note = baninfo["note"]
        timestamp = baninfo["timestamp"]
        organization = baninfo["organization"]
        expires = baninfo["expires"]
        steamlink = baninfo["profileurl"]
        banlink = f"https://www.battlemetrics.com/rcon/bans/edit/{submittedtext}"

        mylength = len(note)

        embed = discord.Embed(title=f"{name} - {steamid}", url=f"{bmlink}")
        embed.add_field(name="Organization", value=f"{organization}", inline=True)
        embed.add_field(name="Banner", value=f"{banner}", inline=True)
        embed.add_field(
            name="Links",
            value=f"[Battlemetrics]({bmlink})\n[Steam]({steamlink})\n[Ban Link]({banlink})",
            inline=True,
        )
        embed.add_field(name="Ban date", value=f"{timestamp}", inline=True)
        embed.add_field(name="Expires", value=f"{expires}", inline=True)

        embed.add_field(name="Server", value=f"{server}", inline=False)
        embed.add_field(name="Reason", value=f"{reason}", inline=False)
        if mylength <= 500:
            embed.add_field(name="Notes", value=f"{note}", inline=False)
        else:
            log_info += "Force sending Notes as a file.\n"

        log_info += f"Sent information to channel.\n ========================= \n"
        embed.set_footer(text="Created by Gnomeslayer#5551")
        await ctx.reply(embed=embed)
        if mylength > 500:
            with open("./json/bannotes.txt", "w") as f:
                f.write(json.dumps(note, indent=4))
            with open("./json/bannotes.txt", "rb") as f:
                await ctx.reply(
                    content="Ban notes were too long to be embed. Force sent as file.",
                    file=discord.File(f, filename="note.txt"),
                )

    # noinspection PyTypeChecker
    @commands.command(
        aliases=["ALTS", "ALT", "alt", "Alt", "Alts"],
        help="Also works with ALTS, ALT, alt, Alt and Alts",
    )
    async def alts(self, ctx, submittedtext):
        print(f"{ctx.author} used the alts command and said {submittedtext}")
        view = AltResults()
        api = BMAPI()
        proxylimit = 5
        waitmsg = await ctx.send(
            "I am searching for relatedplayers now. Please wait a moment. "
            "This process can take up to a minute if the user has a significant amount of relatedplayers."
        )
        await waitmsg.delete(delay=600)
        userids = await api.get_ids(submittedtext)
        if not userids:
            await ctx.reply(
                f"I was unable to find that user. Are you sure you typed in their STEAM ID, STEAM URL or BM URL correctly?\n"
                f"Heres what you submitted:\n{submittedtext}"
            )
            return

        playerinfo = await api.playerinfo(userids["bmid"], "single")
        if not playerinfo:
            await ctx.reply("I was unable to find that user in my searches.")
            return

        if not userids["steamid"]:
            userids["steamid"] = playerinfo["steamid"]

        relatedplayers = await api.relatedplayers(userids["bmid"])

        if relatedplayers["timeout"]:
            await ctx.reply(f"Timed out.\n**Reason**\n{relatedplayers['timeout']}")
            return

        cmdresponse = await ctx.reply(
            f"I have found {relatedplayers['relatedcount']} users and {relatedplayers['proxycount']} proxy users."
        )
        await cmdresponse.delete(delay=15)

        if relatedplayers["proxycount"]:
            thelist = list(relatedplayers.keys())
            if relatedplayers["proxycount"] >= proxylimit:
                await ctx.reply(
                    f"This user is connected to at least {proxylimit} accounts who are on a proxy/vpn.\n"
                    f"This user is connected to {len(thelist)-3} accounts who are not on a proxy/vpn."
                )
            else:
                await ctx.reply(
                    f"I found {relatedplayers['proxycount']} accounts connected to this user via proxy.\n"
                    f"I am not gathering the data on these users."
                )
        thelist = list(relatedplayers.keys())
        thelist.remove("relatedcount")
        thelist.remove("proxycount")
        thelist.remove("timeout")
        if relatedplayers["relatedcount"]:
            usernames = await api.get_names(userids["bmid"])
        if thelist:
            await waitmsg.edit(content=f"Found {len(thelist)} related players!")
            print(
                f"{ctx.author} used alts command to search for {submittedtext} - {len(thelist)} related players!"
            )
            for i in thelist:
                await waitmsg.edit(
                    content=f"Grabbing player information for {i}. This may take a moment."
                )
                relatedplayers[i]["playerinfo"] = await api.playerinfo(i, "alts")
                # await waitmsg.edit(content=f'Grabbing player names for {i}. This may take a moment.')
                relatedplayers[i]["names"] = await api.get_names(i)
                # await waitmsg.edit(content=f'Grabbing player serverbans for {i}. This may take a moment.')
                relatedplayers[i]["serverbans"] = await api.serverbans(i)
                # await waitmsg.edit(content=f'Grabbing player gamebans for {i}. This may take a moment.')
                relatedplayers[i]["gamebans"] = await api.gamebans(
                    relatedplayers[i]["playerinfo"]["steamid"]
                )
                relatedplayers[i]["compared"] = await api.compare(
                    usernames, relatedplayers[i]["names"]
                )

        tempdict_banned = {}
        tempdict_notbanned = {}
        ignoreditems = ["relatedcount", "proxycount", "timeout"]
        for i in relatedplayers:
            if i not in ignoreditems:
                if relatedplayers[i]["gamebans"]["eac_ban_count"] == "0":
                    tempdict_banned[i] = relatedplayers[i]
                else:
                    tempdict_notbanned[i] = relatedplayers[i]

        relatedplayers = tempdict_notbanned
        for i in tempdict_banned:
            relatedplayers[i] = tempdict_banned[i]
        thelist = list(relatedplayers.keys())
        await waitmsg.edit(
            content=f"All player information acquired. Now displaying. "
            f"I was able to find {len(thelist)} related players."
        )
        if len(thelist) == 1:
            bmid = thelist[0]
            embed = discord.Embed(title=f"Alts for {submittedtext}")
            myimage = relatedplayers[bmid]["playerinfo"]["avatar"]
            embed.set_thumbnail(url=myimage)
            embed.add_field(
                name="Name",
                value=f"{relatedplayers[bmid]['playerinfo']['playername']}",
                inline=True,
            )
            steamid = relatedplayers[bmid]["playerinfo"]["steamid"]
            steamurl = relatedplayers[bmid]["playerinfo"]["steamurl"]
            embed.add_field(
                name="SteamID64",
                value=f"[{steamid}]({steamurl})",
                inline=True,
            )
            embed.add_field(
                name="Battlemetrics ID",
                value=f"[{bmid}](https://www.battlemetrics.com/rcon/players/{bmid})",
                inline=True,
            )
            embed.add_field(name="Alt Number", value=f"1/1", inline=True)
            embed.add_field(
                name="# Server Bans (including expired)",
                value=f"{len(relatedplayers[bmid]['serverbans'])}",
                inline=True,
            )

            if relatedplayers[bmid]["gamebans"]["eac_ban_count"] == "0":
                embed.add_field(
                    name="Gamebanned?",
                    value=f"False",
                    inline=True,
                )
            else:
                twitterurl = relatedplayers[bmid]["gamebans"]["url"]
                daysago = relatedplayers[bmid]["gamebans"]["days_ago"]
                embed.add_field(
                    name="Gamebanned?",
                    value=f"[True]({twitterurl}) {daysago} day(s) ago",
                    inline=True,
                )
            embed.add_field(
                name="Total Rust Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['rusthours']}",
                inline=True,
            )
            embed.add_field(
                name="Total Aimtrain Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['aimtrain']}",
                inline=True,
            )

            namematches = ""
            for i in relatedplayers[bmid]["compared"]:
                namematches += f"**{i['name1']}** against **{i['name2']}** -> {i['match_ratio']}%\n"
            embed.add_field(
                name="Name Matches",
                value=f"{namematches}",
                inline=False,
            )
            if relatedplayers[bmid]["country"]:
                embed.add_field(
                    name="Country",
                    value=f"{relatedplayers[bmid]['country']}",
                    inline=True,
                )
            else:
                embed.add_field(name="Country", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["isp"]:
                embed.add_field(
                    name="ISP", value=f"{relatedplayers[bmid]['isp']}", inline=True
                )
            else:
                embed.add_field(name="ISP", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["lastcheck"]:
                embed.add_field(
                    name="lastcheck",
                    value=f"{relatedplayers[bmid]['lastcheck']}",
                    inline=True,
                )
            else:
                embed.add_field(name="lastcheck", value=f"Unknown", inline=True)

            embed.set_footer(text="Created by Gnomeslayer#5551")
            await ctx.reply(embed=embed)
        if len(thelist) > 1:
            view.setusers(relatedplayers)
            view.submittedtext = submittedtext
            bmid = thelist[0]
            embed = discord.Embed(title=f"Alts for {submittedtext}")
            myimage = relatedplayers[bmid]["playerinfo"]["avatar"]
            embed.set_thumbnail(url=myimage)
            embed.add_field(
                name="Name",
                value=f"{relatedplayers[bmid]['playerinfo']['playername']}",
                inline=True,
            )
            steamid = relatedplayers[bmid]["playerinfo"]["steamid"]
            steamurl = relatedplayers[bmid]["playerinfo"]["steamurl"]
            embed.add_field(
                name="SteamID64",
                value=f"[{steamid}]({steamurl})",
                inline=True,
            )
            embed.add_field(
                name="Battlemetrics ID",
                value=f"[{bmid}](https://www.battlemetrics.com/rcon/players/{bmid})",
                inline=True,
            )
            embed.add_field(
                name="Alt Number", value=f"0/{len(thelist) - 1}", inline=True
            )
            embed.add_field(
                name="# Server Bans (including expired)",
                value=f"{len(relatedplayers[bmid]['serverbans'])}",
                inline=True,
            )

            if relatedplayers[bmid]["gamebans"]["eac_ban_count"] == "0":
                embed.add_field(
                    name="Gamebanned?",
                    value=f"False",
                    inline=True,
                )
            else:
                twitterurl = relatedplayers[bmid]["gamebans"]["url"]
                daysago = relatedplayers[bmid]["gamebans"]["days_ago"]
                embed.add_field(
                    name="Gamebanned?",
                    value=f"[True]({twitterurl}) {daysago} day(s) ago",
                    inline=True,
                )
            embed.add_field(
                name="Total Rust Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['rusthours']}",
                inline=True,
            )
            embed.add_field(
                name="Total Aimtrain Hours",
                value=f"{relatedplayers[bmid]['playerinfo']['aimtrain']}",
                inline=True,
            )
            namematches = ""
            for i in relatedplayers[bmid]["compared"]:
                namematches += f"**{i['name1']}** against **{i['name2']}** -> {i['match_ratio']}%\n"
            embed.add_field(
                name="Name Matches",
                value=f"{namematches}",
                inline=False,
            )

            if relatedplayers[bmid]["country"]:
                embed.add_field(
                    name="Country",
                    value=f"{relatedplayers[bmid]['country']}",
                    inline=True,
                )
            else:
                embed.add_field(name="Country", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["isp"]:
                embed.add_field(
                    name="ISP", value=f"{relatedplayers[bmid]['isp']}", inline=True
                )
            else:
                embed.add_field(name="ISP", value=f"Unknown", inline=True)

            if relatedplayers[bmid]["lastcheck"]:
                embed.add_field(
                    name="lastcheck",
                    value=f"{relatedplayers[bmid]['lastcheck']}",
                    inline=True,
                )
            else:
                embed.add_field(name="lastcheck", value=f"Unknown", inline=True)
            await ctx.send(
                "relatedplayers are sorted showing those with gamebans first."
            )
            embed.set_footer(text="Created by Gnomeslayer#5551")
            await ctx.reply(embed=embed, view=view)

        if not thelist:
            await ctx.reply(
                "I was unable to find anybody directly connected to this user through an IP that was not connected through a proxy."
            )

    @commands.command(aliases=["INFO", "Info"], help="Also works with INFO and Info")
    async def info(self, ctx, submittedtext: str):
        print(f"{ctx.author} used the info command and said {submittedtext}")
        """ Gets all the information from battlemetrics about the given user. Also has a 60-second cooldown """
        embed_feedback = discord.Embed()
        embed_feedback.add_field(
            name="Fetching the data now.",
            value=f"Please be patient. I am grabbing the data!",
            inline=True,
        )
        feedback = await ctx.send(embed=embed_feedback)
        await feedback.delete(delay=600)

        bmapi = BMAPI()
        user_ids = await bmapi.get_ids(submittedtext)
        if user_ids["bmid"]:
            playerinfo = await bmapi.playerinfo(user_ids["bmid"], "single")
            if not user_ids["steamid"]:
                user_ids["steamid"] = playerinfo["steamid"]
            notes = await bmapi.playernotes(user_ids["bmid"])
            myserverbans = await bmapi.serverbans(user_ids["bmid"])
            rconbase = r"https://www.battlemetrics.com/rcon/players/"
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
                name="Aim train hours",
                value=f"{playerinfo['aimtrain']}",
                inline=True,
            )

            embed.add_field(
                name="Links",
                value=f"[Steam]({playerinfo['steamurl']})\n[RCON]({rconbase}{user_ids['bmid']})",
                inline=True,
            )

            serverbans = "No server bans"
            if myserverbans:
                serverbans = ""
                for i in myserverbans:
                    banid = myserverbans[i]["banid"]
                    banreason = myserverbans[i]["banreason"]
                    serverbans += f"[{banreason}](https://www.battlemetrics.com/rcon/bans/edit/{banid})\n"
            embed.add_field(name="Server bans", value=f"{serverbans}", inline=False)
            ratio_day = 0
            ratio_week = 0

            if (
                playerinfo["stats"]["kills_day"] > 0
                and playerinfo["stats"]["deaths_day"] > 0
            ):
                ratio_day = round(
                    playerinfo["stats"]["kills_day"]
                    / playerinfo["stats"]["deaths_day"],
                    2,
                )

            if (
                playerinfo["stats"]["kills_day"] > 0
                and playerinfo["stats"]["deaths_day"] == 0
            ):
                ratio_day = playerinfo["stats"]["kills_day"]

            if (
                playerinfo["stats"]["kills_week"] > 0
                and playerinfo["stats"]["deaths_week"] > 0
            ):
                ratio_week = round(
                    playerinfo["stats"]["kills_week"]
                    / playerinfo["stats"]["deaths_week"],
                    2,
                )

            if (
                playerinfo["stats"]["kills_week"] > 0
                and playerinfo["stats"]["deaths_week"] == 0
            ):
                ratio_week = playerinfo["stats"]["kills_week"]

            embed.add_field(
                name="Statistics",
                value=f"**Last 24 Hours**\n"
                f"Kills: {playerinfo['stats']['kills_day']}\n"
                f"Deaths:{playerinfo['stats']['deaths_day']}\n"
                f"KD Ratio: {ratio_day}:1",
                inline=True,
            )

            embed.add_field(
                name="Statistics",
                value=f"Kills in the week: {playerinfo['stats']['kills_week']}\n"
                f"Deaths last week: {playerinfo['stats']['deaths_week']}\n"
                f"KD: {ratio_week}:1",
                inline=True,
            )
            embed.set_footer(text="Created by Gnomeslayer#5551")

            if notes:
                with open("./json/note.json", "w") as f:
                    f.write(json.dumps(notes, indent=4))
                with open("./json/note.json", "rb") as f:
                    await ctx.reply(
                        embed=embed, file=discord.File(f, filename="notes.json")
                    )
            else:
                await ctx.reply(embed=embed)
        else:
            await ctx.reply(f"Could not find: {submittedtext}")
            return

    @staticmethod
    def __rounded_division_with_explicit_float_convert(
        value_1: str, value_2: str
    ) -> float:
        value_1, value_2 = float(value_1), float(value_2)
        return round(value_1 / value_2, 2)


class AltResults(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
        self.pagenumber = 0
        self.users = {}
        self.submittedtext = ""
        self.listlength = 0

    def setusers(self, myusers):
        self.users = myusers
        thelist = list(myusers.keys())
        self.listlength = len(thelist)

    # Possible Bug: Seems like this is used nowhere
    # noinspection PyUnusedLocal
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.red)
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.pagenumber == 0:
            self.pagenumber = self.listlength - 1
        else:
            self.pagenumber = self.pagenumber - 1

        embed = self.setembed(self.pagenumber)
        await interaction.response.edit_message(embed=embed, view=self)

    # Possible Bug: Seems like this is used nowhere
    # noinspection PyUnusedLocal
    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pagenumber == (self.listlength - 1):
            self.pagenumber = 0
        else:
            self.pagenumber = self.pagenumber + 1

        embed = self.setembed(self.pagenumber)
        await interaction.response.edit_message(embed=embed, view=self)

    def setembed(self, pagenumber):
        thelist = list(self.users.keys())
        bmid = thelist[pagenumber]
        embed = discord.Embed(title=f"Alts for {self.submittedtext}")
        myimage = self.users[bmid]["playerinfo"]["avatar"]
        embed.set_thumbnail(url=myimage)
        embed.add_field(
            name="Name",
            value=f"{self.users[bmid]['playerinfo']['playername']}",
            inline=True,
        )
        steamid = self.users[bmid]["playerinfo"]["steamid"]
        steamurl = self.users[bmid]["playerinfo"]["steamurl"]
        embed.add_field(
            name="SteamID64",
            value=f"[{steamid}]({steamurl})",
            inline=True,
        )
        embed.add_field(
            name="Battlemetrics ID",
            value=f"[{bmid}](https://www.battlemetrics.com/rcon/players/{bmid})",
            inline=True,
        )
        embed.add_field(
            name="Alt Number", value=f"{pagenumber}/{self.listlength - 1}", inline=True
        )
        embed.add_field(
            name="# Server Bans (including expired)",
            value=f"{len(self.users[bmid]['serverbans'])}",
            inline=True,
        )

        if self.users[bmid]["gamebans"]["eac_ban_count"] == "0":
            embed.add_field(
                name="Gamebanned?",
                value=f"False",
                inline=True,
            )
        else:
            twitterurl = self.users[bmid]["gamebans"]["url"]
            daysago = self.users[bmid]["gamebans"]["days_ago"]
            embed.add_field(
                name="Gamebanned?",
                value=f"[True]({twitterurl}) {daysago} day(s) ago",
                inline=True,
            )
        embed.add_field(
            name="Rust",
            value=f"{self.users[bmid]['playerinfo']['rusthours']}",
            inline=True,
        )
        embed.add_field(
            name="Aimtrain",
            value=f"{self.users[bmid]['playerinfo']['aimtrain']}",
            inline=True,
        )
        namematches = ""
        for i in self.users[bmid]["compared"]:
            namematches += (
                f"**{i['name1']}** against **{i['name2']}** -> {i['match_ratio']}%\n"
            )
        embed.add_field(
            name="Name Matches",
            value=f"{namematches}",
            inline=False,
        )

        if self.users[bmid]["country"]:
            embed.add_field(
                name="Country", value=f"{self.users[bmid]['country']}", inline=True
            )
        else:
            embed.add_field(name="Country", value=f"Unknown", inline=True)

        if self.users[bmid]["isp"]:
            embed.add_field(name="ISP", value=f"{self.users[bmid]['isp']}", inline=True)
        else:
            embed.add_field(name="ISP", value=f"Unknown", inline=True)

        if self.users[bmid]["lastcheck"]:
            embed.add_field(
                name="lastcheck", value=f"{self.users[bmid]['lastcheck']}", inline=True
            )
        else:
            embed.add_field(name="lastcheck", value=f"Unknown", inline=True)

        embed.set_footer(text="Created by Gnomeslayer#5551")
        return embed


async def setup(client):
    await client.add_cog(Battlemetrics(client))


# noinspection SpellCheckingInspection
class BMAPI:
    def __init__(self):
        # Suggestion: Use TOML instead of JSON for configuration. It is more convinient.
        with open("./json/config.json", "r") as config_file:
            mytokens = json.load(config_file)
        self.url_base = "https://api.battlemetrics.com/"
        self.bmtoken = f"Bearer {mytokens['battlemetrics_token']}"
        self.vpntoken = mytokens["vpn_token"]
        self.steamtoken = mytokens["steam_token"]
        self.rustbannedapi = mytokens["rustbanned_token"]

    async def get_names(self, bm_id):

        response = ""
        my_headers = {
            "Authorization": f"{config['battlemetrics_token']}",
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
                serverid = d["relationships"]["server"]["data"]["id"]
                servername = "Unknown"
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
        url_extension = f"players/{bmid}?include=server,identifier&fields[server]=name"
        url = f"{self.url_base}{url_extension}"
        response = ""
        async with aiohttp.ClientSession(
            headers={"Authorization": self.bmtoken}
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
