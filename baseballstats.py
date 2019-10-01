import re
import pickle
import statsapi
import datetime
import collections
from collections import OrderedDict

def makehash():
    return collections.defaultdict(makehash)

class BattingData:
    # EZ SHIT
    ab = 0
    bb = 0
    h = 0
    k = 0
    lob = 0
    r = 0
    rbi = 0

    # WTF MLB
    dbl = 0
    trpl = 0
    hr = 0
    hbp = 0
    sb = 0

    def __init__(self, args):
        self.ab = int(args.get('ab'))
        self.bb = int(args.get('bb'))
        self.h = int(args.get('h'))
        self.k = int(args.get('k'))
        self.lob = int(args.get('lob'))
        self.r = int(args.get('r'))
        self.rbi = int(args.get('rbi'))

class PitcherData:
    k = 0
    er = 0
    ip = ''
    out = 0
    bb = 0
    hr = 0
    # pitches
    p = 0
    # strikes
    s = 0
    # runs
    r = 0

    # win
    w = 0
    def __init__(self, args):
        self.k = int(args.get('k'))
        self.er = int(args.get('er'))
        self.ip = args.get('ip')
        innings, outs = self.ip.split('.')
        self.out = int(innings) * 3 + int(outs)
        self.bb = int(args.get('bb'))
        self.hr = int(args.get('hr'))
        self.p = int(args.get('p'))
        self.s = int(args.get('s'))
        self.r = int(args.get('r'))

class DataModel():
    lastDateChecked = '09/27/2019'
    ongoingGames = set()
    def __init__(self, beginDate, endDate):
        self.nameToId = {}
        self.playerGameData = {}
        self.playerIdToName = {}
        self.playerNameToId = {}
        self.beginDate = beginDate
        self.endDate = endDate

class BaseballStats():
    def __init__(self, name, beginDate=None, endDate=None):
        self.name = name
        self.data = self.loadData(beginDate, endDate)

    def loadData(self, beginDate, endDate):
        key = '{}_data.p'.format(self.name)
        try:
            dataFile = open(key, "rb")
        except:
            if beginDate:
                self.data = DataModel(beginDate, endDate)
                self.data.lastDateChecked = beginDate
                self.data.endDate = endDate
                self.saveData()
                dataFile = open(key, "rb")
            else:
                dataFile = None

        if not dataFile:
            raise Exception('League not created!')
        data = pickle.load(dataFile)
        dataFile.close()
        return data

    def saveData(self):
        key = '{}_data.p'.format(self.name)
        f = open(key, "wb")
        pickle.dump(self.data, f)
        f.close()

    def getPlayerStats(self):
        date = self.data.lastDateChecked
        self.data.lastDateChecked = datetime.date.today().strftime('%m/%d/%Y')
        if (
            self.data.endDate and
            datetime.datetime.strptime(date, '%m/%d/%Y') > datetime.datetime.strptime(self.data.endDate, '%m/%d/%Y')):
            date = self.data.endDate

        games = statsapi.schedule(start_date=date, end_date=self.data.lastDateChecked)
        gameIdsToGet = set(self.data.ongoingGames)
        # clear now, repop later
        self.data.ongoingGames = set()
        for game in games:
            if game['status'] not in ('Cancelled', 'Final'):
                self.data.ongoingGames.add(game['game_id'])
            gameIdsToGet.add(game['game_id'])
        for gameId in gameIdsToGet:
            self._getPlayerStatsForGame(gameId)

        self.saveData()

    def _getPlayerStatsForGame(self, gameId):
        box_data = statsapi.boxscore_data(gameId)

        box_name_to_id = {}
        for v in box_data['playerInfo'].values():
            box_name_to_id[v['boxscoreName']] =  v['id']
            self.data.playerIdToName[v['id']] = v['fullName']
            self.data.playerNameToId[v['fullName']] = v['id']

        game_info = { v['label']: v.get('value') for v in box_data['gameBoxInfo']}

        raw_home_info = []
        raw_away_info = []
        for field in box_data['home']['info']:
            if field.get('title', None) == 'BATTING':
                raw_home_info = field['fieldList']

        for field in box_data['away']['info']:
            if field.get('title', None) == 'BATTING':
                raw_home_info = field['fieldList']

        home_info = { v['label']: v.get('value') for v in raw_home_info}
        away_info = { v['label']: v.get('value') for v in raw_away_info}

        additional_batter_data = makehash()

        keys = game_info.keys()
        def parseFromInfo(key, info):
            if key in info:
                players = info[key].split(';')
                for player in players:
                    res = re.search(r'(\D+) (\d )*(\(.*\))', player)
                    group = res.groups()
                    additional_batter_data[box_name_to_id[group[0].strip()]][key] = int(group[1].strip()) if group[1] else 1

        parseFromInfo(u'HBP', game_info)
        parseFromInfo(u'HR', home_info)
        parseFromInfo(u'2B', home_info)
        parseFromInfo(u'3B', home_info)
        parseFromInfo(u'SB', home_info)
        parseFromInfo(u'HR', away_info)
        parseFromInfo(u'2B', away_info)
        parseFromInfo(u'3B', away_info)
        parseFromInfo(u'SB', away_info)

        for batter_data in box_data['awayBatters'] + box_data['homeBatters']:
            pid = batter_data['personId']
            if not pid:
                continue
            batter_model = BattingData(batter_data)

            # Parse out HRs, SBs, doubles, triples, hrs
            additional_data = additional_batter_data[pid]
            batter_model.hr = additional_data['HR'] or 0
            batter_model.dbl = additional_data['2B'] or 0
            batter_model.trpl = additional_data['3B'] or 0
            batter_model.sb = additional_data['SB'] or 0
            batter_model.hbp = additional_data['HBP'] or 0

            if not pid in self.data.playerGameData:
                self.data.playerGameData[pid] = {
                    'batting': {}, 'pitching': {}
                }
            self.data.playerGameData[pid]['batting'][gameId] = batter_model

        for pitcher_data in box_data['awayPitchers'] + box_data['homePitchers']:
            res = re.search('([^\(]+)(\((\w).*)*', pitcher_data['namefield']).groups()

            name = res[0].strip()
            if not name in box_name_to_id:
                continue

            pitcherId = box_name_to_id[name]
            pitcher_model = PitcherData(pitcher_data)
            pitcher_model.w = 1 if res[2] == 'W' else 0
            if not pitcherId in self.data.playerGameData:
                self.data.playerGameData[pitcherId] = {
                    'batting': {}, 'pitching': {}
                }
            self.data.playerGameData[pitcherId]['pitching'][gameId] = pitcher_model

