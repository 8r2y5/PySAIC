# Changelog

## `0.3.0b7` — 2025-11-12
### Short summary
- Fix issue with text malform, making some messages not being properly formatted in `0.3.0b6`
- Add `/reply` command to quickly reply to the last private message received or sent
  - there is also alias `/r` for convenience

### Do I need to do anything?
Just update chat app, game files did were not changed so no game restart is required.

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
