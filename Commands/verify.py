import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import random
import string
import sqlite3


class Verify(commands.Cog):
    def __init__(self, client):
        self.client = client


    def connect(self):
        try:
            conn = sqlite3.connect(f"Data/users.db")
            curs = conn.cursor()
            return conn, curs
        except Exception as exc:
            print(exc)
            return None


    @app_commands.command(name="help", description="Displays all commands")
    async def help(self, interaction: discord.Interaction):
        emb = discord.Embed(title=f"Help",
                            colour=discord.Colour.green())
        emb.add_field(name="/balance", value="Displays points & invites balance.", inline=False)
        emb.add_field(name="/withdraw", value="Withdraw points.", inline=False)
        emb.add_field(name="/panel", value="Sends verify panel.", inline=False)
        await interaction.response.send_message(embed=emb)
        return

    @app_commands.command(name="panel", description="Sends verify panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):
        class VerifyView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                self.add_item(discord.ui.Button(emoji="✅", label=f"Verify", style=discord.ButtonStyle.grey, custom_id=f"verify"))

        emb = discord.Embed(title=f"Verify", description=f"Click the button on this message to solve a captcha and verify in the server.",
                            colour=discord.Colour.green())
        await interaction.response.send_message("Panel sent", ephemeral=True)
        await interaction.channel.send(embed=emb, view=VerifyView())
        return


    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        try:

            with open("Data/config.json", "r+", encoding="utf-8") as f:
                config = json.load(f)
                roleid = config["role_id"]

            if interaction.data['custom_id'].startswith("verify"):
                member = interaction.guild.get_member(interaction.user.id)
                role = interaction.guild.get_role(roleid)

                if role in member.roles:
                    await interaction.response.send_message("You are already verified!", ephemeral=True)
                    return

                code = "".join(random.choices(string.ascii_letters + string.digits, k=8))
                emb = discord.Embed(title="Verification", description=f"", colour=discord.Colour.green())
                emb.add_field(name=f"Code",
                              value=f"``{code}``\n\nYou have 5 minutes to reply with the code above to verify yourself in **{interaction.guild.name}**.",
                              inline=False)
                try:
                    await interaction.user.send(embed=emb)
                except Exception as exc:
                    await interaction.response.send_message("Please allow DM's from this bot to verify.",
                                                            ephemeral=True)
                    return exc

                await interaction.response.send_message("Check your DM's to complete verification.", ephemeral=True)

                def checker(m):
                    return m.author.id == interaction.user.id and m.channel.id == interaction.user.dm_channel.id

                while True:
                    try:
                        result = await self.client.wait_for("message", check=checker, timeout=300)
                        if result.content != code:
                            await result.reply("Invalid code! Try again.")
                            continue
                        else:
                            if interaction.user.id in self.client.waiting:
                                result1 = Verify.connect(self)
                                if result1 is None:
                                    return

                                conn = result1[0]
                                curs = result1[1]

                                query = f"""INSERT OR IGNORE INTO users(id, points, invites) VALUES({self.client.waiting[interaction.user.id]}, 0, 0)"""
                                curs.execute(query)
                                conn.commit()
                                query = f"""SELECT * FROM users WHERE id={self.client.waiting[interaction.user.id]}"""
                                curs.execute(query)
                                records = curs.fetchall()
                                points = records[0][1]
                                invites = records[0][2]
                                invites += 1
                                points += 100
                                query = f"""UPDATE users SET (invites, points) = ({invites}, {points}) WHERE id={self.client.waiting[interaction.user.id]}"""
                                curs.execute(query)
                                conn.commit()
                                conn.close()
                                del self.client.waiting[interaction.user.id]

                            await result.reply(f"You are now verified in **{interaction.guild.name}**")
                            await member.add_roles(role)
                            return
                    except asyncio.TimeoutError:
                        await interaction.user.send("Verification cancelled.")
                        return
                    except Exception as exc:
                        print(exc)
                        return exc
        except Exception as exc:
            raise(exc)






async def setup(client):
    await client.add_cog(Verify(client))
