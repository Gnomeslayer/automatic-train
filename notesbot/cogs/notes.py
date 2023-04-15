import discord
from discord import app_commands
from discord.ext import commands
import traceback
import json, aiohttp, validators


TEST_GUILD = discord.Object(794837147068792862)

class notes(commands.Cog):
    
    def __init__(self, client):
        print("[Cog] Notes has been initiated")
        self.client = client
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        self.config = config
       

    @app_commands.command(name="note", description="Create a note!")
    async def note(self, interaction: discord.Interaction):
        if len(self.config['allowed_channels']) > 0:
            if interaction.channel.id in self.config['allowed_channels']:
                await interaction.response.send_modal(Note())
            else:
                await interaction.response.send_message("You cannot use that command in this channel. Please contact the bot manager for more information.", ephemeral=True)
        else:
            await interaction.response.send_modal(Note())
            
            
class Note(discord.ui.Modal, title='Gnomeslayers note maker.'):
        
    steam = discord.ui.TextInput(
        label='steam id/url, bm link',
        placeholder='https://www.battlemetrics.com/rcon/players/579979635',
        required=True,
    )
    note = discord.ui.TextInput(
        label='The note',
        style=discord.TextStyle.long,
        placeholder='Type the note here.',
        required=True,
    )
    async def on_submit(self, interaction: discord.Interaction):
        userids = await self.get_ids(self.steam.value)
        thenote = f"Submitted by: {interaction.user} ({interaction.user.id})\n{self.note.value}"
        await self.makenote(note=thenote, bmid=userids['bmid'])
        await interaction.response.send_message(f"Thank you {interaction.user} for submitting a note!\nThis was created by Gnomeslayer#5551", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__) 
        
    async def makenote(self, note, bmid):
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        url = f"https://api.battlemetrics.com/players/{bmid}/relationships/notes"
        my_headers = {"Authorization": f"Bearer {config['battlemetrics_token']}"}
        response = ""
        json_post = {
            "data": {
                "type": "playerNote",
                "attributes": {
                    "note": note,
                    "shared": True,
                },
                "relationships": {
                    "organization": {
                        "data": {
                            "type": "organization",
                            "id": f"{config['organization_id']}",
                        }
                    }
                }
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url,json=json_post, headers=my_headers) as r:
                response = await r.json()
                
    async def get_ids(self, submittedtext):
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
    
    async def search_bm(self, steamid):
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        """Takes a steam ID and converts it into a BM id for use."""
        url_extension = f"players?filter[search]={steamid}&include=identifier"
        url = f"https://api.battlemetrics.com/{url_extension}"

        my_headers = {"Authorization": f"Bearer {config['battlemetrics_token']}"}
        response = ""
        async with aiohttp.ClientSession(headers=my_headers) as session:
            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data["data"][0]["id"] if data["data"] else ""
    
    async def get_id_from_steam(self, url):
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        """Takes the URL (well part of it) and returns a steam ID"""
        url = (
            f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?format=json&"
            f"key={config['steam_token']}&vanityurl={url}&url_type=1"
        )
        data = ""
        async with aiohttp.ClientSession(
            headers={"Authorization": config['steam_token']}
        ) as session:

            async with session.get(url=url) as r:
                response = await r.json()
        data = response
        return data["response"]["steamid"] if data["response"]["steamid"] else 0
                
async def setup(client):
    await client.add_cog(notes(client))