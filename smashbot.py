import os
import time
import requests
from slackclient import SlackClient


# starterbot's ID as an environment variable
BOT_ID = os.environ.get("BOT_ID")

# Challonge
CHALLONGE_KEY = os.environ.get("CHALLONGE_API_KEY")
CHALLONGE_SUFFIX = '.json?api_key=' + str(CHALLONGE_KEY)
CHALLONGE_BASE_URL = 'https://api.challonge.com/v1/'

# constants
AT_BOT = "<@" + str(BOT_ID) + ">"
LIST_TOURNAMENTS = "tournaments"
LIST_MATCHES = "matches"

# instantiate Slack & Twilio clients
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))


def handle_command(command, channel):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    response = "Not sure what you mean. Use the *" + LIST_MATCHES + \
               "* command with numbers, delimited by spaces."
    if command.startswith(LIST_TOURNAMENTS):
        response = list_tournaments()
    elif command.startswith(LIST_MATCHES):
        if len(command.split()) == 1:
            response = all_open_matches()
        else:
            response = list_matches(command.split()[1])
    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)

def list_tournaments():
    response = '*Tournaments:*\n\n'
    json = requests.get(CHALLONGE_BASE_URL + '/tournaments' + CHALLONGE_SUFFIX).json()
    for entry in json:
        tournament = entry['tournament']
        response = response + tournament['name'] + ' (id: ' + str(tournament['id']) + ')\n'
    return response

def list_matches(tournament):
    tournament_url = CHALLONGE_BASE_URL + '/tournaments/' + tournament
    name = requests.get(tournament_url + CHALLONGE_SUFFIX).json()['tournament']['name']
    response = '*Open matches for "' + name + '":*\n'
    json = requests.get(tournament_url + '/matches' + CHALLONGE_SUFFIX).json()
    for entry in json:
        match = entry['match']
        if match['state'] == 'open':
            response = response + parse_match(match, tournament)
    return response

def all_open_matches():
    tournaments_json = requests.get(CHALLONGE_BASE_URL + '/tournaments' + CHALLONGE_SUFFIX).json()
    for tournament_entry in tournaments_json:
        tournament = tournament_entry['tournament']
        response = list_matches(str(tournament['id']))
    return response

def parse_match(match, tournament):
    tournament_url = CHALLONGE_BASE_URL + '/tournaments/' + tournament
    player_one_json = requests.get(tournament_url + '/participants/' + str(match['player1_id']) + CHALLONGE_SUFFIX).json()
    player_two_json = requests.get(tournament_url + '/participants/' + str(match['player2_id']) + CHALLONGE_SUFFIX).json()
    return player_one_json['participant']['name'] + ' vs. ' + player_two_json['participant']['name'] + '\n'

def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel']
    return None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("StarterBot connected and running!")
        while True:
            command, channel = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                handle_command(command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print('bot: ' + BOT_ID)
        print('challonge: ' + CHALLONGE_KEY)
        print("Connection failed. Invalid Slack token or bot ID?")
