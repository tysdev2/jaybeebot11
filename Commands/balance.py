import discord
from discord import app_commands
from discord.ext import commands
import json
import sqlite3
import random
import requests


class Balance(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.invites = {}
        client.loop.create_task(self.load())

    async def load(self):
        await self.client.wait_until_ready()
        # load the invites
        for guild in self.client.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except:
                pass

    def connect(self):
        try:
            conn = sqlite3.connect(f"Data/users.db")
            curs = conn.cursor()
            return conn, curs
        except Exception as exc:
            print(exc)
            return None

    def find_invite_by_code(self, inv_list, code):
        for inv in inv_list:
            if inv.code == code:
                return inv


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            invs_before = self.invites[member.guild.id]
            invs_after = await member.guild.invites()
            self.invites[member.guild.id] = invs_after

            
            result = Balance.connect(self)
            if result is None:
                return

            conn = result[0]
            curs = result[1]

            query = f"""INSERT OR IGNORE INTO users(id, points, invites) VALUES({member.id}, 0, 0)"""
            curs.execute(query)
            conn.commit()
            conn.close()

            diff = (member.joined_at - member.created_at).total_seconds()
            if diff < 1814400:  # under 21 days old
                return


            for invite in invs_before:
                if invite.uses < self.find_invite_by_code(invs_after, invite.code).uses:
                    self.client.waiting[member.id] = invite.inviter.id
                    # elif member.id in self.client.waiting[invite.inviter.id]:
                        # return
                    # else:
                        # self.client.waiting[invite.inviter.id].append(member.id)
        except Exception as exc:
            print(exc)
            return



    @app_commands.command(name="withdraw", description="Withdraw your points")
    @app_commands.describe(
        points="Points to withdraw",
        username="Site username"
    )
    async def withdraw(self, interaction: discord.Interaction, points: int, username: str):
        with open("Data/config.json", "r+", encoding="utf-8") as f:
            config = json.load(f)
            key = config["key"]
            url1 = config["site_url"]
            url2 = config["instant_url"]

        await interaction.response.defer(thinking=False)
        result = Balance.connect(self)
        if result is None:
            return

        conn = result[0]
        curs = result[1]

        query = f"""SELECT * FROM users WHERE id={interaction.user.id}"""
        curs.execute(query)
        records = curs.fetchall()


        if len(records) == 0:
            balance = 0
            query = f"""INSERT OR IGNORE INTO users(id, points, invites) VALUES({interaction.user.id}, 0, 0)"""
            curs.execute(query)
            conn.commit()
        else:
            balance = records[0][1]

        if points > balance:
            await interaction.followup.send(f"You don't have enough points!")
            return

        rs = requests.Session()
        headers = {
            "username": username,
            "points": str(points),
            "key": key
        }

        class ChoiceView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)


            @discord.ui.button(label="Site Balance", custom_id=f"site_balance")
            async def sitebalance(self, inter: discord.Interaction, button: discord.Button):

                if interaction.user.id != inter.user.id:
                    return

                source = rs.post(url1, headers=headers)
                if source.status_code == 200:
                    query = f"""UPDATE users SET (points) = ({(balance - points) if (balance - points) > 0 else 0}) WHERE id={inter.user.id}"""
                    curs.execute(query)
                    conn.commit()
                    conn.close()

                    emb = discord.Embed(title=f"Withdrawal Completed",
                                        description=f"Withdrawal to site balance has been confirmed.",
                                        colour=discord.Colour.green())
                    emb.add_field(name="Username", value=username, inline=False)
                    emb.add_field(name="Points", value=points, inline=False)
                    await inter.response.send_message(embed=emb)
                    return
                else:
                    await inter.response.send_message(f"Invalid username! Status code: {source.status_code}",
                                                      ephemeral=True)

                self.stop()
                return


            @discord.ui.button(label="Instantly", custom_id=f"instantly")
            async def instantly(self, inter: discord.Interaction, button: discord.Button):

                if interaction.user.id != inter.user.id:
                    return

                source = rs.post(url2, headers=headers)
                if source.status_code == 200:
                    query = f"""UPDATE users SET (points) = ({(balance - points) if (balance - points) > 0 else 0}) WHERE id={inter.user.id}"""
                    curs.execute(query)
                    conn.commit()
                    conn.close()

                    emb = discord.Embed(title=f"Withdrawal Completed",
                                        description=f"Instant withdrawal has been confirmed.",
                                        colour=discord.Colour.green())
                    emb.add_field(name="Username", value=username, inline=False)
                    emb.add_field(name="Points", value=points, inline=False)
                    await inter.response.send_message(embed=emb)
                    return
                else:
                    await inter.response.send_message(f"Invalid username! Status code: {source.status_code}",
                                                      ephemeral=True)

                self.stop()
                return


        emb = discord.Embed(title=f"Withdraw Menu", description=f"Select the option of withdrawal.",
                            colour=discord.Colour.green())
        emb.add_field(name="Username", value=username, inline=False)
        emb.add_field(name="Points", value=points, inline=False)
        emb.set_footer(text="Expires in 5 minutes", icon_url=None)
        await interaction.followup.send(embed=emb, view=ChoiceView())
        return



    @withdraw.error
    async def catch(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        print(error)





    @app_commands.command(name="balance", description="Displays your points balance & invites")
    async def balance(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        result = Balance.connect(self)
        if result is None:
            return

        conn = result[0]
        curs = result[1]

        query = f"""SELECT * FROM users WHERE id={interaction.user.id}"""
        curs.execute(query)
        records = curs.fetchall()

        if len(records) == 0:
            points = 0
            invites = 0
            query = f"""INSERT OR IGNORE INTO users(id, points, invites) VALUES({interaction.user.id}, 0, 0)"""
            curs.execute(query)
            conn.commit()
        else:
            points = records[0][1]
            invites = records[0][2]

        conn.close()
        emb = discord.Embed(title=f"Balance", description=f"",
                            colour=discord.Colour.green())
        emb.add_field(name="Points", value=points, inline=False)
        emb.add_field(name="Total Invites", value=invites, inline=False)
        await interaction.followup.send(embed=emb)
        return


    @app_commands.command(name="daily", description="Claim daily reward")
    @app_commands.checks.cooldown(1, 86400, key=lambda i: i.user.id)
    async def daily(self, interaction: discord.Interaction):

        with open("Data/config.json", "r+", encoding="utf-8") as f:
            config = json.load(f)
            roleid = config["role_id"]
            role = interaction.guild.get_role(roleid)
            member = interaction.guild.get_member(interaction.user.id)

        if role is not None:
            if role not in member.roles:
                await interaction.response.send_message("You are not verified!", ephemeral=True)
                return

        await interaction.response.defer(thinking=False)
        result = Balance.connect(self)
        if result is None:
            return

        conn = result[0]
        curs = result[1]

        query = f"""SELECT * FROM users WHERE id={interaction.user.id}"""
        curs.execute(query)
        records = curs.fetchall()

        if len(records) == 0:
            points = 0
            query = f"""INSERT OR IGNORE INTO users(id, points, invites) VALUES({interaction.user.id}, 0, 0)"""
            curs.execute(query)
            conn.commit()
        else:
            points = records[0][1]


        choicelist = [35, 85, 150, 250, 1000]  # rewards in millions
        weightlist = [60, 25, 10, 4.5, 0.5]  # percentages

        choice = random.choices(choicelist, weights=weightlist, k=1)[0]
        points += choice
        query = f"""UPDATE users SET (points) = ({points}) WHERE id={interaction.user.id}"""
        curs.execute(query)
        conn.commit()
        conn.close()

        emb = discord.Embed(title="Daily Reward", description=f"You claimed **{choice}** points.", colour=discord.Colour.green())
        emb.add_field(name=f"Total Points", value=points, inline=False)
        await interaction.followup.send(embed=emb)
        return

    @daily.error
    async def catch_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):

        if isinstance(error, app_commands.CommandOnCooldown):
            if error.retry_after < 60:
                wait = round(error.retry_after)
                await interaction.response.send_message(
                    f"Wait **{wait} second{'' if wait == 1 else 's'}** before you can claim your daily reward.",
                    ephemeral=True)
                return
            elif error.retry_after < 3600:
                wait = round(error.retry_after / 60)
                await interaction.response.send_message(
                    f"Wait **{wait} minutes{'' if wait == 1 else 's'}** before you can claim your daily reward.", ephemeral=True)
                return
            else:
                wait = round(error.retry_after / 3600)
                await interaction.response.send_message(
                    f"Wait **{wait} hour{'' if wait == 1 else 's'}** before you can claim your daily reward.", ephemeral=True)
                return
        else:
            print(error)







    @balance.error
    async def catch(self, interaction, error):
        print(error)


async def setup(client):
    await client.add_cog(Balance(client))
