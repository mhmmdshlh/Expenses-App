from discord.ext import commands
import discord
from datetime import datetime

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def cog_check(self, ctx):
        return ctx.prefix == '!'
    
    @commands.command()
    async def foo(self, ctx, *, arg):
        await ctx.send(arg)

    @commands.command()
    async def info(self, ctx):
        embed = discord.Embed(
            title="Bot Information",
            description="A powerful Discord bot built with Discord.py",
            color=discord.Color.blue()
        )
        embed.add_field(name="Author", value="Your Name", inline=True)
        embed.add_field(name="Version", value="1.0", inline=True)
        embed.set_footer(text="Thanks for using our bot!")
        
        await ctx.send(embed=embed)
    
    @commands.command() 
    async def userinfo(self, ctx, member: discord.Member = None):
        """Displays detailed information about a user."""
        if member is None:
            member = ctx.author

        embed = discord.Embed(
            title=f"User Information for {member.name}",
            description=f"Here's what I found about {member.mention}.",
            color=discord.Color.blue(), 
            timestamp=datetime.now() 
        )
        
        embed.set_author(name=f"{member.name}#{member.discriminator}", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"), inline=True)
        
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        if roles:
            embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles), inline=False)
        else:
            embed.add_field(name="Roles", value="This user has no roles.", inline=False)

        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="Is Bot?", value=member.bot, inline=True)

        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))
