import asyncio
import datetime
import json
import math
import os
import random
import time
from urllib.parse import quote

import discord
import matplotlib.pyplot as plt
import numpy as np
import requests
from discord.ext import commands, tasks
from discord_slash import SlashCommand
from dotenv import load_dotenv
from pretty_help import PrettyHelp
from scipy.interpolate import make_interp_spline

from keep_alive import keep_alive

load_dotenv()

intents = discord.Intents.default()

intents.presences = True
intents.members = True

bot = commands.Bot(intents=intents, command_prefix='!')

bot.help_command = PrettyHelp(color=0xcf7336) # 0xcf7336 should be used for all embeds

# client = discord.Client()
slash = SlashCommand(bot, sync_commands=True)

with open("jsons/discord2steamid.json",'r') as f:

	discord2steam = json.load(f)
	f.close()

with open("jsons/hours.json",'r') as f:

	hours = json.load(f)
	f.close()


async def heartbeat():

	global ping_arr
	global time_ping
	ping_arr = np.array([])

	await bot.wait_until_ready()
	while not bot.is_closed():

		if len(ping_arr) < 16:

			ping_arr = np.append(ping_arr, int(round(bot.latency * 1000, 3)))
			time_ping = time.time()

		else:

			ping_arr = np.delete(ping_arr, 0)
			ping_arr = np.append(ping_arr, int(round(bot.latency * 1000, 3)))
			time_ping = time.time()

		await asyncio.sleep(40)
		

async def check_hours_played():

	await bot.wait_until_ready()
	while not bot.is_closed():

		global hours
		global discord2steam
		
		with open("jsons/discord2steamid.json",'r') as f:

			discord2steam = json.load(f)
			f.close()


		for user_id in list(discord2steam):


			url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={os.getenv('steamtoken')}&input_json="+quote(f'{{"steamid": {discord2steam[user_id]}, "include_played_free_games": true, "appids_filter": [440]}}')

			r = requests.get(url)

			try:

				hours_played = json.loads(r.text)['response']['games'][0]['playtime_forever']/60
				
				# print(user_id + ': ' + discord2steam[user_id] + ': ' + str(hours_played))

				try:

					if (hours_played // 100) > (hours[user_id] // 100):
					
						embed=discord.Embed(title="Congratulations!", description=f"<@{user_id}> has reached **{str(int((hours_played // 100)*100))} hours** in TF2!", color=0xcf7336)

						embed.timestamp = datetime.datetime.utcnow()

						await bot.get_channel(890820026800676894).send(embed=embed)
				
				except KeyError: # New entry in dict

					pass

				hours[user_id] = hours_played

			except KeyError:

				pass

		print('hours updated')

		with open("jsons/hours.json", 'w') as f:

			json.dump(hours, f, indent=4)
			f.close()

		with open("jsons/hours.json", 'r') as f:
			
			hours = json.load(f)
			f.close()
			

		await asyncio.sleep(300) # checks every 5 minutes


playingStatus = ['Ultiduos', 'Spire MGE', 'Uncletopia | Atlanta 1', '24/7 plr_hightower'
				 ]


users = list(discord2steam)


@bot.event
async def on_ready():

	print('Logged in as {0.user}'.format(bot), ' - ', bot.user.id)

	while True:

		statusNum = random.randint(0, len(playingStatus) - 1)
		await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=playingStatus[statusNum]))

		await asyncio.sleep(10)


