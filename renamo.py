import argparse
import asyncio
import bot_config
import discord
import time


from discord import app_commands
from discord import ui
from discord.ext import commands


EMOJI="✅"
BAN_EMOJI="🚫"
CONFIRM="👌"
TIMELIMIT = 10 * 60 # in seconds
PENSIVE_EMOJI="😔"
CHECK_EMOJI = "✅"
YAWN_EMOJI = "🥱"


CONFIG = bot_config.live_config
REACTION_LIMIT = 4


class Renamo(commands.Cog):
  def __init__(self, bot: commands.Bot):
    super().__init__()
    self.bot = bot
    self.tracked_messages = {} # message_id -> victim, new_name
    self.renames = {} # user id -> (nickname, timestamp)

  @commands.Cog.listener()
  async def on_ready(self):
    guild = self.bot.get_guild(CONFIRM.guild_id)
    if not guild:
      print(f"Unable to find guild with id {CONFIRM.guild_id}. Shutting down...")
      await self.close()
      return

    self.bot.tree.copy_global_to(guild=guild)
    await self.bot.tree.sync(guild=guild)
    print(f"Running as {self.bot.user} in {guild}!")

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message):
    if message.content.startswith("!rename"):
      await message.reply("The future is here! Use `/rename` instead!")

  @commands.Cog.listener()
  async def on_reaction_add(self, reaction: discord.Reaction, reactor: discord.Member):
    if str(reaction.emoji) != CHECK_EMOJI:
      return

    if reaction.message.id not in self.tracked_messages:
      return
    victim, new_name = self.tracked_messages[reaction.message.id]

    if reactor.bot and reactor.id != self.bot.user.id:
      await reaction.remove(reactor)
      await reaction.message.channel.send( f"Bots can't vote, {reactor.display_name}.")
      return

    if reaction.count == REACTION_LIMIT:
      try:
        self.renames[victim.id] = (new_name, time.time()+TIMELIMIT)
        self.tracked_messages.pop(reaction.message.id)
        await victim.edit(nick=new_name)
        await reaction.message.add_reaction(CONFIRM)
        await reaction.message.channel.send("> Hello, " + victim.mention + "!")
      except Exception as e:
        print(f"Failed to rename {victim}: {e}")
        await reaction.message.add_reaction(PENSIVE_EMOJI)
        await reaction.message.channel.send(
            f"Sorry, {victim.mention} is too sensitive to rename. {PENSIVE_EMOJI}")

  @commands.Cog.listener()
  async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
    if str(reaction.emoji) != CHECK_EMOJI:
      return

    if reaction.message.id in self.tracked_messages:
      print(f"{user} removed their reaction!")

  @commands.Cog.listener()
  async def on_member_update(self, before: discord.Member, after: discord.Member):
    try:
      new_name, end = self.renames[after.id]
      if after.display_name != new_name and time.time() < end:
        print(f"Correcting {after.display_name} back to {new_name}.")
        await after.edit(nick=new_name)
    except KeyError:
      pass

  @app_commands.command()
  @app_commands.guilds(CONFIRM.guild_id)
  async def rename(self, itx: discord.Interaction, user: discord.Member, new_name: str):
    if len(new_name) > 32:
      await message.response.send_message(f"Too long; didn't read. {YAWN_EMOJI}", ephemeral=True)
      return

    if user.id == self.bot.user.id:
      await itx.response.send_message("I'm too sophisticated for your puny human names.", ephemeral=True)
      return

    await itx.response.send_message(
        content=f"> {itx.user.mention} wants to rename {user.mention} to {new_name}.\n\nVote with {EMOJI}!")
    new_message = await itx.original_message()

    self.tracked_messages[new_message.id] = (user, new_name)
    await new_message.add_reaction(EMOJI)


async def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "discord_token", help="The path to your Discord bot token.")
  args = parser.parse_args()

  with open(args.discord_token, "r") as token_file:
    discord_token = token_file.read().strip()

  intents = discord.Intents.default()
  intents.members = True
  intents.messages = True
  intents.message_content = True

  bot = commands.Bot("/", intents=intents)
  async with bot:
    await bot.add_cog(Renamo(bot))
    await bot.start(discord_token)


if __name__ == "__main__":
  asyncio.run(main())
