--[[
    AIthleewPro - Settings Wrapper
    Opens the settings dialog.
]]

local LrFunctionContext = import "LrFunctionContext"
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
local Config = loadModule("Utils/Config.lua")
local Settings = loadModule("UI/Settings.lua")

local logger = Logger:getLogger("SettingsWrapper")

LrTasks.startAsyncTask(function()
    LrFunctionContext.callWithContext("AIthleewSettings", function(context)
        Config:load()
        Settings:show(context)
    end)
end)
