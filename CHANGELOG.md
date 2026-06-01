# Changelog

## `0.3.0b14` - 2026-06-01
### What's New:
- **New Integration patch for PDA**
  - [Mod App Creator](https://github.com/Ncenka/Mod-App-Creator)

### Do I need to do anything?
- Please reinstall PySAIC using Mod Organizer 2 (MO2) to ensure all updates are applied correctly.

---

## `0.3.0b13` - 2026-05-31
### What's New and Improved:
- **Your Settings Stay Saved**:
  - Your personal settings, themes, and activity logs will now automatically save and stay put in a special folder (`%appdata%/PySAIC`). You won't lose them when updating the app anymore!
- **Smoother Performance**:
  - App run more efficiently and use less of your computer's processing power by reducing unnecessary communication between PySAIC and the game.
- **Chatbox-Only Option**:
  - You can now install PySAIC to only show the chatbox, without making any changes to your PDA's UI.
    - There is also included the [Mags Redux Patch](https://www.moddb.com/mods/stalker-anomaly/addons/152-banjajis-patch-chernobyl-relay-chat-rebirth-and-mags-redux) as an easy installation option for your convenience.
- **Easier Private Messages**:
  - When you receive a new private message, it will also appear in your main chat window.
    - Previously, it would open in a new tab, which sometimes caused users to miss these messages.
- **Cleaner Map Changes**:
  - Fixed bug that caused a long list of login/logout messages to appear every time you switched maps.
    - Now, you'll only see new messages without that wall of text.

### Do I need to do anything?
- Please reinstall PySAIC using Mod Organizer 2 (MO2) to ensure all updates are applied correctly.

---

## `0.3.0b12` - 2026-05-17
### Short summary
- **Improved Chat Reliability**: Messages should now be handled more smoothly, especially if your connection isn't perfect.
- **Internal Improvements**: Some under-the-hood changes to how the app finds its files, leading to better stability.

### Do I need to do anything?
- Reinstall PySAIC via MO2

---

## `0.3.0b11` - 2026-05-15
### Short summary
- **PDA Chat**: You can now chat directly from your PDA, with features like unread message indicators, message timestamps, and dynamic message display templates.
  - **Compatibility**: Enhanced integration with mods like [Fatal Error](https://www.moddb.com/addons/fatal-error-by-ncenka) and [iTheon-PDA-Taskboard](https://github.com/lTheon/iTheon-PDA-Taskboard).
- **Themes**: More ways to customize your app's look! Theme management is improved with icon support, and it's easier to create, select, and delete themes.
- **New Features**:
  - Support for password-protected IRC channels.
  - Integrated tutorial into the FOMOD installer.
- **Payment Shortcuts**: The `/pay` command now understands human-readable amounts (e.g., `/pay user 1.5k` for 1500).
- **New Maps**: Added support for Grimwood, Promzone, and Town Yuzhniy.
- **User Experience**:
  - Improved nickname auto-completion with cycling through matches.
  - Better user list sorting and status indicators.
  - Clearer messages for unsupported versions and connection events.
  - Word deletion in chat with `Ctrl+Backspace`.
- **Mod Organizer 2**: Fully supported. You don't need to install manually into the game folder anymore.
- **Performance**: Faster and smoother synchronization between chat and game.

### Fixes:
- Fixed display issues with messages on screen and avatar handling.
- Resolved issues with user state display when offline and nickname auto-completion in-game.
- Fixed scrolling down issues and incorrect faction tags in death messages.
- Improved handling of IRC connection waiting times.

### Do I need to do anything?
- You need to copy all the files and restart your game.

---

## `0.3.0b10` — 2026-05-11
## Short summary
- Fix issue that prevented avatar picker from rendering
- Fix issue related to in-game icon display

### Do I need to do anything?
- if you are updating from 0.3.0b8
  - you only need to turn off client and update PySAIC, no game restart is required
- if you are updating from anything else
  - You need to copy all the files and restart your game.

---

## `0.3.0b9` — 2026-01-15
### Short summary
- Fix error that might occur when applying colors in preview mode
- Fix typos

### Do I need to do anything?
- if you are updating from 0.3.0b8
  - you only need to turn off client and update PySAIC, no game restart is required
- if you are updating from anything else
  - You need to copy all the files and restart your game.

## `0.3.0b8` — 2026-01-15
### Short summary
- Add faction colored nicks in-game user list
  - you can toggle this option in settings. It is enabled by default
- Improved emission and underground detection
- Improved faction and avatar syncing in-game
- New option for the disconnect: Random
  - Depending on the setting, it will each time choose if you client will stay in/disconnect/malform text during emission or going underground
- Made Clear Sky more distinguishable from Mercenary in user list
  - their colors were too similar, Clear Sky is now a lighter shade of blue
- Colors:
  - changed default theme from gray to more dark ones 
  - now you can configure everything you want, from faction colors to the button color
  - in-game faction colors are hardcoded, they are not synchronized, yet.
- Font:
  - all settings are configurable in the options
  - changed default font from `Microsoft Sarif Sans` to `JetBrains Mono`
  - default font size is `10`
- Messages will stay on after loading the map
  - previously after loading into new map chat history in game was missing

### Do I need to do anything?
You need to copy all the files and restart your game.

## `0.3.0b7` — 2025-11-14
### Short summary
- Add `/reply` command to quickly reply to the last private message received or sent.
  - there is also alias `/r` for convenience.
- Add option to configure in-game user list display.
- Improved user list sorting.
- Fix issue with text malform, making some messages not being properly formatted in `0.3.0b6`.

### Do I need to do anything?
You need to copy all the files and restart the game.

---

## `0.3.0b6` — 2025-11-11
### Short summary
- Fix config issue that was causing some settings to not be saved properly in `0.3.0b5`

### Do I need to do anything?
Just update chat app, game files did were not changed so no game restart is required.

---

## `0.3.0b5` — 2025-11-11

### Short summary
A small update focused on making the chat experience smoother and less distracting. We improved syncing, reduced noisy messages, and made disconnects and window behavior more predictable.

### What you'll notice
- Fewer sync interruptions: the app keeps chat and player info up-to-date more smoothly.
- Quieter app: less technical noise and fewer background messages.
- More control over disconnects: you can choose when the app disconnects, with separate settings for emission and underground connections so each behaves the way you prefer.
- Better window focus: the right chat window comes forward when needed.

### Fixes and improvements
- Improved handling of occasional sync errors so you see fewer interruptions.
- Lowered background logging noise for a cleaner experience.
- Tidied up window and disconnect behavior to avoid surprises when switching or closing the app.

### Do I need to do anything?
No. Update to `0.3.0b5` and continue using the app as usual. If you see repeated sync failures or missing visuals, please take a screenshot and report it.

### Need help?
Open an issue or contact support with a short description and steps to reproduce the problem; screenshots help a lot.

---

## Release notes (since `0.3.0b4`)

### Short summary
This update makes the chat app more stable and easier to use. We focused on fixing annoying sync problems, reducing noisy messages, and making window and disconnect behavior more predictable. Most changes are behind the scenes, but you should feel the app is smoother and less distracting.

### What you'll notice (high level)
- Fewer sync interruptions: data syncing is more reliable, so messages and player info update more smoothly.
- Less noise: unnecessary technical messages and logs are reduced — the app feels quieter.
- Clearer behavior when disconnecting or switching: closing or reconnecting should work more predictably.
- Better window focus: the app manages windows and focus more helpfully when you switch instances.
- Small UI and icon fixes: some icons and small visuals were tidied up.

### New or improved features (user-facing)
- More reliable player status and chat synchronization.
- An IRC window for raw IRC messages (helpful if you want to see the activity coming from IRC servers).
- Improvements to window focus so the correct chat window is brought forward when needed.

### Fixes you might notice
- Less chance of duplicate nicknames causing confusion.
- Small text fixes in messages and dialogs.
- Improved handling when the app shuts down so the local server closes properly.

### Under the hood (short)
We updated several libraries and refactored internal code to improve stability and performance. If you're not a developer, you don't need to worry about these details — this work is to make the app more stable for everyone.

### Do I need to do anything?
No. Just update to the latest version and continue using the app as before. If you run into problems (sync failing repeatedly, odd errors, or missing icons), please tell us the steps to reproduce the issue and include a screenshot if possible.

### Need help or want to report a bug?
Open an issue or contact support with a short description of what happened and what you were doing. Screenshots and the exact steps to reproduce the problem help us fix things faster.

---

## Changes since `0.2.0` (brief user summary)
- Added avatar editor and more avatar options.
- Better chat synchronization and new IRC commands support.
- Popup notifications for messages.
- Blocking options for users and words in chat.
- Improved login, reconnection, and message display behaviors.
- Various bug fixes and small UI improvements.

If you'd like the changelog to be even shorter (one-liner per release) or translated into another language, tell me which format you prefer.
