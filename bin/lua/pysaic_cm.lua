-- PySAIC Connection Manager
local pollnet_raw = require("pollnet")

local M = {}
local socket = nil

local function connect()
    if socket then return end -- Prevent re-creating the socket

    printf("PySAIC_Connection: Connecting to backend...")
    socket = pollnet_raw.open_tcp("127.0.0.1:8008")
    if socket then
        printf("PySAIC_Connection: Socket created, status: %s", socket:status())
    else
        printf("PySAIC_Connection: Failed to create socket")
    end
end

function M.init()
    connect()
end

function M.update()
    if not socket then
        -- This can happen if the initial connection failed.
        -- The game script will call init() on first_update, but we can try again here.
        connect()
        return nil
    end

    if socket:status() == "closed" or socket:status() == "error" then
        -- The connection was lost, let's try to reconnect.
        printf("PySAIC_Connection: Connection lost. Reconnecting...")
        socket:close()
        socket = nil
        connect()
        return nil
    end

    local ok, data = socket:poll()
    if not ok and data ~= "closed" then
        printf("PySAIC_Connection: Socket error: %s", data)
        socket:close()
        socket = nil
        return nil
    end
    return data
end

function M.send(line)
    if socket and socket:status() == "open" then
        socket:send(line .. "\n")
        return true
    end
    return false
end

function M.status()
    if socket then
        return socket:status()
    end
    return "closed"
end

function M.shutdown()
    -- we don't close it ever
end

return M
