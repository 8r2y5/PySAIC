# Python Stalker Anomaly IRC Client
or PySAIC for short.  
Based on [CRCR / Chernobyl Relay Chat Rebirth](https://github.com/8r2y5/Chernobyl-Relay-Chat-Rebirth), rewritten in Python with additional features and improvements.  
Compatible with any Stalker Anomaly version and modpack that uses Stalker Anomaly.

# ![Download](https://img.shields.io/badge/Download-something?style=for-the-badge&link=https://github.com/8r2y5/PySAIC/releases/latest)
![Version](https://img.shields.io/github/v/release/8r2y5/PySAIC?style=flat-square) ![License](https://img.shields.io/github/license/8r2y5/PySAIC?style=flat-square) ![Downloads](https://img.shields.io/github/downloads/8r2y5/PySAIC/total?style=flat-square)

# Features
- **Compatible with [CRCR / Chernobyl Relay Chat Rebirth](https://github.com/8r2y5/Chernobyl-Relay-Chat-Rebirth) and addons**
  - Works with any version of Stalker Anomaly and modpack that uses it.
  - Using [MAGS Redux](https://github.com/RAX-Anomaly/MagsRedux)? Download patch [here](https://www.moddb.com/mods/stalker-anomaly/addons/152-banjajis-patch-chernobyl-relay-chat-rebirth-and-mags-redux).
- **Ability to connect to different IRC servers**
  - Want to use your own server? You can do that! Just edit the `server.yml` file.
  - You can connect to any IRC server that supports the protocol, not only the one that Chernobyl Relay Chat uses. Just change it in `server.yml` file.
  - Twitch IRC is supported too, you can use it to chat with your viewers while streaming Stalker Anomaly.
- **Custom channels**
  - Want to create your own channel? You can do that! Just add it to the `server.yml` file.
- **Customizable**
  - Change your nickname, avatar, and other settings in the options menu.
- **Block Users**
  - Block users from sending you messages or interacting with you in-game.
- **Block Words**
  - Block messages that contain specific words or phrases.
- **Private Messaging**
  - Send private messages to other players in-game.
- **Money Transfer**
  - Send money to other players in-game.
- **Command Support**
  - Supports various commands for managing your chat experience.
- **Easy Installation**
  - Simple installation process, just extract the files and run the client.
- **Cross-Platform**
  - Works on Windows or Linux.
- **See others status in-game**
  - Online status 
  - Avatar / Profile Picture
  - Faction
  - **PySAIC Client** (if they use it)
    - Location name
    - AFK status
    - Rank
    - Reputation


## Ability to identify with IRC server
You can provide password in `Options`.  
To register your nick type, `/msg NickServ REGISTER [password] [email]` and follow the instructions.
Configuration is stored in `config.yml` file, which is created after the first run of the client.

## Commands
You can find all available commands in-game by typing `/commands` or `/help`.
All commands that requires to provide nick can be used with `@` for nick completion.

| Command      | Description                                     | Usage                            | Note                                                                                     |
|--------------|-------------------------------------------------|----------------------------------|------------------------------------------------------------------------------------------|
| `/block`     | Blocks interactions/messages with provided user | Check `/block` command section   |                                                                                          |
| `/blockword` | Blocks messages that contain specified word     | See `/blockword` command section |                                                                                          |
| `/help`      | Shows help message for command                  | `/help block`                    |                                                                                          |
| `/commands`  | Shows avaliable commands                        | `/commands`                      |                                                                                          |
| `/msg`       | Sends private message to user                   | `/msg [nick] [message]`          |                                                                                          |
| `/m`         | Alias for `/msg`                                | `/m [nick] [message]`            |                                                                                          |
| `/w`         | Alias for `/msg`                                | `/w [nick] [message]`            |                                                                                          |
| `/priv`      | Alias for `/msg`                                | `/priv [nick] [message]`         |                                                                                          |
| `/dm`        | Alias for `/msg`                                | `/dm [nick] [message]`           |                                                                                          |
| `/nick`      | Changes you nicname in chat.                    | `/nick [new nick]`               | Nick cannot contain space, it's IRC limitation                                           |
| `/reply`     | Replyes to last private message/dm              | `/reply [message]`               |                                                                                          |
| `/r`         | Alias for `/reply`                              | `/r [message]`                   |                                                                                          |
| `/pay`       | Transfers money to another user                 | `/pay [nick] [amount]`           | Both need to be in-game. There is option to block money transfer in `Options`.           |
| `/exit`      | Closes the client                               | `/exit`                          |                                                                                          |
| `/afk`       | Sets you as AFK                                 | `/afk`                           | Will show AFK status in chat, other players can see it.                                  |
| `/mode`      | Sends IRC MODE command                          | `/mode [mode]`                   | [See IRC MODE](https://matrix-org.github.io/matrix-appservice-irc/latest/irc_modes.html) |
| `/who`       | Sends IRC WHO command                           | `/who [nick/channel]`            |                                                                                          |
| `/whois`     | Sends IRC WHOIS command                         | `/whois [nick]`                  |                                                                                          |
| `/whowas`    | Sends IRC WHOWAS command                        | `/whowas [nick]`                 |                                                                                          |


# /block command usage
It is stored inside `comfig.yml` file.

| Command       | Description         | Usage                |
|---------------|---------------------|----------------------|
| `/block list` | Lists blocked users | `/block list`        |
| `/block add`  | Blocks user         | `/block add [nick]`  |
| `/block del`  | Removes user        | `/block del [nick]`  |

# /blockword command usage
It is stored inside `config.yml` file.

| Command           | Description                   | Usage                   |
|-------------------|-------------------------------|-------------------------|
| `/blockword list` | Lists blocked words           | `/blockword list`       |
| `/blockword add`  | Blocks messages with word     | `/blockword add [word]` |
| `/blockword del`  | Removes word from block list  | `/blockword del [word]` |

# Discord Server
<div>
    <p>
        <a href="https://discord.gg/KjNHXCkHr9">
            <img src="https://img.shields.io/discord/1254093654172110898?color=5865F2&label=Discord%20Server&logo=discord&logoColor=5865F2&style=for-the-badge" alt="Discord Server">
        </a>
    </p>
</div> 

# Installation 
Currently, Mod Managers are not supported, so you will need to install it manually.
1. Extract the contents of the zip wherever you like, preferably inside Anomaly's game directory.
2. Copy the included `gamedata`, `res`, `pysaic` folders to your Anomaly directory.

# Usage
Run `pysaic.exe`; the application must be running for in-game chat to work.  
After connecting, click the Options button to change your name and other settings, it can be lunched after/before Anomaly.  
Once playing, press Enter (by default) to bring up the chat interface and Enter again to send your message, or Escape to close without sending.  
You may use text commands from the game or client by starting with a /. Use `/commands` to see all available commands.

# Connecting to different IRC servers
You can connect to any IRC server that supports the protocol.
PySAIC upon starting (or missing) creates `server.yml` file in the same directory as `pysaic.exe`.
You can edit this file to change the server, port, and other connection settings. You can also add/remove/modify channels too.
You can share this file with other players to connect to the same server and channels.

# Custom Avatar / Profile Picture
In options, you can set your own avatar, uploading/creating new one will require restarting the game.
Custom avatars are displayed only locally, other players will see the default avatar based on your nickname and current faction.