@bot.command(brief='Checks whos online',description='Checks whos online')
async def online(ctx):

	async with ctx.typing():

		users_playing = {}
		users_in_menu = []

		for user_id in users: # adds user info if they are on a server in tf2 to users_playing

			r = requests.get(f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={os.getenv('steamtoken')}&steamids={discord2steam[user_id]}")
			status = json.loads(r.text)['response']['players'][0]

			try:

				if status['gameid'] == '440':

					try:
				
						users_playing[status['personaname']] = status['gameserverip'] # eg. {'Generic':'64.94.100.34:27015'}

					except KeyError: # not in a server

						users_in_menu.append(status['personaname'])

			except KeyError: # ignore if not playing tf2

				pass

		if len(users_playing) == 0 and len(users_in_menu) == 0: # no user online

			embed=discord.Embed(title="no one is in a server rn :(", color=0xcf7336)

		else:

			server_ips = {} # groups users by server ip theyre connected to

			for i, j in users_playing.items(): # shamelessly stolen from Stack Overflow lol

				server_ips[j] = [i] if j not in server_ips.keys() else server_ips[j] + [i]

			embed=discord.Embed(title="People Currently Playing TF2", color=0xcf7336)


			if len(users_in_menu) != 0:

				connected = ""

				for player in users_in_menu:
					
					connected += ("> **" + player + "**\n")
				
				connected = connected.strip()

				embed.add_field(name="In Menu", value=connected, inline=False)


			for ip_port in list(server_ips):

				ip, port = ip_port.split(":")

				r = requests.get(f"https://teamwork.tf/api/v1/quickplay/server?ip={ip}&port={port}&key={os.getenv('teamworktoken')}")

				try:

					server = json.loads(r.text)[0]

					connected = ""

					for player in server_ips[ip_port]:
						
						connected += ("> **" + player + "**\n")
					
					connected = connected.strip()

					embed.add_field(name="Server Name", value=server['name'], inline=True)
					embed.add_field(name="IP", value=ip_port, inline=True)
					embed.add_field(name="Join this server", value=f"steam://connect/{ip_port}", inline=True)

					embed.add_field(name="Playing on this server", value=connected, inline=False)
					

				except (IndexError, KeyError) as e: # server not community or not on teamwork.tf list

					connected = ""

					for player in server_ips[ip_port]:
						
						connected += ("> **" + player + "**\n")

					connected = connected.strip()

					embed.add_field(name="Server Name", value='Unknown (Valve or private server not on teamwork.tf)', inline=True)
					embed.add_field(name="IP", value=ip_port, inline=True)
					embed.add_field(name="Join this server", value=f"steam://connect/{ip_port}", inline=True)

					embed.add_field(name="Playing on this server", value=connected, inline=False)

			
		embed.set_footer(text=((f'Requested by {ctx.message.author.display_name} (') + str(ctx.message.author.id) + ')'))
		embed.timestamp = datetime.datetime.utcnow()


	# embed.add_field(name='Activity Details', value=str(member.activity.details), inline=False)
	await ctx.send(embed=embed)


@bot.command(brief='Returns user info',description='Returns user info')
async def user(ctx, member: discord.Member):

	embed=discord.Embed(title="User Information", color=0xcf7336)
	embed.add_field(name='Server', value='**'+str(member.guild)+'**', inline=False)
	embed.add_field(name='Username', value=member, inline=False)
	embed.add_field(name='Server Nickname', value=member.nick, inline=False)
	embed.add_field(name='ID', value='`'+str(member.id)+'`', inline=False)
	embed.add_field(name='Status', value='`'+str(member.status)+'`', inline=False)
	embed.add_field(name='Joined', value='`'+str(member.joined_at)+'`', inline=False)
	embed.add_field(name='Role', value=str(member.top_role), inline=False)
		
	embed.set_footer(text=((f'Requested by {ctx.message.author.display_name} (') + str(ctx.message.author.id) + ')'))
	embed.timestamp = datetime.datetime.utcnow()


	# embed.add_field(name='Activity Details', value=str(member.activity.details), inline=False)
	await ctx.send(embed=embed)


@bot.command(brief='Returns latency to the server',description='Returns latency to the server in milliseconds')
async def ping(ctx):

	embed=discord.Embed(title="Pong!", color=0xcf7336)
	embed.add_field(name="Latency", value=(f'`{round(bot.latency * 1000, 3)}ms`'), inline=False)
	embed.set_footer(text=((f'Requested by {ctx.message.author.display_name} (') + str(ctx.message.author.id) + ')'))
	embed.timestamp = datetime.datetime.utcnow()

	await ctx.send(embed=embed)


@bot.command(brief='Returns a latency graph',description='Returns a latency graph over the past 10 minutes')
async def netgraph(ctx):

	async with ctx.typing():

		time_since_ping = round(time.time() - time_ping)

		x = np.append(np.arange((len(ping_arr) - 1)*-
					40, 1, 40) - time_since_ping, 0)
		y = np.append(ping_arr, ping_arr[len(ping_arr) - 1])

		X_ = np.linspace(min(x), max(x), 500)
		X_Y_Spline = make_interp_spline(x, y)
		Y_ = X_Y_Spline(X_)

		plt.plot(X_, Y_, color='red')

		plt.xlim(-600, 0)

		plt.ylim(0, max(Y_)*1.1)

		plt.xlabel('Time')

		plt.ylabel('Milliseconds')

		plt.title('Latency within the last 10 minutes')

		plt.savefig("temp/netgraph.png")

		file = discord.File("temp/netgraph.png")
		embed = discord.Embed(color=0xcf7336)
		embed.set_image(url="attachment://netgraph.png")
		embed.set_footer(text=((f'Requested by {ctx.message.author.display_name} (') + str(ctx.message.author.id) + ')'))
		embed.timestamp = datetime.datetime.utcnow()
	await ctx.send(embed=embed, file=file)
	plt.clf()


@bot.command(brief='General information',description='General information')
async def info(ctx):

	await ctx.send('**UltiduoBot v0.0.1**\n' \
		'Discord bot made for this server\n' \
		'Source code is available on GitHub by using *!github*')


@bot.command(brief='GitHub Repository',description='GitHub Repository')
async def github(ctx):

	await ctx.send('https://github.com/awesomeplaya211/UltiduoBot')


@bot.command(brief='Status check with uptime',description='Status check with uptime')
async def status(ctx):
		
	t2 = time.time()

	time_online = (
	str(math.floor((t2-t1)/3600)) + ' hours ' +
	str(math.floor(((t2-t1) % 3600)/60)) + ' minutes ' +
	str(round((t2-t1) % 60, 3)) + ' seconds')

	embed=discord.Embed(title="Status", color=0xcf7336)
	embed.add_field(name='Online for', value=time_online, inline=False)
	embed.add_field(name="Online since", value='`'+str(t1)+'`', inline=False)
	embed.set_footer(text=((f'Requested by {ctx.message.author.display_name} (') + str(ctx.message.author.id) + ')'))
	embed.timestamp = datetime.datetime.utcnow()

	await ctx.send(embed=embed)


@bot.command(brief='Kills bot (Dev command)',description='Kills bot (Dev command)')
async def kill(ctx):

	if ctx.author.id == 538921994645798915:
		await ctx.send('*dies*')

		await bot.close()

	else:
		await ctx.send("You're not my dev! >:(")
		print(ctx.author, 'attempted to kill bot')


t1 = time.time()

bot.loop.create_task(heartbeat())

bot.loop.create_task(check_hours_played())

keep_alive()

bot.run(os.getenv('discordtoken'))
