--[[
    AIthleewPro - Socket Client
    Handles TCP socket communication with the Python AI engine.

    Protocol: JSON messages over TCP with newline delimiters.
    Each message is a single JSON object terminated by \n.

    NOTE: Currently unused - TaskRunner uses file-based communication.
    This module is preserved for future socket-based IPC.

    IMPORTANT: LrSocket API uses callback-based communication:
        LrSocket.bind {
            functionContext = context,
            plugin = _PLUGIN,
            port = 9876,
            mode = "send" or "receive",
            onConnected = function(...) end,
            onMessage = function(socket, message) end,
            onClosed = function(...) end,
            onError = function(...) end,
        }
    There is no synchronous receive or LrSocket.open().
]]

local LrTasks = import "LrTasks"
local LrPathUtils = import "LrPathUtils"

local pluginDir = (_PLUGIN and _PLUGIN.path) or LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AIthleewPro.lrplugin")
if not LrPathUtils.isAbsolute(pluginDir) or not LrPathUtils.child(pluginDir, "Info.lua") then
    local fallback = LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AutoColorPro.lrplugin")
    if LrPathUtils.isAbsolute(fallback) then pluginDir = fallback end
end
local function loadModule(modulePath)
    local fullPath = LrPathUtils.child(pluginDir, modulePath)
    local chunk, err = loadfile(fullPath)
    if chunk then return chunk() else error("Failed to load: " .. modulePath .. " - " .. tostring(err)) end
end

local Logger = loadModule("Utils/Logger.lua")
local Json = loadModule("Utils/Json.lua")

local logger = Logger:getLogger("SocketClient")

local SocketClient = {}
SocketClient.__index = SocketClient

local REQUEST_TIMEOUT = 30000
local MAX_RETRIES = 3

function SocketClient:new(opts)
    local obj = {
        host = opts.host or "127.0.0.1",
        port = opts.port or 9876,
        connected = false,
        send_port = nil,
        receive_port = nil,
        request_counter = 0,
        message_queue = {},
    }
    setmetatable(obj, self)
    return obj
end

function SocketClient:encodeJSON(obj)
    return Json.encode(obj)
end

function SocketClient:decodeJSON(str)
    return Json.decode(str)
end

function SocketClient:nextRequestId()
    self.request_counter = self.request_counter + 1
    return string.format("req_%d_%d", os.time(), self.request_counter)
end

function SocketClient:request(action, params)
    return nil, "Socket mode not implemented - use file-based communication"
end

function SocketClient:send(action, params)
    return false, "Socket mode not implemented"
end

function SocketClient:ping()
    return false
end

return SocketClient