PITCHERPOINTS = {
    'out': 1.5,
    'er': -3,
    'k': 3,
}
HITTERPOINTS = {
    'h': 3,
    'dbl': 3,
    'trpl': 6,
    'hr': 9,
    'rbi': 3.5,
    'r': 3.2,
    'bb': 3,
    'sb': 6,
    'hbp': 3,
}

class Team():
    def getPlayerTotal(self, data, pid, side):
        if side == 'batting':
            points = HITTERPOINTS
        else:
            points = PITCHERPOINTS

        games = data.playerGameData.get(pid, {}).get(side, None)
        pointTotal = 0
        if games:
            for game in games.values():
                for k, v in points.items():
                    pointTotal += getattr(game, k, 0) * v
        return pointTotal

    def printTeam(self, dataSource):
        data = dataSource.data
        temp = '{:<20} {:<10}\n'
        output = temp.format('NAME', 'POINTS')
        teamTotal = 0
        for pid, name in getattr(self, 'pitchers', {}).items():
            total = self.getPlayerTotal(data, pid, 'batting')
            total += self.getPlayerTotal(data, pid, 'pitching')
            teamTotal += total
            output += temp.format(name, total)

        for pid, name in getattr(self, 'posPlayers', {}).items():
            total = self.getPlayerTotal(data, pid, 'batting')
            teamTotal += total
            output += temp.format(name, total)

        output += temp.format('**Total**', '**{:.1f}**'.format(teamTotal))
        return output

class League():
    teams = {}
    def __init__(self, name, beginDate=None, endDate=None):
        self.name = name
        self.dataSource = BaseballStats(name, beginDate, endDate)
        self.teams = self.loadTeams()

    def addTeam(self, name):
        self.teams[name] = Team()
        self.saveTeams()

    def removeTeam(self, name):
        self.teams.pop(name, None)
        self.saveTeams()

    def setPlayers(self, teamName, players):
        agg = OrderedDict({})
        for player in players:
            res = statsapi.lookup_player(player)
            if len(res) > 1:
                # WILL SMITH
                res = [r for r in res if r['primaryPosition']['abbreviation'] != 'P']
            agg[res[0]['id']] = res[0]['fullName']
        self.teams[teamName].posPlayers = agg
        self.saveTeams()

    def setPitcher(self, teamName, pitcher):
        res = statsapi.lookup_player(pitcher)
        if len(res) > 1:
            # WILL SMITH
            res = [r for r in res if r['primaryPosition']['abbreviation'] == 'P']
        self.teams[teamName].pitchers = { res[0]['id'] : pitcher }
        self.saveTeams();

    def update(self):
        self.dataSource.getPlayerStats()

    def printTeam(self, name):
        return self.teams[name].printTeam(self.dataSource)

    def printLeague(self):
        tmp = '--------{}---------\n{}\n'
        output = f'Stats between {self.dataSource.data.beginDate}-{self.dataSource.data.lastDateChecked}. Stat collection ends on {self.dataSource.data.endDate}\n'
        for name, team in self.teams.items():
            output += tmp.format(name, team.printTeam(self.dataSource))
        return output

    def loadTeams(self):
        key = '{}.p'.format(self.name)
        try:
            dataFile = open(key, "rb")
        except:
            self.saveTeams()
            dataFile = open(key, "rb")

        data = pickle.load(dataFile)
        dataFile.close()
        return data

    def saveTeams(self):
        key = '{}.p'.format(self.name)
        f = open(key, "wb")
        pickle.dump(self.teams, f)
        f.close()
