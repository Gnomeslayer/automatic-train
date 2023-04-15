import discord
from discord import app_commands
from discord.ext import commands
import json, traceback

class Suggestions(commands.Cog):
    
    def __init__(self, client):
        print("[Cog] Suggestions has been initiated")
        self.client = client
        with open("./json/config.json", "r") as f:
            config = json.load(f)
        self.config = config
        self.stalks = []
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == self.config['suggestions_channel']:
            if not message.author.bot:
                buttons = SuggestButtons()
                reply = await message.reply("Please use the slash command **/suggest** or click this button", view=buttons)
                await message.delete()
                await reply.delete(delay=300)
    
    @app_commands.command(name="suggest", description="Suggest something for the servers!")
    async def suggest(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SuggestionForm())
        
class SuggestButtons(discord.ui.View):
    @discord.ui.button(label="Make a suggestion!", style=discord.ButtonStyle.green)
    async def admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionForm())
        
class AdminButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.suggestion_id = 0
        
    @discord.ui.button(label="Approve Suggestion", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.guild_permissions.administrator:
            responseform = ResponseForm_approve()
            responseform.suggestion_number = self.suggestion_id
            await interaction.response.send_modal(responseform)
        
        
    @discord.ui.button(label="Reject Suggestion", style=discord.ButtonStyle.red)
    async def Reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.guild_permissions.administrator:
            responseform = ResponseForm_reject()
            responseform.suggestion_number = self.suggestion_id
            await interaction.response.send_modal(responseform)
        
class SuggestionForm(discord.ui.Modal, title="Apply to become staff for this server!"):
    def __init__(self):
        super().__init__()
    
    suggestion = discord.ui.TextInput(
        label="What is your suggestion?",
        style=discord.TextStyle.long,
        placeholder="Your suggestion goes here",
        max_length=1000,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        buttons = AdminButtons()
        stored_suggestions = ''
        config = ''
        with open('./json/config.json', 'r') as f:
            config = json.load(f)
        with open('./json/suggestions.json', 'r') as f:
            stored_suggestions = json.load(f)
        suggestionschannel = interaction.guild.get_channel(config['suggestions_channel'])
        
        buttons.suggestion_id = len(stored_suggestions)
        embed = discord.Embed(title=f'Suggestion #{len(stored_suggestions)} from {interaction.user}', color=int(config['suggestion_color'], base=16))
        embed.add_field(name='The suggestion', value=f'```{self.suggestion.value}```', inline=False)
        icon_url=interaction.user.display_avatar
        embed.set_footer(text=f"{config['footer_text']}", icon_url=icon_url)
        suggestion_message = await suggestionschannel.send(embed=embed, view=buttons)
        message_id = suggestion_message.id
        await interaction.response.send_message("Thank you for making a suggestion!", ephemeral=True)
        current_suggestion = [{'message_id': message_id, 'suggester': str(interaction.user), 'suggester_id': int(interaction.user.id), 'suggestion': self.suggestion.value, 'status': 'Unreviewed', 'response': 'None'}]
        stored_suggestions += current_suggestion
        with open('./json/suggestions.json', 'w') as f:
            f.write(json.dumps(stored_suggestions, indent=4))
            
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)

class ResponseForm_approve(discord.ui.Modal, title="Approval form"):
    def __init__(self):
        super().__init__()
        self.suggestion_number = 0
    
    myresponse = discord.ui.TextInput(
        label="Reason for approving this suggestion?",
        style=discord.TextStyle.long,
        placeholder="Your response goes here.",
        max_length=1000,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = ''
        with open('./json/config.json', 'r') as f:
            config = json.load(f)
        stored_suggestions = ''
        with open('./json/suggestions.json', 'r') as f:
            stored_suggestions = json.load(f)
               
        responsechannel = interaction.guild.get_channel(config['suggestions_response_channel'])
        suggestionschannel = interaction.guild.get_channel(config['suggestions_channel'])
        stored_suggestions[self.suggestion_number]['response'] = self.myresponse.value
        stored_suggestions[self.suggestion_number]['status'] = 'approved'
        suggester = interaction.guild.get_member(stored_suggestions[self.suggestion_number]['suggester_id'])
        message = await suggestionschannel.fetch_message(stored_suggestions[self.suggestion_number]['message_id'])
        embed = discord.Embed(title=f"Suggestion #{self.suggestion_number} from {stored_suggestions[self.suggestion_number]['suggester']}", color=int(config['approval_color'], base=16))
        embed.add_field(name='The suggestion', value=f"```{stored_suggestions[self.suggestion_number]['suggestion']}```", inline=False)
        embed.add_field(name='Status', value=f"Approved.", inline=False)
        embed.add_field(name='Response', value=f"```{self.myresponse.value}```", inline=False)
        embed.set_footer(text=f"{config['footer_text']}")
        if config['send_response_to_user']:
            await suggester.send(embed=embed)
            await interaction.response.send_message("Thank you for approving a suggestion!\nI have contacted the person who made the suggestion.", ephemeral=True)
        else:
            await interaction.response.send_message("Thank you for approving this suggestion!", ephemeral=True)
        
        await message.delete()
        
        
        if config['send_response_to_channel']:
            await responsechannel.send(embed=embed)
        with open('./json/suggestions.json', 'w') as f:
            f.write(json.dumps(stored_suggestions, indent=4))
        
            
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)
        
class ResponseForm_reject(discord.ui.Modal, title="Reject form"):
    def __init__(self):
        super().__init__()
        self.suggestion_number = 0
    
    myresponse = discord.ui.TextInput(
        label="Reason for rejecting this suggestion?",
        style=discord.TextStyle.long,
        placeholder="Your response goes here.",
        max_length=1000,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        config = ''
        with open('./json/config.json', 'r') as f:
            config = json.load(f)
        stored_suggestions = ''
        with open('./json/suggestions.json', 'r') as f:
            stored_suggestions = json.load(f)
               
        responsechannel = interaction.guild.get_channel(config['suggestions_response_channel'])
        suggestionschannel = interaction.guild.get_channel(config['suggestions_channel'])
        stored_suggestions[self.suggestion_number]['response'] = self.myresponse.value
        stored_suggestions[self.suggestion_number]['status'] = 'rejected'
        suggester = interaction.guild.get_member(stored_suggestions[self.suggestion_number]['suggester_id'])
        message = await suggestionschannel.fetch_message(stored_suggestions[self.suggestion_number]['message_id'])
        embed = discord.Embed(title=f"Suggestion #{self.suggestion_number} from {stored_suggestions[self.suggestion_number]['suggester']}", color=int(config['rejection_color'], base=16))
        embed.add_field(name='The suggestion', value=f"```{stored_suggestions[self.suggestion_number]['suggestion']}```", inline=False)
        embed.add_field(name='Status', value=f"Rejected.", inline=False)
        embed.add_field(name='Response', value=f"```{self.myresponse.value}```", inline=False)
        embed.set_footer(text=f"{config['footer_text']}")
        if config['send_response_to_user']:
            await suggester.send(embed=embed)
            await interaction.response.send_message("Thank you for rejecting a suggestion!\nI have contacted the person who made the suggestion.", ephemeral=True)
        else:
            await interaction.response.send_message("Thank you for rejecting this suggestion!", ephemeral=True)
        
        await message.delete()
        
        
        if config['send_response_to_channel']:
            await responsechannel.send(embed=embed)
        with open('./json/suggestions.json', 'w') as f:
            f.write(json.dumps(stored_suggestions, indent=4))
            
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)
        
async def setup(client):
    await client.add_cog(Suggestions(client))