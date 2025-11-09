# Changelog

## Release notes (since 0.3.0b3) 
### Summary
 - This release contains a series of improvements to player data synchronization, window/focus management, network disconnection handling, UI and icon updates, dependency updates, and many internal refactors that improve stability, logging, and performance. Several bug fixes and small UI tweaks are included as well.

### Highlights
 - Player data synchronization reworked and stabilized (queued processing, improved router logic).
 - Network disconnection handling refactored and made more robust via enums and clearer logic.
 - New window focus helpers (lift_and_focus) and improved instance focus/communication.
 - URI protocol registration added for the local server.
 - Dependency upgrades for several core libraries.
 - Multiple refactors and logging improvements to make the codebase clearer and reduce noisy logs.
### Added
 - Implemented player data synchronization in GameEventRouter to better handle player updates and avoid race conditions.
 - Added an IRC window and logging for raw IRC messages, improving visibility into IRC events.
 - Added lift_and_focus method and focused-window handling to improve window management and instance focus behavior.
 - Registered a URI protocol in the local server to improve integration (local server now registers a URI protocol).
 - Status update functions now support an optional "force send" parameter to allow forced state synchronization when needed.
 - Added a changelog file and updated README (meta: changelog now present in repo).
### Changed / Improved
 - Refactored IncomingQueue for clearer semantics and improved behavior under network disconnections.
 - Network disconnection handling refactored to use DisconnectOnNetworkDestructionSetting enum and related settings for clearer code paths.
 - Renamed icon texture files: pysaic_icons_unisg.dds → pysaic_icons_isg.dds (asset rename for consistency).
 - Improved money update logic to allow forced updates in sendActorStatus.
 - Player data synchronization refactored to use a queue (better handling of multiple updates) and many related improvements across game_event_router.
 - Shutdown process improved to ensure the local server is properly closed during shutdown.
 - Improved registry key handling in notification_registry.py to suppress spurious errors and be clearer.
 - Logging improvements: normalized IRC logging, masked sensitive info in logs, and several formatting improvements.
 - Achievement handling now posts updates asynchronously to chat to reduce blocking.
 - Default chat message color set to white when unspecified.
 - isValidIcon updated to include user type parameter for better validation.
### Fixed
 - Handle nickname collisions by appending an underscore and updating the user mapping (prevents duplicate nick edge cases).
 - Fixed a typo in death remarks (text/content fix).
 - Removed redundant check for original content in message handling (cleanup).
 - Various smaller fixes related to icons, UI display, and user list presentation.
### Performance
 - Replaced ThreadPoolExecutor usage with asyncio.to_thread in game process lookup to improve performance and reduce thread pool overhead.
 - Optimized several lookup and synchronization paths (player updates, status updates).
### Dependencies
 - Upgraded a number of dependencies (notable entries from the dependency update commit):
   - attrs: 25.3.0 -> 25.4.0
   - frozenlist: 1.7.0 -> 1.8.0
   - idna: 3.10 -> 3.11
   - matplotlib-inline: 0.1.7 -> 0.2.1
   - multidict: 6.6.4 -> 6.7.0
   - propcache: 0.3.2 -> 0.4.1
   - iniconfig: 2.1.0 -> 2.3.0
   - ipython: 9.5.0 -> 9.6.0
   - platformdirs: 4.4.0 -> 4.5.0
   - py-irclib: 0.6.0 -> 0.8.1
   - yarl: 1.20.1 -> 1.22.0
   - aiohttp: 3.12.15 -> 3.13.2
   - pylint: 3.3.8 -> 3.3.9
   - pyyaml: 6.0.2 -> 6.0.3
   - click: 8.2.1 -> 8.3.0
 - Also updated wcwidth and adjusted Python version compatibility in one commit (see repo for exact changes).
### Internal / Code cleanup
 - Large number of refactors aimed at simplifying state synchronization, improving error logging, and removing excessive/noisy logs.
 - Removed old .thm files and other cleanup tasks.
 - Formatting changes applied via black in several commits.
### Potential breaking changes / upgrade notes
 - Icon rename: `pysaic_icons_unisg.dds` renamed to `pysaic_icons_isg.dds.` If you have custom themes or references to the old filename, update them.
 - Dependency upgrades (especially aiohttp, yarl, and py-irclib) may affect runtime behavior; run your test suite and re-check integrations (IRC, HTTP) after upgrading.
 - No other explicit breaking API changes were indicated in commits — most changes are internal refactors and improvements.

## Changes from version 0.2.0 to current (0.3.x)

### New Features
- Player Avatar Editor: supports DDS/PNG generation, zoom, pan, and masking.
- In-game chat synchronization and new IRC commands (e.g. /mode, /whois, /whowas).
- Popup notifications for private and channel messages.
- Additional avatars, and new user display styles.
- Ability to create own local avatar.
- Blocking users and words in chat.
- Expanded death, location, and travel message system (new XML/YML files).
- AFK status and AFK icon in user list.

### Improvements
- Refactored options window: better section organization and styling.
- Improved login, synchronization, and user display logic.
- Enhanced player location handling and game synchronization.
- Improved message handling: hyperlink support and word wrapping.

### Bug Fixes
- Fixed faction, icon, texture path, and avatar synchronization issues.
- Improved nickname validation, AFK handling, money transfer, and status sync.
- Fixed config file and encoding errors.
- Improved window closing, state reset after disconnect, and reconnect handling.

### Documentation
- Improved README, added configuration guides and Twitch instructions.

