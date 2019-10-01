import os
import discord
import baseballstats
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('BASEBALL_BOT_TOKEN')
client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
lg_store = {}
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.upper() == 'OH':
        await message.channel.send('-tani?')
    if message.content.upper() == 'MIKE':
        await message.channel.send("trout")
    try:
        if message.content.startswith('!createLeague'):
            params = message.content.split(' ')[1:]
            lg = baseballstats.League(*params)
            lg_store[params[0]] = lg
            await message.channel.send('League Created')

        if message.content.startswith('!addTeam'):
            params = message.content.split(' ')[1:]
            lg = lg_store.get(params[0], None) or baseballstats.League(params[0])
            lg.addTeam(params[1])
            await message.channel.send('Team added')

        if message.content.startswith('!removeTeam'):
            params = message.content.split(' ')[1:]
            lg = lg_store.get(params[0], None) or baseballstats.League(params[0])
            lg.removeTeam(params[1])
            await message.channel.send('Team removed')

        if message.content.startswith('!setPlayers'):
            params = message.content.split(' ')[1:]
            lg = lg_store.get(params[0], None) or baseballstats.League(params[0])
            teamName = params[1]
            players = [x.strip() for x in ' '.join(params[2:]).split(',')]
            lg.setPlayers(teamName, players)
            await message.channel.send('Players set')

        if message.content.startswith('!setPitcher'):
            params = message.content.split(' ')[1:]
            lg = lg_store.get(params[0], None) or baseballstats.League(params[0])
            teamName = params[1]
            players = [x.strip() for x in ' '.join(params[2:]).split(',')]
            lg.setPitcher(teamName, players[0])
            await message.channel.send('Pitcher set')

        if message.content.startswith('!update'):
            params = message.content.split(' ')[1:]
            lg = lg_store.get(params[0], None) or baseballstats.League(params[0])
            lg.update()
            output = lg.printLeague()
            await message.channel.send(f'``` {output} ```')

        if message.content.startswith('!print'):
            params = message.content.split(' ')[1:]
            lg = lg_store.get(params[0], None) or baseballstats.League(params[0])
            output = lg.printLeague()
            await message.channel.send(f'``` {output} ```')
    except Exception as a:
        await message.channel.send(a)
client.run(token)
