import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

async def main():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=['!', '>'], intents=intents, owner_id=int(os.getenv('OWNER_ID')))

    await bot.load_extension("cogs.general")

    # TODO: kirim pesan ketika prefix '>' digunakan pada channel yg tidak sesuai
    await bot.load_extension("cogs.expenses")
    
    @bot.event
    async def on_ready():
        print(f'{bot.user.name} has connected')
    
    @bot.command(name='reload', hidden=True)
    @commands.is_owner()
    async def reload_cog(ctx, *, cog_name):
        fullname = f"cogs.{cog_name}"
        try:
            await bot.reload_extension(fullname)
            await ctx.send(f"{fullname} reloaded successfully!")
            print(f"{fullname} reloaded successfully!")
        except Exception as e:
            print(e)

    await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
