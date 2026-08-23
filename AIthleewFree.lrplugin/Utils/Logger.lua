--[[
    AIthleewPro - Logger Utility
    Provides consistent logging across the plugin.
]]

local LrLogger = import "LrLogger"

local Logger = {}
Logger.__index = Logger

local loggers = {}

Logger.LEVELS = {
    DEBUG = 1,
    INFO = 2,
    WARN = 3,
    ERROR = 4,
}

local LEVEL_NAMES = {
    [1] = "DEBUG",
    [2] = "INFO",
    [3] = "WARN",
    [4] = "ERROR",
}

local current_level = Logger.LEVELS.DEBUG

function Logger:getLogger(module_name)
    if not loggers[module_name] then
        local lrLogger = LrLogger("AIthleewPro")
        lrLogger:enable("logfile")

        local obj = {
            lrLogger = lrLogger,
            module = module_name,
        }
        setmetatable(obj, self)
        loggers[module_name] = obj
    end
    return loggers[module_name]
end

function Logger:setLevel(level)
    current_level = level
end

function Logger:format(level, message)
    local timestamp = os.date("%Y-%m-%d %H:%M:%S")
    local moduleName = self.module or "?"
    return string.format("[%s] [%s] [%s] %s", timestamp, LEVEL_NAMES[level], moduleName, message)
end

function Logger:debug(message)
    if current_level <= Logger.LEVELS.DEBUG then
        self.lrLogger:trace(self:format(Logger.LEVELS.DEBUG, message))
    end
end

function Logger:info(message)
    if current_level <= Logger.LEVELS.INFO then
        self.lrLogger:trace(self:format(Logger.LEVELS.INFO, message))
    end
end

function Logger:warn(message)
    if current_level <= Logger.LEVELS.WARN then
        self.lrLogger:trace(self:format(Logger.LEVELS.WARN, message))
    end
end

function Logger:error(message)
    if current_level <= Logger.LEVELS.ERROR then
        self.lrLogger:trace(self:format(Logger.LEVELS.ERROR, message))
    end
end

return Logger
